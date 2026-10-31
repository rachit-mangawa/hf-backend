"""FastAPI gateway for subproject routers on Hugging Face Spaces.

Mounts external routers, runs startup model warmups, enforces request limits
and security headers, and serves health status.
"""

import asyncio
import importlib
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

from dashboard import render_statuspage
from registry import PROJECT_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hf-backend")

loaded_projects: dict[str, str] = {}
failed_projects: dict[str, str] = {}
warm_status: dict[str, str] = {}
total_warmup_seconds: float = 0.0

max_body_size = int(os.getenv("MAX_BODY_SIZE_BYTES", str(10 * 1024 * 1024)))
request_timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60.0"))
default_warmup_timeout = float(os.getenv("WARMUP_TIMEOUT_SECONDS", "300.0"))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets security headers and allows Hugging Face Space framing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space;"
        )
        if request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLimitMiddleware(BaseHTTPMiddleware):
    """Enforces request payload limits and execution timeouts."""

    def __init__(self, app, max_size: int, timeout: float):
        super().__init__(app)
        self.max_size = max_size
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.scope.get("type") != "http":
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    return Response(content="Payload Too Large", status_code=413)
            except ValueError:
                return Response(content="Invalid Content-Length Header", status_code=400)

        bytes_received = 0
        original_receive = request._receive

        async def limited_receive():
            nonlocal bytes_received
            message = await original_receive()
            if message["type"] == "http.request":
                bytes_received += len(message.get("body", b""))
                if bytes_received > self.max_size:
                    raise HTTPException(status_code=413, detail="Payload Too Large")
            return message

        request._receive = limited_receive

        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return Response(content="Request Timeout", status_code=504)


async def run_warmup_for_project(prefix: str, target: str, timeout: float):
    """Runs a package warmup function in a worker thread."""
    logger.info(f"[{prefix}] Checking warmup for target '{target}'...")
    try:
        module_name = target.split(":")[0]
        top_pkg_name = module_name.split(".")[0]
        pkg = importlib.import_module(top_pkg_name)
        warmup_fn = getattr(pkg, "warmup", None)
        if warmup_fn is None or not callable(warmup_fn):
            logger.info(f"[{prefix}] No callable warmup found on package '{top_pkg_name}'")
            warm_status[prefix] = "no warmup"
            return

        logger.info(f"[{prefix}] Starting warmup with timeout {timeout}s...")
        await asyncio.wait_for(asyncio.to_thread(warmup_fn), timeout=timeout)
        warm_status[prefix] = "warmed"
        logger.info(f"[{prefix}] Warmup completed successfully")
    except asyncio.TimeoutError:
        msg = f"failed: TimeoutError: warmup timed out after {timeout}s"
        warm_status[prefix] = msg
        logger.error(f"[{prefix}] Warmup timed out after {timeout}s")
    except Exception as e:
        msg = f"failed: {type(e).__name__}: {str(e)}"
        warm_status[prefix] = msg
        logger.error(f"[{prefix}] Warmup failed: {e}", exc_info=True)


async def run_all_warmups():
    global total_warmup_seconds
    timeout = float(os.getenv("WARMUP_TIMEOUT_SECONDS", str(default_warmup_timeout)))
    logger.info(f"Lifespan startup: beginning sequential project warmups (timeout={timeout}s)...")
    t0 = time.perf_counter()
    for prefix, target in list(loaded_projects.items()):
        await run_warmup_for_project(prefix, target, timeout=timeout)
    total_warmup_seconds = round(time.perf_counter() - t0, 3)
    logger.info(f"Lifespan startup: all warmups finished in {total_warmup_seconds}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_all_warmups()
    yield
    logger.info("Lifespan shutdown: Gateway stopped cleanly.")


enable_docs = os.getenv("ENABLE_DOCS", "true").lower() in ("true", "1", "yes")
docs_url = os.getenv("DOCS_URL", "/project") if enable_docs else None
openapi_url = os.getenv("OPENAPI_URL", "/openapi.json") if enable_docs else None

app = FastAPI(
    title="HF Backend Gateway",
    description="API gateway for HeartFlow OS and Semantic Comment Analyzer.",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=None,
    openapi_url=openapi_url,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLimitMiddleware, max_size=max_body_size, timeout=request_timeout)

raw_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://heartflow.vercel.app",
]
allowed_origins = [o for o in (raw_origins or default_origins) if o != "*"]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health", tags=["Host Gateway"])
def health():
    any_warmup_failed = any(status.startswith("failed:") for status in warm_status.values())
    has_mount_failures = len(failed_projects) > 0

    if not loaded_projects:
        overall_status = "unhealthy"
    elif has_mount_failures or any_warmup_failed:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "loaded": loaded_projects,
        "failed": failed_projects,
        "warm_status": warm_status,
        "total_warmup_seconds": total_warmup_seconds,
    }


@app.get("/status", response_class=HTMLResponse, tags=["Host Gateway"])
def status_page():
    return HTMLResponse(content=render_statuspage(health()))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/", tags=["Host Gateway"])
def root(request: Request, format: str | None = None):
    accept = request.headers.get("accept", "")
    wants_html = format == "html" or ("text/html" in accept and not accept.startswith("*/*"))
    if format == "json" or not wants_html:
        return health()
    return HTMLResponse(content=render_statuspage(health()))


def load_routers():
    """Imports and mounts routers defined in registry.py."""
    loaded_projects.clear()
    failed_projects.clear()
    warm_status.clear()

    disabled_raw = [p.strip().strip("/") for p in os.getenv("DISABLE_PROJECTS", "").split(",") if p.strip()]
    disabled_set = {p for p in disabled_raw}

    for prefix, target in PROJECT_REGISTRY.items():
        clean_prefix = prefix.strip("/")
        if clean_prefix in disabled_set:
            logger.warning(f"[{prefix}] Skipped: disabled by DISABLE_PROJECTS")
            continue

        try:
            logger.info(f"[{prefix}] Importing {target}")
            module_name, attr_name = target.split(":")
            module = importlib.import_module(module_name)
            router = getattr(module, attr_name)
            tag = "Semantic Comment Analyzer" if "semantic" in prefix else ("HeartFlow OS" if "heartflow" in prefix else prefix.strip("/").title())
            app.include_router(router, prefix=prefix, tags=[tag])
            if prefix == "/heartflow":
                app.include_router(router, include_in_schema=False)
            loaded_projects[prefix] = target
            logger.info(f"[{prefix}] Successfully mounted at {prefix}")
        except Exception as e:
            failed_projects[prefix] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[{prefix}] Failed to mount router: {e}", exc_info=True)


load_routers()
