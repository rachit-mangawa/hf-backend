import asyncio
import importlib
import logging
import os
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from registry import PROJECT_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hf-backend")

loaded_projects: dict[str, str] = {}
failed_projects: dict[str, str] = {}

max_body_size = int(os.getenv("MAX_BODY_SIZE_BYTES", str(10 * 1024 * 1024)))
request_timeout = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60.0"))


class RequestLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int, timeout: float):
        super().__init__(app)
        self.max_size = max_size
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return Response(content="Payload Too Large", status_code=413)

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


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(RequestLimitMiddleware, max_size=max_body_size, timeout=request_timeout)

raw_origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = [o for o in raw_origins if o != "*"]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def load_routers():
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
            app.include_router(router, prefix=prefix)
            loaded_projects[prefix] = target
            logger.info(f"[{prefix}] Successfully mounted at {prefix}")
        except Exception as e:
            failed_projects[prefix] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"[{prefix}] Failed to mount router: {e}", exc_info=True)


load_routers()


@app.get("/health")
def health():
    if not failed_projects:
        overall_status = "healthy"
    elif loaded_projects:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "loaded": loaded_projects,
        "failed": failed_projects,
    }
