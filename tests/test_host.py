import asyncio
import logging
import os
import sys
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
        client = TestClient(main.app)

    assert "[/semantic] Successfully mounted at /semantic" in caplog.text
    assert "[/broken] Failed to mount router" in caplog.text

    res_health = client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "degraded"
    assert "/semantic" in health_data["loaded"]
    assert "/broken" in health_data["failed"]

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
    client = TestClient(main.app)

    res_health = client.get("/health")
    health_data = res_health.json()
    assert "/semantic" not in health_data["loaded"]
    assert "/semantic" not in health_data["failed"]

    assert client.get("/semantic/ping").status_code == 404


def test_healthy_status_when_all_load(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/semantic": "mock_semantic.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    client = TestClient(main.app)

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    assert "/semantic" in res_health.json()["loaded"]

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json() == res_health.json()


def test_real_registry():
    import importlib
    import registry
    importlib.reload(registry)
    assert list(registry.PROJECT_REGISTRY.keys()) == ["/semantic"]
    assert registry.PROJECT_REGISTRY["/semantic"] == "semantic_backend.router:router"

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    client = TestClient(main.app)

    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "/semantic" in data["loaded"]
    assert not data["failed"]

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json() == data
