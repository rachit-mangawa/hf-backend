---
title: HF Backend
emoji: ⚡
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
---

# HF Backend

FastAPI host running on a Hugging Face Docker Space. It mounts backend routers from separate project repositories under specific URL prefixes.

## How it works

The host application does not define business logic. Each subproject lives in its own repository, exposes a router in `<package>/router.py`, and is installed as a Python package.

The host imports each router dynamically from `registry.py` and mounts it under a prefix. If an individual router fails to import, the host logs the error, records the failure, and keeps running for the other services.

```
/project-1/* -> HEARTFLOW_OS backend router
/project-2/* -> Semantic Comment Analyzer backend router
/health      -> Host health status
```

## Adding a project

Adding a new service takes two steps:

1. Add the prefix and router path to `registry.py`:
```python
PROJECT_REGISTRY = {
    "/project-1": "heartflow_backend.router:router",
    "/project-2": "semantic_backend.router:router",
    "/project-3": "new_project.router:router",
}
```

2. Add the pinned Git tag to `requirements.txt`:
```text
git+https://github.com/<user>/<repo>.git@v1.0#subdirectory=backend
```

Pushing to `main` syncs the change to Hugging Face and rebuilds the Space container.

## Configuration

Set these in the Space settings under **Variables and secrets**:

| Variable | Required | Default | Notes |
| :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | No | None | Comma-separated allowed origins. Wildcards (`*`) are ignored. |
| `DISABLE_PROJECTS` | No | None | Comma-separated prefixes to skip loading (e.g. `project-2`). |
| `MAX_BODY_SIZE_BYTES` | No | 10485760 (10 MB) | Max request body size before returning 413. |
| `REQUEST_TIMEOUT_SECONDS` | No | 60.0 | Request timeout before returning 504. |
| `WARMUP_TIMEOUT_SECONDS` | No | 300.0 | Warmup timeout per project in worker thread before timing out. |
| `GITHUB_TOKEN` | Only for private repos | None | GitHub token passed as a build secret to clone private dependencies. |

GitHub repository secrets (used by GitHub Actions):

| Secret | Notes |
| :--- | :--- |
| `HF_BACKEND_SPACE` | Hugging Face write token used to push code and trigger Space restart. |
| `HF_SPACE_URL` | Optional. Health URL for the keep-alive workflow. |

## Endpoints

### `GET /health`
Returns the status of the host and each registered project.

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
  "total_warmup_seconds": 6.35
}
```

If any service fails to load or warm up, `status` changes to `"degraded"` or `"unhealthy"` and the error is listed under `"failed"` or `"warm_status"`.

Interactive documentation (`/docs`, `/redoc`, `/openapi.json`) is disabled.

## Release workflow

1. Test changes in the project repository using its `dev.py`.
2. Tag the release (`git tag v1.0`, `git push origin v1.0`).
3. Update the tag in this repo's `requirements.txt`.
4. Push to `main`. The GitHub Actions workflow pushes to Hugging Face and restarts the Space.
