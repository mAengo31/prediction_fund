"""Runtime configuration for local development."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings sourced from environment variables."""

    database_url: str = Field(default_factory=lambda: _env("PREDICTION_DESK_DATABASE_URL"))


def _env(name: str) -> str:
    return os.getenv(name, "sqlite:///prediction_desk.db")


def get_settings() -> Settings:
    return Settings()
