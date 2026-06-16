"""Bearer-token authentication for the internal API."""

from __future__ import annotations

import hmac
from typing import cast

from fastapi import HTTPException, Request, status

from prediction_desk.config import Settings

AUTH_HEADER_PREFIX = "Bearer "


def require_api_token(request: Request) -> None:
    settings = _settings(request)
    if not settings.require_api_token:
        return

    expected_token = settings.prediction_desk_api_token
    authorization = request.headers.get("authorization")
    supplied_token = _bearer_token(authorization)
    if expected_token is None or supplied_token is None:
        raise _unauthorized()
    if not hmac.compare_digest(supplied_token, expected_token):
        raise _unauthorized()


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None or not authorization.startswith(AUTH_HEADER_PREFIX):
        return None
    token = authorization.removeprefix(AUTH_HEADER_PREFIX).strip()
    return token or None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )
