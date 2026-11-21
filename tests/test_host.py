import asyncio
import logging
import os
import sys
import time
import types

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


def create_mock_modules():
    sem = types.ModuleType("mock_semantic")
    sem_router_mod = types.ModuleType("mock_semantic.router")
    r = APIRouter()

    @r.get("/ping")
    def ping():
        return {"project": "semantic", "status": "ok"}

    @r.post("/echo")
    def echo(data: dict):
        return {"project": "semantic", "echo": data}

    @r.get("/slow")
    async def slow():
        await asyncio.sleep(0.5)
        return {"status": "finished"}

    sem_router_mod.router = r
    sem.router = sem_router_mod
    sem.warmup = lambda: True
    sys.modules["mock_semantic"] = sem
    sys.modules["mock_semantic.router"] = sem_router_mod


def test_host_with_mocks(monkeypatch, caplog):
    create_mock_modules()

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://allowed.com,https://example.com")
    monkeypatch.setenv("MAX_BODY_SIZE_BYTES", "1024")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
        "/broken": "nonexistent_module.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    with caplog.at_level(logging.INFO):
        import main
        with TestClient(main.app) as client:
            assert "[/semantic] Successfully mounted at /semantic" in caplog.text
            assert "[/broken] Failed to mount router" in caplog.text

            res_health = client.get("/health")
            assert res_health.status_code == 200
            health_data = res_health.json()
            assert health_data["status"] == "degraded"
            assert "/semantic" in health_data["loaded"]
            assert "/broken" in health_data["failed"]
            assert health_data["warm_status"]["/semantic"] == "warmed"

            # Verify GET / points nowhere but an empty message
            res_root = client.get("/")
            assert res_root.status_code == 200
            assert res_root.json() == {"message": ""}

            res_sem = client.get("/semantic/ping")
            assert res_sem.status_code == 200
            assert res_sem.json() == {"project": "semantic", "status": "ok"}

            # Verify global doc listings are vanished
            for doc_url in ["/docs", "/redoc", "/project", "/projects", "/openapi.json"]:
                assert client.get(doc_url).status_code == 404

            # Verify /{project} points to all of the project's APIs
            res_sem_docs = client.get("/semantic", headers={"Accept": "text/html"})
            assert res_sem_docs.status_code == 200
            assert "swagger" in res_sem_docs.text.lower() or "text/html" in res_sem_docs.headers.get("content-type", "")

            res_sem_json = client.get("/semantic")
            assert res_sem_json.status_code == 200
            sem_json_data = res_sem_json.json()
            assert sem_json_data["prefix"] == "/semantic"
            assert any(ep["path"] == "/semantic/ping" for ep in sem_json_data["endpoints"])

            res_sem_openapi = client.get("/semantic/openapi.json")
            assert res_sem_openapi.status_code == 200
            assert "/semantic/ping" in res_sem_openapi.json()["paths"]
            assert "/broken" not in str(res_sem_openapi.json()["paths"])

            # Security headers verification
            assert res_health.headers.get("x-content-type-options") == "nosniff"
            assert res_health.headers.get("x-xss-protection") == "0"
            assert res_health.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
            assert "frame-ancestors" in res_health.headers.get("content-security-policy", "")

            # HSTS header when forwarded proto is https
            res_https = client.get("/health", headers={"x-forwarded-proto": "https"})
            assert "max-age" in res_https.headers.get("strict-transport-security", "")

            # Favicon 204 endpoint
            assert client.get("/favicon.ico").status_code == 204

            # Malformed content-length test
            res_bad_cl = client.post("/semantic/echo", headers={"content-length": "invalid-len"})
            assert res_bad_cl.status_code == 400

            cors_allowed = client.get(
                "/semantic/ping",
                headers={"Origin": "https://allowed.com"}
            )
            assert cors_allowed.status_code == 200
            assert cors_allowed.headers.get("access-control-allow-origin") == "https://allowed.com"

            cors_rejected = client.get(
                "/semantic/ping",
                headers={"Origin": "https://disallowed.com"}
            )
            assert cors_rejected.headers.get("access-control-allow-origin") is None

            oversized_data = {"text": "a" * 2000}
            res_oversized = client.post("/semantic/echo", json=oversized_data)
            assert res_oversized.status_code == 413

            res_slow = client.get("/semantic/slow")
            assert res_slow.status_code == 504


