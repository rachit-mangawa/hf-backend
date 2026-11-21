"""FastAPI gateway for subproject routers on Hugging Face Spaces."""

import asyncio
import importlib
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
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

storage_bucket = (
    os.getenv("STORAGE_BUCKET_NAME")
    or os.getenv("BUCKET_NAME")
    or os.getenv("HF_BUCKET_NAME")
    or ""
).strip()
storage_endpoint = (
    os.getenv("STORAGE_ENDPOINT_URL")
    or os.getenv("S3_ENDPOINT_URL")
    or ""
).strip()
storage_region = (
    os.getenv("STORAGE_REGION")
    or os.getenv("AWS_REGION")
    or ""
).strip()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets standard security headers and allows Hugging Face Space framing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space;"
        )
        if request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLimitMiddleware(BaseHTTPMiddleware):
    """Enforces request payload size limits and execution timeouts."""

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

app = FastAPI(
    title="HF Backend Gateway",
    description="Pluggable aggregation gateway for independent Python microservices.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLimitMiddleware, max_size=max_body_size, timeout=request_timeout)

raw_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
default_origins = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "https://heartflow.vercel.app",
    "https://rachit-mangawa.github.io",
]
allowed_origins = [o for o in (raw_origins or default_origins) if o != "*"]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^https://.*\.github\.io$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )


def format_project_title(prefix: str) -> str:
    clean = prefix.strip("/").replace("-", " ").replace("_", " ")
    if "semantic" in clean:
        return "Semantic Comment Analyzer"
    if "heartflow" in clean:
        return "HeartFlow OS"
    return " ".join(word.capitalize() for word in clean.split())


def get_project_routes(prefix: str) -> list[dict[str, Any]]:
    """Inspects mounted routes for a specific subproject prefix from OpenAPI schema."""
    endpoints: list[dict[str, Any]] = []
    schema = app.openapi()
    excluded_suffixes = ("/openapi.json", "/docs")
    for path, methods_dict in schema.get("paths", {}).items():
        if path.startswith(prefix) and path not in (prefix, f"{prefix}/") and not any(path.endswith(s) for s in excluded_suffixes):
            methods = [m.upper() for m in methods_dict.keys() if m != "parameters"]
            summary = ""
            for m_info in methods_dict.values():
                if isinstance(m_info, dict):
                    summary = m_info.get("summary") or m_info.get("description") or ""
                    if summary:
                        break
            endpoints.append({
                "path": path,
                "methods": sorted(methods) or ["GET"],
                "name": path.split("/")[-1],
                "summary": summary,
            })
    return endpoints


def get_project_openapi(prefix: str) -> dict[str, Any]:
    """Generates an OpenAPI schema containing ONLY routes for this specific project."""
    full = app.openapi()
    scoped_paths = {}
    excluded_suffixes = ("/openapi.json", "/docs")
    for p, methods in full.get("paths", {}).items():
        if p.startswith(prefix) and p not in (prefix, f"{prefix}/") and not any(p.endswith(s) for s in excluded_suffixes):
            scoped_paths[p] = methods

    title = format_project_title(prefix)
    return {
        "openapi": full.get("openapi", "3.1.0"),
        "info": {
            "title": f"{title} API",
            "version": full.get("info", {}).get("version", "1.0.0"),
            "description": f"Dedicated endpoints and API documentation for {title} (mounted at {prefix}).",
        },
        "paths": scoped_paths,
        "components": full.get("components", {}),
    }


def get_routes_summary() -> dict[str, list[dict[str, Any]]]:
    """Inspects mounted routes and groups them by service prefix."""
    routes_by_prefix: dict[str, list[dict[str, Any]]] = {}
    for prefix in loaded_projects:
        routes_by_prefix[prefix] = get_project_routes(prefix)
    return routes_by_prefix


def get_gateway_info() -> dict[str, Any]:
    """Returns runtime configuration for the developer status console."""
    return {
        "max_body_size_bytes": max_body_size,
        "request_timeout_seconds": request_timeout,
        "warmup_timeout_seconds": default_warmup_timeout,
        "docs_url": None,
        "openapi_url": None,
        "enable_docs": enable_docs,
        "allowed_origins": allowed_origins,
        "storage_bucket": storage_bucket or None,
        "storage_endpoint": storage_endpoint or None,
        "storage_region": storage_region or None,
    }


@app.get("/health", tags=["Host Gateway"])
def health():
    any_warmup_failed = any(status.startswith("failed:") for status in warm_status.values())
    if not loaded_projects:
        overall_status = "unhealthy"
    elif failed_projects or any_warmup_failed:
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
    return HTMLResponse(
        content=render_statuspage(
            health(),
            gateway_info=get_gateway_info(),
            routes_info=get_routes_summary(),
        )
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/", tags=["Host Gateway"])
def root():
    """Root entrypoint points nowhere but an empty message."""
    return {"message": ""}


def make_project_handlers(p_prefix: str):
    """Generates scoped documentation and API listing handlers for a specific project."""
    async def p_root(request: Request, format: str | None = None):
        accept = request.headers.get("accept", "")
        wants_html = format == "html" or ("text/html" in accept and not accept.startswith("*/*"))
        if enable_docs and wants_html:
            title = format_project_title(p_prefix)
            return get_swagger_ui_html(
                openapi_url=f"{p_prefix}/openapi.json",
                title=f"{title} - API Documentation",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            )
        title = format_project_title(p_prefix)
        routes = get_project_routes(p_prefix)
        return {
            "project": title,
            "prefix": p_prefix,
            "target": loaded_projects.get(p_prefix, ""),
            "endpoints": routes,
            "openapi_url": f"{p_prefix}/openapi.json" if enable_docs else None,
        }

    async def p_openapi():
        if not enable_docs:
            raise HTTPException(status_code=404, detail="Documentation disabled")
        return get_project_openapi(p_prefix)

    return p_root, p_openapi


def load_routers():
    """Imports and mounts routers defined in registry.py with scoped per-project docs."""
    loaded_projects.clear()
    failed_projects.clear()
    warm_status.clear()

    disabled_raw = [p.strip().strip("/") for p in os.getenv("DISABLE_PROJECTS", "").split(",") if p.strip()]
    disabled_set = set(disabled_raw)

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

            # Support both APIRouter and full FastAPI application instances
            if isinstance(router, FastAPI):
                router = router.router

            tag = format_project_title(prefix)
            app.include_router(router, prefix=prefix, tags=[tag])

            # Mount scoped project documentation and endpoint inspector at /{project}
            p_root, p_openapi = make_project_handlers(prefix)
            app.add_api_route(prefix, p_root, methods=["GET"], include_in_schema=False)
            app.add_api_route(f"{prefix}/", p_root, methods=["GET"], include_in_schema=False)
            app.add_api_route(f"{prefix}/docs", p_root, methods=["GET"], include_in_schema=False)
            app.add_api_route(f"{prefix}/openapi.json", p_openapi, methods=["GET"], include_in_schema=False)

            loaded_projects[prefix] = target
            logger.info(f"[{prefix}] Successfully mounted at {prefix}")
        except Exception as e:
            failed_projects[prefix] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[{prefix}] Failed to mount router: {e}", exc_info=True)


load_routers()
