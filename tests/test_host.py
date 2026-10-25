import asyncio
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import logging
import types
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient


def create_mock_modules():
    p1 = types.ModuleType("mock_p1")
    p1_router_mod = types.ModuleType("mock_p1.router")
    r1 = APIRouter()

    @r1.get("/ping")
    def ping_p1():
        return {"project": "p1", "status": "ok"}

    @r1.post("/echo")
    def echo_p1(data: dict):
        return {"project": "p1", "echo": data}

    @r1.get("/slow")
    async def slow_p1():
        await asyncio.sleep(0.5)
        return {"status": "finished"}

    p1_router_mod.router = r1
    p1.router = p1_router_mod
    sys.modules["mock_p1"] = p1
    sys.modules["mock_p1.router"] = p1_router_mod

    p2 = types.ModuleType("mock_p2")
    p2_router_mod = types.ModuleType("mock_p2.router")
    r2 = APIRouter()

    @r2.get("/ping")
    def ping_p2():
        return {"project": "p2", "status": "ok"}

    p2_router_mod.router = r2
    p2.router = p2_router_mod
    sys.modules["mock_p2"] = p2
    sys.modules["mock_p2.router"] = p2_router_mod


def test_host_with_mocks(monkeypatch, caplog):
    create_mock_modules()

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://allowed.com,https://example.com")
    monkeypatch.setenv("MAX_BODY_SIZE_BYTES", "1024")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/project-1": "mock_p1.router:router",
        "/project-2": "mock_p2.router:router",
        "/project-3": "nonexistent_module.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    with caplog.at_level(logging.INFO):
        import main
        client = TestClient(main.app)

    assert "[/project-1] Successfully mounted at /project-1" in caplog.text
    assert "[/project-2] Successfully mounted at /project-2" in caplog.text
    assert "[/project-3] Failed to mount router" in caplog.text

    res_health = client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "degraded"
    assert "/project-1" in health_data["loaded"]
    assert "/project-2" in health_data["loaded"]
    assert "/project-3" in health_data["failed"]

    res_p1 = client.get("/project-1/ping")
    assert res_p1.status_code == 200
    assert res_p1.json() == {"project": "p1", "status": "ok"}

    res_p2 = client.get("/project-2/ping")
    assert res_p2.status_code == 200
    assert res_p2.json() == {"project": "p2", "status": "ok"}

    for doc_url in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(doc_url).status_code == 404

    cors_allowed = client.get(
        "/project-1/ping",
        headers={"Origin": "https://allowed.com"}
    )
    assert cors_allowed.status_code == 200
    assert cors_allowed.headers.get("access-control-allow-origin") == "https://allowed.com"

    cors_rejected = client.get(
        "/project-1/ping",
        headers={"Origin": "https://disallowed.com"}
    )
    assert cors_rejected.headers.get("access-control-allow-origin") is None

    oversized_data = {"text": "a" * 2000}
    res_oversized = client.post("/project-1/echo", json=oversized_data)
    assert res_oversized.status_code == 413

    res_slow = client.get("/project-1/slow")
    assert res_slow.status_code == 504


def test_kill_switch(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("DISABLE_PROJECTS", "project-2")

    import registry
    registry.PROJECT_REGISTRY = {
        "/project-1": "mock_p1.router:router",
        "/project-2": "mock_p2.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    client = TestClient(main.app)

    res_health = client.get("/health")
    health_data = res_health.json()
    assert "/project-1" in health_data["loaded"]
    assert "/project-2" not in health_data["loaded"]
    assert "/project-2" not in health_data["failed"]

    assert client.get("/project-1/ping").status_code == 200
    assert client.get("/project-2/ping").status_code == 404


def test_healthy_status_when_all_load(monkeypatch):
    create_mock_modules()
    monkeypatch.setenv("DISABLE_PROJECTS", "")

    import registry
    registry.PROJECT_REGISTRY = {
        "/project-1": "mock_p1.router:router",
        "/project-2": "mock_p2.router:router",
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    import main
    client = TestClient(main.app)

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
