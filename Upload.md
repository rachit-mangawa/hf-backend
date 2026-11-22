# Subproject Packaging & Deployment Runbook (`Upload.md`)

A step-by-step Standard Operating Procedure (SOP) for modifying any external Python backend repository, packaging it as an installable microservice, cutting SemVer release tags, and mounting it into the `hf-backend` gateway on Hugging Face Spaces.

---

## Quick Reference Checklist

- [ ] **Phase 1 (Upstream Service Repo)**:
  - [ ] 1. Move flat Python files into namespaced package directory `backend/<service>_backend/` (prevents `main.py` collisions).
  - [ ] 2. Create `backend/pyproject.toml` (declares package name, version, and dependencies).
  - [ ] 3. Expose `router = APIRouter()` in `router.py` with relative paths.
  - [ ] 4. Expose `GET /health` inside `router.py` for health checks.
  - [ ] 5. *(Optional)* Define `def warmup()` in `__init__.py` for pre-downloading model weights/checkpoints.
  - [ ] 6. Commit, tag with SemVer (`v1.0.0`), and push tags (`git push origin --tags`).
- [ ] **Phase 2 (Host Gateway `hf-backend` Repo)**:
  - [ ] 1. Add Git dependency with tag and subdirectory to `requirements.in`.
  - [ ] 2. Recompile `requirements.txt` via `uv pip compile`.
  - [ ] 3. Register route prefix in `registry.py`.
  - [ ] 4. Run verification tests (`pytest tests/test_host.py -v`).
  - [ ] 5. Commit and push to `main` (auto-triggers deployment to Hugging Face Space & GitHub Pages showcase).

---

## Phase 1: Upstream Subproject Setup (In Your Service Repo)

Follow these steps in your microservice repository:

### Step 1: Restructure files into a namespaced package
To prevent collisions with `hf-backend`'s root `main.py` and other microservices, move all flat `.py` files inside a dedicated package subdirectory (e.g. `backend/<service>_backend/`):

```text
my-service-repo/
├── backend/
│   ├── pyproject.toml                     <-- REQUIRED packaging manifest (Step 2)
│   └── my_service_backend/                <-- Dedicated namespace (prevents collisions)
│       ├── __init__.py                    <-- Exports warmup() and package root
│       ├── router.py                      <-- Exports router = APIRouter()
│       ├── config.py                      <-- Internal configuration
│       └── ... other service modules
```

> [!WARNING]
> Do NOT leave flat files like `main.py` directly under `backend/`. If multiple subprojects expose top-level `main.py` files, they will collide in the host gateway Python environment.

---

### Step 2: Add `backend/pyproject.toml`
Create `backend/pyproject.toml` to define your package metadata and dependencies using `setuptools`:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my_service_backend"
version = "1.0.0"
description = "My Service Backend Microservice"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "pydantic>=2.0.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["my_service_backend*"]
```

---

### Step 3: Define routes & `/health` endpoint in `router.py`
Inside `backend/my_service_backend/router.py`:
1. Instantiate FastAPI's `APIRouter`.
2. Define relative route paths (e.g. `/predict`, not `/my-service/predict` — the host gateway mounts the prefix automatically).
3. Expose a `GET /health` endpoint returning service status.

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "my_service_backend"
    }

@router.post("/predict")
def predict(payload: dict):
    # Core inference or business logic
    return {"status": "success", "result": payload}
```

---

### Step 4: Add startup `warmup()` in `__init__.py` (Optional)
If your service loads machine learning models (PyTorch, Transformers, ONNX) or pre-downloads assets, define a top-level `warmup()` callable in `backend/my_service_backend/__init__.py`:

```python
from .router import router

def warmup():
    """
    1. Called by prefetch.py during Docker build to bake weights into image cache.
    2. Called by the gateway lifespan on container boot before opening port 7860.
    """
    print("Pre-warming model weights into memory...")
    # Load model weights or download checkpoints here
```

---

### Step 5: Commit and release a Git SemVer tag
Commit your package changes and cut a version tag:

```bash
git add backend/
git commit -m "feat: package backend as installable microservice"
git tag -a v1.0.0 -m "Release v1.0.0 for hf-backend deployment"
git push origin main
git push origin --tags
```

> [!IMPORTANT]
> Make sure to run `git push origin --tags`. The host gateway pins dependencies by Git tag.

---

## Phase 2: Host Gateway Integration (In `hf-backend`)

Once your subproject repository is tagged on GitHub, integrate it into `hf-backend`:

### Step 1: Declare dependency in `requirements.in`
Open [`requirements.in`](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/requirements.in) and append your service Git repository URL with the release tag and `#subdirectory=backend`:

