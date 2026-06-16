"""FastAPI dependency wiring."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from prediction_desk.persistence.repositories import PredictionMarketRepository


def get_session(request: Request) -> Generator[Session]:
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_repository(
    session: Annotated[Session, Depends(get_session)],
) -> PredictionMarketRepository:
    return PredictionMarketRepository(session)
