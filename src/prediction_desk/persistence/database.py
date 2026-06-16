"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from prediction_desk.config import get_settings
from prediction_desk.persistence.orm import Base


def build_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_settings().database_url
    connect_args: dict[str, object] = {}
    if resolved_url.startswith("sqlite:"):
        connect_args["check_same_thread"] = False
    return create_engine(resolved_url, connect_args=connect_args, future=True, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(database_url: str | None = None) -> None:
    engine = build_engine(database_url)
    Base.metadata.create_all(bind=engine)


def check_database_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def database_appears_migrated(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return version.scalar_one_or_none() is not None
    except SQLAlchemyError:
        return False


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