def test_kill_switch(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("DISABLE_PROJECTS", "semantic")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res_health = client.get("/health")
        health_data = res_health.json()
        assert "/semantic" not in health_data["loaded"]
        assert "/semantic" not in health_data["failed"]

        assert client.get("/semantic/ping").status_code == 404


def test_warmup_success(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res_health = client.get("/health")
        assert res_health.status_code == 200
        data = res_health.json()
        assert data["status"] == "healthy"
        assert data["loaded"]["/semantic"] == "mock_semantic.router:router"
        assert data["warm_status"]["/semantic"] == "warmed"
        assert data["total_warmup_seconds"] >= 0

        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json() == {"message": ""}


def test_warmup_exception(monkeypatch):
    sem = types.ModuleType("err_semantic")
    sem_router_mod = types.ModuleType("err_semantic.router")
    r = APIRouter()

    @r.get("/ping")
    def ping():
        return {"status": "ok"}

    sem_router_mod.router = r
    sem.router = sem_router_mod

    def fail_warmup():
        raise RuntimeError("Weights file corrupted")

    sem.warmup = fail_warmup
    sys.modules["err_semantic"] = sem
    sys.modules["err_semantic.router"] = sem_router_mod

    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/err": "err_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["loaded"]["/err"] == "err_semantic.router:router"
        assert "failed: RuntimeError" in data["warm_status"]["/err"]

        res_ping = client.get("/err/ping")
        assert res_ping.status_code == 200


def test_warmup_timeout(monkeypatch):
    fast = types.ModuleType("fast_proj")
    fast_router = types.ModuleType("fast_proj.router")
    rf = APIRouter()
    @rf.get("/ping")
    def fast_ping():
        return {"fast": "ok"}
    fast_router.router = rf
    fast.router = fast_router
    fast.warmup = lambda: True
    sys.modules["fast_proj"] = fast
    sys.modules["fast_proj.router"] = fast_router

    slow = types.ModuleType("slow_proj")
    slow_router = types.ModuleType("slow_proj.router")
    rs = APIRouter()
    @rs.get("/ping")
    def slow_ping():
        return {"slow": "ok"}
    slow_router.router = rs
    slow.router = slow_router

    def slow_warmup():
        time.sleep(1.0)
        return True

    slow.warmup = slow_warmup
    sys.modules["slow_proj"] = slow
    sys.modules["slow_proj.router"] = slow_router

    monkeypatch.setenv("DISABLE_PROJECTS", "")
    monkeypatch.setenv("WARMUP_TIMEOUT_SECONDS", "0.1")

    import registry
    registry.PROJECT_REGISTRY = {
        "/slow": "slow_proj.router:router",
        "/fast": "fast_proj.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert "failed: TimeoutError" in data["warm_status"]["/slow"]
        assert data["warm_status"]["/fast"] == "warmed"
        # Others still serve
        assert client.get("/fast/ping").status_code == 200
        assert client.get("/slow/ping").status_code == 200


def test_project_without_warmup(monkeypatch):
    nowarm = types.ModuleType("nowarm_proj")
    nowarm_router = types.ModuleType("nowarm_proj.router")
    r = APIRouter()
    @r.get("/ping")
    def ping():
        return {"nowarm": "ok"}
    nowarm_router.router = r
    nowarm.router = nowarm_router
    sys.modules["nowarm_proj"] = nowarm
    sys.modules["nowarm_proj.router"] = nowarm_router

    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/nowarm": "nowarm_proj.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["warm_status"]["/nowarm"] == "no warmup"
        assert client.get("/nowarm/ping").status_code == 200


def test_real_registry():
    import importlib
    import registry
    importlib.reload(registry)
    assert set(registry.PROJECT_REGISTRY.keys()) == {"/semantic", "/heartflow"}
    assert registry.PROJECT_REGISTRY["/semantic"] == "semantic_backend.router:router"
    assert registry.PROJECT_REGISTRY["/heartflow"] == "heartflow_backend.router:router"

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "/semantic" in data["loaded"]
        assert "/heartflow" in data["loaded"]
        assert not data["failed"]
        assert data["warm_status"]["/semantic"] == "warmed"
        assert data["warm_status"]["/heartflow"] == "warmed"
        assert data["total_warmup_seconds"] >= 0

        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json() == {"message": ""}

        # Check Semantic /health endpoint reports models_loaded
        res_sem = client.get("/semantic/health")
        assert res_sem.status_code == 200
        sem_data = res_sem.json()
        assert sem_data["status"] == "healthy"
        assert sem_data["service"] == "semantic_backend"
        assert sem_data["models_loaded"]["embedding"] is True
        assert sem_data["models_loaded"]["classifier_head"] is True
        assert sem_data["models_loaded"]["sentiment"] is True

        # Check Heartflow /health endpoint reports models_loaded
        res_hf = client.get("/heartflow/health")
        assert res_hf.status_code == 200
        hf_data = res_hf.json()
        assert hf_data["status"] == "Healthy"
        assert hf_data["models_loaded"] is True

        # Check global /project and /projects are vanished
        assert client.get("/project").status_code == 404
        assert client.get("/projects").status_code == 404

        # Check /{project} points to all APIs of that project
        res_sem_p = client.get("/semantic")
        assert res_sem_p.status_code == 200
        assert res_sem_p.json()["prefix"] == "/semantic"
        assert any(e["path"] == "/semantic/health" for e in res_sem_p.json()["endpoints"])

        res_hf_p = client.get("/heartflow")
        assert res_hf_p.status_code == 200
        assert res_hf_p.json()["prefix"] == "/heartflow"
        assert any(e["path"] == "/heartflow/health" for e in res_hf_p.json()["endpoints"])


def test_status_page_and_content_negotiation():
    create_mock_modules()
    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        # 1. Dedicated /status endpoint always returns HTML
        res_status = client.get("/status")
        assert res_status.status_code == 200
        assert "text/html" in res_status.headers.get("content-type", "")
        assert "HF Backend" in res_status.text
        assert "Registered Services" in res_status.text

        # 2. Normal / points nowhere but an empty message
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json() == {"message": ""}

        res_root_html = client.get("/", headers={"Accept": "text/html"})
        assert res_root_html.status_code == 200
        assert res_root_html.json() == {"message": ""}

        # 3. Global /project and /projects are vanished
        assert client.get("/project").status_code == 404
        assert client.get("/projects").status_code == 404

        # 4. /{project} points to all APIs for that project
        res_proj_html = client.get("/semantic", headers={"Accept": "text/html"})
        assert res_proj_html.status_code == 200
        assert "swagger" in res_proj_html.text.lower() or "text/html" in res_proj_html.headers.get("content-type", "")

        res_proj_json = client.get("/semantic?format=json")
        assert res_proj_json.status_code == 200
        assert res_proj_json.json()["prefix"] == "/semantic"
        assert any(ep["path"] == "/semantic/ping" for ep in res_proj_json.json()["endpoints"])


def test_host_websocket_through_middleware(monkeypatch):
    from fastapi import WebSocket

    ws_pkg = types.ModuleType("mock_ws_pkg")
    ws_router_mod = types.ModuleType("mock_ws_pkg.router")
    r = APIRouter()

    @r.websocket("/ws")
    async def dummy_ws(websocket: WebSocket):
        await websocket.accept()
        for i in range(3):
            await websocket.send_text(f"frame-{i}")
        await websocket.close()

    ws_router_mod.router = r
    ws_pkg.router = ws_router_mod
    ws_pkg.warmup = lambda: True
    sys.modules["mock_ws_pkg"] = ws_pkg
    sys.modules["mock_ws_pkg.router"] = ws_router_mod

    monkeypatch.setenv("DISABLE_PROJECTS", "")
    monkeypatch.setenv("MAX_BODY_SIZE_BYTES", "1024")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5.0")

    import registry
    registry.PROJECT_REGISTRY = {
        "/mockws": "mock_ws_pkg.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        with client.websocket_connect("/mockws/ws") as ws:
            frames = [ws.receive_text() for _ in range(3)]
            assert frames == ["frame-0", "frame-1", "frame-2"]


def test_docs_killswitch(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("ENABLE_DOCS", "false")
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        assert client.get("/project").status_code == 404
        assert client.get("/projects").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/semantic/openapi.json").status_code == 404


def test_storage_bucket_configured(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("STORAGE_BUCKET_NAME", "my-ml-models-bucket")
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://s3.hf.co")
    monkeypatch.setenv("STORAGE_REGION", "us-east-1")
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    info = main.get_gateway_info()
    assert info["storage_bucket"] == "my-ml-models-bucket"
    assert info["storage_endpoint"] == "https://s3.hf.co"
    assert info["storage_region"] == "us-east-1"

    with TestClient(main.app) as client:
        res_status = client.get("/status")
        assert res_status.status_code == 200
        assert "my-ml-models-bucket" in res_status.text
        assert "Configured" in res_status.text


def test_storage_bucket_default_unset(monkeypatch):
    create_mock_modules()
    monkeypatch.delenv("STORAGE_BUCKET_NAME", raising=False)
    monkeypatch.delenv("BUCKET_NAME", raising=False)
    monkeypatch.delenv("HF_BUCKET_NAME", raising=False)
    monkeypatch.delenv("STORAGE_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("STORAGE_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    info = main.get_gateway_info()
    assert info["storage_bucket"] is None
    assert info["storage_endpoint"] is None
    assert info["storage_region"] is None

    with TestClient(main.app) as client:
        res_status = client.get("/status")
        assert res_status.status_code == 200
        assert "Not Configured" in res_status.text


def test_generate_frontend_registry():
    from scripts.generate_frontend_registry import sync_registry
    projects = sync_registry()
    prefixes = [p["prefix"] for p in projects]
    assert "/semantic" in prefixes
    assert "/heartflow" in prefixes
    for p in projects:
        assert "name" in p
        assert "prefix" in p
        assert "target" in p
        assert "description" in p


def test_storage_module_helpers(monkeypatch, tmp_path):
    import storage
    
    # 1. Unset bucket
    monkeypatch.delenv("STORAGE_BUCKET_NAME", raising=False)
    monkeypatch.delenv("BUCKET_NAME", raising=False)
    monkeypatch.delenv("HF_BUCKET_NAME", raising=False)
    info = storage.get_storage_info()
    assert info["configured"] is False
    assert info["bucket_name"] is None

    # Unconfigured download & upload should safely return False
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("hello")
    assert storage.download_from_bucket("remote/file.txt", tmp_path / "dest.txt") is False
    assert storage.upload_to_bucket(dummy_file, "remote/file.txt") is False

    # 2. Configured bucket info
    monkeypatch.setenv("STORAGE_BUCKET_NAME", "my-org/my-bucket")
    monkeypatch.setenv("STORAGE_ENDPOINT_URL", "https://s3.hf.co")
    monkeypatch.setenv("STORAGE_REGION", "us-east-1")
    info = storage.get_storage_info()
    assert info["configured"] is True
    assert info["bucket_name"] == "my-org/my-bucket"
    assert info["endpoint_url"] == "https://s3.hf.co"
    assert info["region"] == "us-east-1"

