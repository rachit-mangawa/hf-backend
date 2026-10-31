---
title: HF Backend
emoji: ⚡
colorFrom: gray
colorTo: pink
sdk: docker
app_port: 7860
---

# HF Backend Gateway

A FastAPI gateway hosted on Hugging Face Spaces. It mounts backend routers from external project repositories (`heartflow` and `semantic`) into one container, handling model pre-warming, request limits, security headers, and health monitoring.

Read [ARCHITECTURE.md](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/ARCHITECTURE.md) for details on build caching, lifespan warmups, and failure isolation.

---

## Quick links

| Resource | Path | Description |
| :--- | :--- | :--- |
| Interactive API docs | [`/project`](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/main.py#L112) | Swagger UI for all mounted services |
| Status dashboard | [`/status`](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/main.py#L189) | Dark-mode overview of mount status and warmup latencies |
| Health endpoint | [`/health`](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/main.py#L168) | JSON health and readiness payload |
| OpenAPI schema | `/openapi.json` | OpenAPI 3.1 specification |

---

## Mounted services

Each subproject lives in its own repository, installs as a Python package via git tag, and exports an `APIRouter`.

| Route Prefix | Service | Source Repository | Capabilities |
| :--- | :--- | :--- | :--- |
| `/heartflow` | HeartFlow OS | [`rachit-mangawa/HEARTFLOW_OS`](https://github.com/rachit-mangawa/HEARTFLOW_OS) | Vitals risk scoring, SHAP explanations, TinyML C export, model retraining |
| `/semantic` | Semantic Analyzer | [`rachit-mangawa/Semantic-Comment-Analyze`](https://github.com/rachit-mangawa/Semantic-Comment-Analyze) | RoBERTa sentiment analysis, intent classification, CSV batch streaming |

If one project fails to load or warm up, the gateway records the failure, marks overall status as `degraded`, and continues serving the remaining healthy services.

---

## Adding a new service

Adding a service takes two steps:

### 1. Register the router
Add the URL prefix and router target to `registry.py`:

```python
PROJECT_REGISTRY = {
    "/semantic": "semantic_backend.router:router",
    "/heartflow": "heartflow_backend.router:router",
    "/new-service": "new_service.router:router",
}
```

### 2. Pin the dependency
Add the git repository URL and release tag to `requirements.in`:

```text
git+https://github.com/<owner>/<repo>.git@v1.0#subdirectory=backend
```

Compile `requirements.txt` and push to `main`:

```bash
pip-compile requirements.in -o requirements.txt
git commit -am "feat: mount new-service router"
git push origin main
```

The GitHub Actions workflow syncs the code to the Hugging Face Space and rebuilds the container.

---

## Environment configuration

Configure these settings in the Hugging Face Space under **Settings > Variables and secrets**:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ENABLE_DOCS` | `true` | Toggles Swagger UI at `/project` and `/openapi.json`. |
| `DOCS_URL` | `/project` | Path where Swagger UI is served. |
| `OPENAPI_URL` | `/openapi.json` | Path where the OpenAPI specification is served. |
| `CORS_ALLOWED_ORIGINS` | *(localhost, Vercel)* | Comma-separated list of origins allowed for cross-origin requests. |
| `DISABLE_PROJECTS` | *(none)* | Comma-separated prefixes to skip at boot (e.g. `semantic`). |
| `MAX_BODY_SIZE_BYTES` | `10485760` (10 MB) | Maximum incoming request body size before returning HTTP 413. |
| `REQUEST_TIMEOUT_SECONDS` | `60.0` | Timeout per request before returning HTTP 504. |
| `WARMUP_TIMEOUT_SECONDS` | `300.0` | Maximum time allowed for each package warmup call at boot. |
| `GITHUB_TOKEN` | *(none)* | Personal access token used during Docker build to clone private repos. |

---

## Endpoints and responses

### `GET /health`
Returns the status of the host and each mounted project:

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
  "total_warmup_seconds": 6.48
}
```

Status values:
* `healthy`: Every registered router mounted and warmed up without errors.
* `degraded`: One or more services failed to mount or threw a warmup error. Surviving services remain operational.
* `unhealthy`: No registered services loaded.

### `GET /` and `GET /status`
* Browser requests return an HTML status page with active routes, warmup timings, and links.
* API clients sending `Accept: application/json` or `?format=json` receive the health JSON object.

### `GET /project`
Interactive Swagger UI documentation. Routes are grouped by service:
* HeartFlow OS: `/heartflow/predict`, `/heartflow/explain`, `/heartflow/metrics`, `/heartflow/dataset`, `/heartflow/export_tinyml`, `/heartflow/retrain`
* Semantic Comment Analyzer: `/semantic/analyze`, `/semantic/batch`, `/semantic/health`
* Host Gateway: `/health`, `/status`, `/`

---

## Security controls

The gateway applies several safeguards to every connection:
* Security headers: sets `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 0`, and `Referrer-Policy: strict-origin-when-cross-origin`. Sets `Content-Security-Policy: frame-ancestors` so Hugging Face Spaces can embed the page while blocking third-party iframes. Injects `Strict-Transport-Security` on HTTPS connections.
* Fast payload check: rejects requests that exceed `MAX_BODY_SIZE_BYTES` upfront, returning HTTP 413 before the body loads into memory. Returns HTTP 400 if `Content-Length` is not a valid number.
* Chunk metering: tracks arriving bytes on unbuffered streams to catch oversized uploads that omit `Content-Length`.
* Timeout guard: bounds downstream route execution with `REQUEST_TIMEOUT_SECONDS`, returning HTTP 504 if a handler hangs.

---

## Local development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the gateway locally
uvicorn main:app --reload --port 7860

# Run automated tests
pytest tests
```
