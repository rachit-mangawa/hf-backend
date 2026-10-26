---
title: HF Backend
emoji: ⚡
colorFrom: gray
colorTo: pink
sdk: docker
app_port: 7860
---

# HF Backend

FastAPI gateway running on a Hugging Face Docker Space. The gateway mounts backend routers from standalone project repositories under designated URL prefixes.

For in-depth lifecycle mechanics, prefetch caching, and degradation semantics, see [ARCHITECTURE.md](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/ARCHITECTURE.md).

## How It Works

The host application does not contain domain business logic. Each subproject is maintained in its own repository, exposes a router in `<package>/router.py`, and installs as a standard Python package.

The host imports each router from `registry.py` and mounts it under its configured prefix. If a router fails to import, the host logs the error, records the failure, and keeps running for the remaining services.

```
/project-1/* -> HEARTFLOW_OS router
/semantic/*  -> Semantic Comment Analyzer router
/health      -> Host health and readiness status
```

## Adding a Service

Adding a new service takes two steps:

1. Register the URL prefix and target router in `registry.py`:
```python
PROJECT_REGISTRY = {
    "/semantic": "semantic_backend.router:router",
    "/new-service": "new_service.router:router",
}
```

2. Pin the Git tag or release in `requirements.in`, then compile `requirements.txt`:
```text
git+https://github.com/<owner>/<repo>.git@v1.0#subdirectory=backend
```

Pushing to `main` deploys the changes to Hugging Face and rebuilds the Space container.

## Configuration

Set these variables in the Space settings under **Variables and secrets**:

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | No | None | Comma-separated allowed origins. Wildcards (`*`) are ignored. |
| `DISABLE_PROJECTS` | No | None | Comma-separated prefixes to skip loading (e.g. `semantic`). |
| `MAX_BODY_SIZE_BYTES` | No | 10485760 (10 MB) | Maximum request body size before returning HTTP 413. |
| `REQUEST_TIMEOUT_SECONDS` | No | 60.0 | Request timeout before returning HTTP 504. |
| `WARMUP_TIMEOUT_SECONDS` | No | 300.0 | Warmup timeout per project during container boot. |
| `GITHUB_TOKEN` | Only for private repos | None | GitHub token passed as a build secret to clone private dependencies. |

Repository secrets for GitHub Actions:

| Secret | Description |
| :--- | :--- |
| `HF_BACKEND_SPACE` | Hugging Face token with write permissions to push code and restart the Space. |
| `HF_SPACE_URL` | Optional health URL for the keep-alive workflow. |

## Endpoints

### `GET /health`
Returns the status of the host and each registered project:

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
  "total_warmup_seconds": 6.48
}
```

Status outcomes:
- `healthy`: All registered projects mounted successfully and no warmup failed.
- `degraded`: One or more services failed to mount, or a warmup failed or timed out.
- `unhealthy`: No services loaded successfully.

Interactive documentation (`/docs`, `/redoc`, `/openapi.json`) is disabled for production hardening.

## Release Workflow

1. Test changes in the subproject repository.
2. Tag the release (`git tag v1.0`, `git push origin v1.0`).
3. Update the tag reference in `requirements.in` and recompile `requirements.txt`.
4. Run `pytest` locally to verify routing and warmups.
5. Push to `main`. The GitHub Actions workflow syncs the commit to Hugging Face and triggers a restart.
