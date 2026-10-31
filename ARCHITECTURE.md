# Architecture Guide

Technical design, container lifecycle, and integration contracts for `hf-backend`.

---

## System overview

`hf-backend` is an aggregation gateway hosted in a Hugging Face Docker Space. It mounts independent Python package routers under dedicated URL prefixes, providing shared networking, security, documentation, and telemetry infrastructure.

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
[ SecurityHeadersMiddleware ] (HSTS, nosniff, frame-ancestors CSP)
       │
       ▼
[ RequestLimitMiddleware ] (Body size cap + request execution timeout)
       │
       ├── /project ────────► [ Interactive Swagger UI (OpenAPI 3.1) ]
       ├── /status ─────────► [ Developer Console (HTML) ]
       ├── /health ─────────► [ Aggregated Health Monitor (JSON) ]
       │
       ├── /<prefix-a>/* ───► [ Subproject A Router (e.g. /heartflow) ]
       ├── /<prefix-b>/* ───► [ Subproject B Router (e.g. /semantic) ]
       └── /<prefix-n>/* ───► [ Dynamically Mounted Future Subprojects ]
```

The gateway handles shared host responsibilities:
* Dynamic discovery and isolated mounting of external service packages.
* Inbound payload verification before buffering data into memory.
* Global request timeouts to avoid thread starvation.
* Zero-cold-start inference by baking weights at build time and warming them up at boot.
* Centralized health tracking reflecting route mounting and model readiness.

---

## Container lifecycle and model prefetching

Restarting an ML container typically introduces two delays: downloading weights over the network, and compiling or loading model tensors into memory on the first user request.

`hf-backend` avoids both delays with a two-phase build and boot workflow:

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

The Dockerfile separates dependency installation from application code:
1. `requirements.txt` installs first.
2. `registry.py` and `prefetch.py` are copied, and `prefetch.py` runs. Model weights are saved inside `/home/user/hf-cache`.
3. `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are set, disabling runtime network calls to the Hugging Face Hub.
4. Application code (`main.py`, `dashboard.py`, tests) is copied last.

When you update gateway routing or documentation, Docker reuses the cached model layers. The Space rebuilds and restarts in seconds rather than redownloading multi-gigabyte checkpoints.

---

## Subproject contracts

Every subproject mounted into `hf-backend` follows two standard conventions.

### 1. Package structure and router export
A subproject must be installable as a Python package (pinned by Git tag in `requirements.in`) and export a FastAPI `APIRouter` instance:

```python
# target: "my_package.router:router"
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def service_health():
    return {"status": "healthy"}
```

The gateway imports the router via setuptools entrypoint notation (`<module_path>:<attribute_name>`) and mounts it using `app.include_router(router, prefix=prefix)`.

### 2. Startup warmup function (optional)
If the top-level package defines a callable named `warmup()`, the gateway lifespan executes it during container boot:

```python
# my_package/__init__.py
def warmup():
    from .model_engine import load_weights
    load_weights()
```

Warmup conventions:
* Loads lazy model checkpoints (tokenizers, classification heads, neural nets).
* Runs a synthetic inference pass to compile compute graphs and prime memory.
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

1. **`SecurityHeadersMiddleware`**:
   * Sets `X-Content-Type-Options: nosniff` to block MIME sniffing.
   * Sets `X-XSS-Protection: 0` to disable problematic legacy browser filters.
   * Sets `Referrer-Policy: strict-origin-when-cross-origin`.
   * Sets `Content-Security-Policy: frame-ancestors 'self' https://huggingface.co https://*.hf.space;` allowing the Hugging Face Space UI to embed the service while blocking third-party clickjacking.
   * Injects `Strict-Transport-Security` on HTTPS connections.

2. **`RequestLimitMiddleware`**:
   * Inspects `Content-Length` headers immediately, returning HTTP 413 before large payloads enter application memory. Rejects malformed headers with HTTP 400.
   * On chunked or streaming requests, it counts incoming bytes and aborts with HTTP 413 if the total exceeds `MAX_BODY_SIZE_BYTES`.
   * Wraps downstream request processing in `asyncio.wait_for`, returning HTTP 504 if execution exceeds `REQUEST_TIMEOUT_SECONDS`.

3. **`CORSMiddleware`**:
   * Handles browser preflight checks against configured allowed origins.

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
* Individual subproject failures are isolated; a broken dependency in one subproject will not crash the host or prevent healthy services from serving traffic.

---

## Developer console & route introspection

The `/status` endpoint renders an interactive developer console. It dynamically introspects `app.routes` at runtime to group endpoints under their mounted prefixes.

Features:
* **Live latency counter**: Measures round-trip ping time to `/health` with an auto-refresh toggle (10s polling interval) and manual reload control.
* **Route explorer**: Displays HTTP method pills (`GET`, `POST`, `WS`), endpoint paths, one-click cURL generator, and direct links to Swagger UI.
* **Instant search**: Keyboard-driven filter (`/`) to search across services and paths instantly.
* **Gateway specifications**: Shows active payload caps, execution timeouts, docs paths, and CORS origins.
* **Raw JSON inspector**: Formatted view of the `/health` response with a copy-to-clipboard button.
* **Zero external CDN dependencies**: Uses inline CSS and vanilla JavaScript, ensuring functionality offline and under strict Content Security Policies.