```text
git+https://github.com/<owner>/<repo>.git@v1.0.0#subdirectory=backend
```

*Example from existing services:*
```text
fastapi
uvicorn[standard]
pydantic
starlette
git+https://github.com/rachit-mangawa/Semantic-Comment-Analyze.git@v1.3#subdirectory=backend
git+https://github.com/rachit-mangawa/HEARTFLOW_OS.git@v1.2#subdirectory=backend
```

---

### Step 2: Recompile `requirements.txt`
Compile the pinned dependency graph using `uv` (fastest) or `pip-compile`:

```bash
uv pip compile requirements.in -o requirements.txt --python-version 3.11 --python-platform linux --extra-index-url https://download.pytorch.org/whl/cpu --emit-index-url --refresh
```

*(Alternative using pip-compile)*:
```bash
pip-compile requirements.in -o requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

---

### Step 3: Register route prefix in `registry.py`
Open [`registry.py`](file:///c:/Users/manga/Projects/github/rachit-mangawa/hf-backend/registry.py) and map your URL prefix to the router object using entrypoint format (`<package>.<module>:<router_attr>`):

```python
PROJECT_REGISTRY = {
    "/semantic": "semantic_backend.router:router",
    "/heartflow": "heartflow_backend.router:router",
    "/my-service": "my_service_backend.router:router",  # <--- Your new microservice
}
```

---

### Step 4: Run local verification test suite
Run the test suite to verify router resolution and mock loading:

```bash
pytest tests/test_host.py -v
```

Ensure all tests pass before pushing.

---

### Step 5: Commit and push to `main`
```bash
git add requirements.in requirements.txt registry.py
git commit -m "feat(deploy): mount my-service v1.0.0"
git push origin main
```

---

## Phase 3: Automated Deployment & Live Verification

Once pushed to `main`, GitHub Actions automates the entire lifecycle:

1. **Hugging Face Space Sync (`.github/workflows/deploy.yml`)**:
   - Isolates pure backend files on an orphan branch (`hf-sync`).
   - Pushes code to Hugging Face Space and triggers container rebuild.
   - Runs `prefetch.py` to bake `warmup()` weight caches into container layers.
   - Boots container and serves all registered microservices on port 7860.

2. **Frontend Website Sync (`.github/workflows/deploy_pages.yml`)**:
   - Automatically runs `python scripts/generate_frontend_registry.py`.
   - Auto-discovers newly registered services from `registry.py` and `requirements.in`.
   - Mounts live interactive cards and Swagger API explorers on [rachit-mangawa.github.io/hf-backend](https://rachit-mangawa.github.io/hf-backend/).

3. **Keep-Alive Ping (`.github/workflows/keep_alive.yml`)**:
   - Pings `GET /health` every 12 hours to prevent the free-tier Hugging Face Space from sleeping.

### Checking Live Endpoints

| Resource | URL Pattern | Expected Output |
| :--- | :--- | :--- |
| **Service Health** | `https://<hf-user>-<space-name>.hf.space/<prefix>/health` | `{"status": "healthy", ...}` |
| **Developer Console** | `https://<hf-user>-<space-name>.hf.space/status` | Visual dashboard of all mounted routes & warmup status |
| **Gateway Health** | `https://<hf-user>-<space-name>.hf.space/health` | `{"status": "healthy", "projects": [...]}` |
| **Showcase Website** | `https://rachit-mangawa.github.io/hf-backend/` | Live Swagger cards with interactive "Try Endpoint" |

---

## Common Pitfalls & Solutions

| Pitfall | Cause | Solution |
| :--- | :--- | :--- |
| `error: backend does not appear to be a Python project` | `pyproject.toml` or `setup.py` missing in `backend/` | Add `backend/pyproject.toml` with setuptools build configuration (Phase 1, Step 2). |
| Namespace collisions (e.g. `main.py` overwriting host `main.py`) | Flat `.py` files placed directly in `backend/` | Place all modules in a dedicated directory: `backend/<service>_backend/` (Phase 1, Step 1). |
| `pip install` fails with `fatal: Remote branch v1.0.0 not found` | Git tag was created locally but not pushed to remote | Push tags using `git push origin --tags` (Phase 1, Step 5). |
| Subproject marked as `"failed"` on `/status` console | Import error or uncaught exception in router or `warmup()` | Check space container logs or `/health` JSON output to identify missing dependencies. |
| Warmup TimeoutError | Weight downloading took longer than gateway limit | Set `WARMUP_TIMEOUT_SECONDS` (e.g. 600) under Space Settings > Variables and secrets. |
| Ephemeral data wiped on restart | Writing SQLite databases directly to local container filesystem | Mount `/data` persistent storage volume or sync database checkpoints via `storage.py`. |
