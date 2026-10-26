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

            # Verify GET / returns same info as /health
            res_root = client.get("/")
            assert res_root.status_code == 200
            assert res_root.json() == health_data

            res_sem = client.get("/semantic/ping")
            assert res_sem.status_code == 200
            assert res_sem.json() == {"project": "semantic", "status": "ok"}

            for doc_url in ["/docs", "/redoc", "/openapi.json"]:
                assert client.get(doc_url).status_code == 404

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
        assert res_root.json() == data


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
        assert data["status"] == "degraded"
        assert data["warm_status"]["/nowarm"] == "no warmup"
        assert client.get("/nowarm/ping").status_code == 200


def test_real_registry():
    import importlib
    import registry
    importlib.reload(registry)
    assert list(registry.PROJECT_REGISTRY.keys()) == ["/semantic"]
    assert registry.PROJECT_REGISTRY["/semantic"] == "semantic_backend.router:router"

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    with TestClient(main.app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "/semantic" in data["loaded"]
        assert not data["failed"]
        assert data["warm_status"]["/semantic"] == "warmed"
        assert data["total_warmup_seconds"] >= 0

        res_root = client.get("/")
        assert res_root.status_code == 200
        assert res_root.json() == data

        # Check Semantic /health endpoint reports models_loaded
        res_sem = client.get("/semantic/health")
        assert res_sem.status_code == 200
        sem_data = res_sem.json()
        assert sem_data["status"] == "healthy"
        assert sem_data["service"] == "semantic_backend"
        assert sem_data["models_loaded"]["embedding"] is True
        assert sem_data["models_loaded"]["classifier_head"] is True
        assert sem_data["models_loaded"]["sentiment"] is True
