"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from prediction_desk.api.routes import router
from prediction_desk.config import get_settings
from prediction_desk.persistence.database import build_engine, build_session_factory


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
    app.include_router(router)
    return app
