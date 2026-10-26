# Architecture Guide

This document describes the design, execution lifecycle, and operational contracts of `hf-backend`.

## System Overview

`hf-backend` is an aggregation gateway deployed on a Hugging Face Docker Space. Rather than hosting business logic directly, it mounts domain-specific routers from separate repositories under dedicated URL prefixes.

```
Internet Request
       │
       ▼
[ Hugging Face Edge Proxy ] (:443)
       │
       ▼
[ Uvicorn Worker ] (:7860)
       │
       ▼
[ RequestLimitMiddleware ] (Body size cap + request timeout)
       │
       ├── /health ─────────► [ Host Health Monitor ]
       ├── /semantic/* ─────► [ Mounted Subproject: Semantic-Comment-Analyze ]
       └── /<prefix>/* ─────► [ Future Mounted Services ]
```

The gateway handles shared infrastructure requirements:
- Dynamic discovery and mounting of standalone service packages.
- Early input validation (payload length enforcement before buffering).
- Global request timeouts preventing worker stalls.
- Zero-cold-start initialization through baked image weights and startup warmups.
- Centralized health checks reflecting mount status and model readiness.

---

## The Cold-Start Problem and Solution

Machine learning services on serverless or restart-prone container hosts typically suffer from two cold-start stages:

1. **Storage delay**: Weights must be pulled from Hugging Face Hub over the network at first boot, taking anywhere from 30 seconds to several minutes.
2. **Compute delay**: Models must be deserialized, moved to memory, and compiled or JIT-traced on the first inference call.

`hf-backend` eliminates both delays across container restarts.

```
┌─────────────────────────────────────────────────────────────┐
│ 1. BUILD TIME (Docker Build via BuildKit)                   │
│                                                             │
│  pip install requirements.txt                               │
│        │                                                    │
│  COPY registry.py prefetch.py                               │
│        │                                                    │
│  RUN python prefetch.py                                     │
│        └─► Imports mounted packages                         │
│        └─► Calls warmup()                                   │
│        └─► Models download into /home/user/hf-cache         │
│        │                                                    │
│  ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1                │
│        │                                                    │
│  COPY . . (App code changes never bust prefetch cache)      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTAINER STARTUP (Lifespan Hook)                        │
│                                                             │
│  Uvicorn starts process [1]                                 │
│        │                                                    │
│  load_routers() mounts endpoints from registry.py           │
│        │                                                    │
│  Lifespan executes:                                         │
│        ├─► Iterates over loaded projects                    │
│        ├─► Dispatches warmup() in a background thread       │
│        └─► Applies WARMUP_TIMEOUT_SECONDS per project       │
│        │                                                    │
│  All warmups finish / weights load into memory              │
│        │                                                    │
│  Server opens socket :7860 and accepts incoming traffic     │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SERVING RUNTIME                                          │
│                                                             │
│  First incoming inference request (e.g. /semantic/analyze)  │
│        └─► Models already resident in memory                │
│        └─► Response latency < 100 ms                        │
└─────────────────────────────────────────────────────────────┘
```

### Layer Caching Details

The build uses a two-phase copy strategy:
1. `requirements.txt` is installed first.
2. `registry.py` and `prefetch.py` are copied, then `prefetch.py` executes. Model weights are stored in `/home/user/hf-cache`.
3. `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` are exported to lock down the filesystem at runtime.
4. Application code (`main.py`, tests, documentation) is copied last.

When you modify routing logic or update documentation, Docker reuses the cached model layers. The Space rebuilds and restarts in seconds rather than downloading multi-gigabyte checkpoints repeatedly.

---

## Service Contracts

Every service mounted into `hf-backend` follows a standard contract.

### 1. Package Structure
A subproject must be installable as a Python package (e.g., via git tag in `requirements.txt`) and expose a FastAPI `APIRouter` instance:

```python
# target: "semantic_backend.router:router"
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def project_health():
    ...
```

### 2. Startup Warmup
If the top-level package defines a callable named `warmup()`, the host lifespan executes it at boot time:

```python
# semantic_backend/__init__.py
def warmup():
    from .nlp_engine import warmup as _warmup
    return _warmup()
```

Warmup conventions:
- Must load lazy checkpoints (embeddings, classification heads, tokenizers).
- Runs one dummy inference pass through the primary execution path.
- Runs synchronously; the host wraps execution in `asyncio.to_thread`.
- If a project does not define `warmup()`, the host records `"no warmup"` and continues without error.

---

## Guard Middleware

The host places `RequestLimitMiddleware` in front of all endpoints:

1. **Streaming Body Guard**:
   Inspects the `Content-Length` header upfront. If the declared size exceeds `MAX_BODY_SIZE_BYTES` (default 10 MB), the connection returns HTTP 413 immediately. For chunked or undeclared streams, chunks are counted on arrival, raising HTTP 413 before memory exhaustion occurs.

2. **Request Timeout**:
   Wraps downstream route evaluation with `asyncio.wait_for`. If route processing exceeds `REQUEST_TIMEOUT_SECONDS` (default 60.0s), the gateway returns an HTTP 504 Gateway Timeout.

---

## Health and Degradation Model

The root `/health` and `/` endpoints report the aggregate status of all registered projects:

```json
{
  "status": "healthy",
  "loaded": {
    "/semantic": "semantic_backend.router:router"
  },
  "failed": {},
  "warm_status": {
    "/semantic": "warmed"
  },
  "total_warmup_seconds": 6.484
}
```

### Evaluation Logic

```
   ┌──────────────────────────────────────────────┐
   │ Any projects failed to mount?                │
   │                OR                            │───► "degraded"
   │ Any project warmup failed / timed out?       │
   └──────────────────────────────────────────────┘
                          │ No
                          ▼
   ┌──────────────────────────────────────────────┐
   │ Are there any loaded projects?               │───► No: "unhealthy"
   └──────────────────────────────────────────────┘
                          │ Yes
                          ▼
                     "healthy"
```

- A project without a `warmup()` reports `"no warmup"` and remains `"healthy"`.
- If a warmup throws an exception or exceeds `WARMUP_TIMEOUT_SECONDS`, the host logs the error, marks the project as `"failed: <reason>"`, and marks overall status as `"degraded"`.
- Surviving projects continue serving traffic even if an adjacent service is degraded.
