"""FastAPI application factory."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from prediction_desk.api.routes import health_router, v1_router
from prediction_desk.config import get_settings
from prediction_desk.persistence.database import build_engine, build_session_factory

logger = logging.getLogger("prediction_desk.api")
REQUEST_ID_HEADER = "X-Request-ID"


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    docs_url = "/docs" if settings.enable_openapi_docs else None
    redoc_url = "/redoc" if settings.enable_openapi_docs else None
    openapi_url = "/openapi.json" if settings.enable_openapi_docs else None

    app = FastAPI(
        title="prediction-desk",
        version=settings.app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    engine = build_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                json.dumps(
                    {
                        "event": "request_failed",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": 500,
                        "duration_ms": round(duration_ms, 2),
                    },
                    sort_keys=True,
                )
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
                sort_keys=True,
            )
        )
        return response


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = (
        exc
        if isinstance(exc, HTTPException)
        else HTTPException(status_code=500, detail="internal_server_error")
    )
    request_id = getattr(request.state, "request_id", uuid4().hex)
    code, message = _error_code_and_message(http_exc)
    headers = dict(http_exc.headers or {})
    headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=http_exc.status_code,
        headers=headers,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


def _error_code_and_message(exc: HTTPException) -> tuple[str, str]:
    detail = exc.detail
    if isinstance(detail, str):
        code = _normalize_error_code(detail)
        return code, _error_message(code, detail)
    try:
        encoded = json.dumps(detail, sort_keys=True)
    except TypeError:
        encoded = "HTTP error"
    return "http_error", encoded


def _normalize_error_code(detail: str) -> str:
    return detail.strip().lower().replace(" ", "_")


def _error_message(code: str, fallback: str) -> str:
    messages = {
        "database_unreachable": "Database is unreachable.",
        "market_not_found": "Market not found.",
        "rule_snapshot_not_found": "Rule snapshot not found.",
        "trust_verdict_not_found": "Trust verdict not found.",
        "unauthorized": "Unauthorized.",
        "not_found": "Not found.",
    }
    return messages.get(code, fallback)
