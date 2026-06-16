"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from prediction_desk.config import get_settings
from prediction_desk.persistence.orm import Base


def build_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_settings().database_url
    connect_args: dict[str, object] = {}
    if resolved_url.startswith("sqlite:"):
        connect_args["check_same_thread"] = False
    return create_engine(resolved_url, connect_args=connect_args, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(database_url: str | None = None) -> None:
    engine = build_engine(database_url)
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope(database_url: str | None = None) -> Generator[Session]:
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
