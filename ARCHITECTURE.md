# Architecture Guide

Technical design, container lifecycle, and service contracts for `hf-backend`.

---

## System overview

`hf-backend` is an aggregation gateway running in a Hugging Face Docker Space. It mounts routers from separate repositories under dedicated URL prefixes.

```
Incoming Request
       │
       ▼
[ Hugging Face Edge Proxy ] (:443)
       │
       ▼
[ Uvicorn Worker ] (:7860)
       │
       ▼
[ SecurityHeadersMiddleware ] (HSTS, nosniff, frame-ancestors)
       │
       ▼
[ RequestLimitMiddleware ] (Body size cap + request execution timeout)
       │
       ├── /project ────────► [ Interactive Swagger UI ]
       ├── / (browser) ─────► [ Status Dashboard (HTML) ]
       ├── /status ─────────► [ Status Dashboard (HTML) ]
       ├── /health ─────────► [ Aggregated Health Monitor (JSON) ]
       ├── /heartflow/* ────► [ Mounted Subproject: HeartFlow OS ]
       ├── /semantic/* ─────► [ Mounted Subproject: Semantic Comment Analyzer ]
       └── /<prefix>/* ─────► [ Dynamically Mounted Future Services ]
```

The gateway handles shared infrastructure tasks:
* Dynamic discovery and isolated mounting of external service packages.
* Inbound payload verification before memory buffering.
* Global request timeouts to prevent worker starvation.
* Zero-cold-start inference by baking weights at build time and warming them up at boot.
* Centralized health tracking reflecting route mounting and model readiness.

---

## Container lifecycle and model prefetching

Restarting an ML container typically introduces two delays: downloading weights over the network, and compiling or loading model tensors into memory on the first user request.

`hf-backend` eliminates both delays with a two-phase build and boot workflow:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DOCKER BUILD TIME (BuildKit)                             │
│                                                             │
│  pip install requirements.txt                               │
│        │                                                    │
│  COPY registry.py prefetch.py                               │
│        │                                                    │
│  RUN python prefetch.py                                     │
│        ├─► Imports registered packages                      │
│        ├─► Dispatches warmup()                              │
│        └─► Weights download into /home/user/hf-cache        │
│        │                                                    │
│  ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1                │
│        │                                                    │
│  COPY . . (Code changes do not invalidate model cache)      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTAINER STARTUP (FastAPI Lifespan)                     │
│                                                             │
│  Uvicorn starts process [1]                                 │
│        │                                                    │
│  load_routers() mounts endpoints from registry.py           │
│        │                                                    │
│  Lifespan executes:                                         │
│        ├─► Iterates over loaded projects                    │
│        ├─► Calls warmup() in a background worker thread     │
│        └─► Enforces WARMUP_TIMEOUT_SECONDS per project      │
│        │                                                    │
│  All models loaded into RAM / dummy inferences complete     │
│        │                                                    │
│  Uvicorn opens port 7860 and accepts incoming requests      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SERVING RUNTIME                                          │
│                                                             │
│  First incoming inference request                           │
│        └─► Weights already resident in memory               │
│        └─► Initial response latency < 100 ms                │
└─────────────────────────────────────────────────────────────┘
```

### Build caching strategy

The Dockerfile separates dependency installation from code copying:
1. `requirements.txt` installs first.
2. `registry.py` and `prefetch.py` are copied, and `prefetch.py` runs. Model weights are saved inside `/home/user/hf-cache`.
3. `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are set, disabling runtime network calls to the Hub.
4. Application code (`main.py`, `dashboard.py`, tests) is copied last.

When you update gateway routing or edit documentation, Docker reuses the cached model layers. The Space rebuilds and restarts in seconds rather than redownloading multi-gigabyte checkpoints.

---

## Service contracts

Every subproject mounted into `hf-backend` follows two standard conventions.

### 1. Package structure and router export
A subproject must be installable as a Python package (pinned by Git tag in `requirements.in`) and export a FastAPI `APIRouter` instance:

```python
# target: "semantic_backend.router:router"
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def project_health():
    return {"status": "healthy"}
```

### 2. Startup warmup function
If the top-level package defines a callable named `warmup()`, the gateway lifespan executes it during container boot:

```python
# semantic_backend/__init__.py
def warmup():
    from .nlp_engine import warmup as _warmup
    return _warmup()
```

Warmup conventions:
* Loads lazy model checkpoints (tokenizers, classification heads, neural nets).
* Runs a synthetic inference pass to prime memory and execution graphs.
* Runs synchronously; the gateway wraps it in `asyncio.to_thread`.
* If a package omits `warmup()`, the gateway marks it as `"no warmup"` and proceeds normally.

---

## Middleware stack

Incoming requests traverse three layers of middleware before reaching subproject routers:

```
Request ──► [ SecurityHeadersMiddleware ]
                 │
                 ▼
            [ RequestLimitMiddleware ] ──(Exceeds limit)──► 413 Payload Too Large
                 │                     ──(Timeout)──────► 504 Gateway Timeout
                 ▼
            [ CORSMiddleware ]
                 │
                 ▼
            [ Subproject Router ]
```

1. `SecurityHeadersMiddleware`: Sets nosniff, Referrer-Policy, and a frame-ancestors CSP directive so Hugging Face Spaces can embed the UI without exposing it to third-party clickjacking. Adds HSTS on HTTPS requests.
2. `RequestLimitMiddleware`: Fast-fails requests larger than `MAX_BODY_SIZE_BYTES` using the `Content-Length` header (returning 413) or rejects unparseable headers (returning 400). On chunked or streaming requests, it tallies bytes on arrival and raises 413 if the limit is exceeded. Downstream handler execution is wrapped in `asyncio.wait_for`, returning 504 if a task exceeds `REQUEST_TIMEOUT_SECONDS`.
3. `CORSMiddleware`: Handles browser preflight checks against configured origins.

---

## Health and degradation model

The `/health` endpoint reports the aggregated status of the host and each mounted project:

```json
{
  "status": "healthy",
  "loaded": {
    "/semantic": "semantic_backend.router:router",
    "/heartflow": "heartflow_backend.router:router"
  },
  "failed": {},
  "warm_status": {
    "/semantic": "warmed",
    "/heartflow": "warmed"
  },
  "total_warmup_seconds": 6.484
}
```

### Status evaluation rules

| Condition | Overall Status | Serving Behavior |
| :--- | :--- | :--- |
| All registered projects mounted and all warmups succeeded | `healthy` | All endpoints operational |
| A project failed to mount, or a warmup threw an error or timed out | `degraded` | Failed project marked with reason; remaining projects serve traffic normally |
| No projects could be imported or loaded | `unhealthy` | Host runs but no domain routes are active |

* A project without a `warmup()` reports `"no warmup"` and remains `healthy`.
* If a warmup throws an exception or exceeds `WARMUP_TIMEOUT_SECONDS`, the gateway records `"failed: <reason>"` in `warm_status` and logs the traceback.
* Individual subproject failures are isolated; one broken dependency will not crash the host or prevent healthy services from serving traffic.
