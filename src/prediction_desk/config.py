"""Runtime configuration."""

from __future__ import annotations

import os
from typing import Literal, cast

from pydantic import BaseModel, Field

from prediction_desk import __version__

AppEnv = Literal["local", "staging", "production"]


class Settings(BaseModel):
    """Application settings sourced from environment variables."""

    app_env: AppEnv = "local"
    app_version: str = __version__
    database_url: str = Field(default_factory=lambda: _env_first("DATABASE_URL"))
    log_level: str = "INFO"
    prediction_desk_api_token: str | None = None
    enable_openapi_docs: bool = True
    require_api_token: bool = False
    git_commit: str | None = None


def _env_first(*names: str, default: str = "sqlite:///prediction_desk.db") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    legacy_value = os.getenv("PREDICTION_DESK_DATABASE_URL")
    return legacy_value or default


def get_settings() -> Settings:
    app_env = _app_env(os.getenv("APP_ENV", "local"))
    return Settings(
        app_env=app_env,
        app_version=os.getenv("APP_VERSION", __version__),
        database_url=_env_first("DATABASE_URL"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        prediction_desk_api_token=os.getenv("PREDICTION_DESK_API_TOKEN"),
        enable_openapi_docs=_bool_env("ENABLE_OPENAPI_DOCS", default=app_env == "local"),
        require_api_token=_bool_env(
            "REQUIRE_API_TOKEN", default=app_env in {"staging", "production"}
        ),
        git_commit=os.getenv("GIT_COMMIT"),
    )


def _app_env(value: str) -> AppEnv:
    normalized = value.lower()
    if normalized not in {"local", "staging", "production"}:
        raise ValueError("APP_ENV must be one of: local, staging, production")
    return cast(AppEnv, normalized)


def _bool_env(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

