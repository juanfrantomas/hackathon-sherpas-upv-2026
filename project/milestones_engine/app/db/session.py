"""Database engine, session factory and the FastAPI session dependency."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _apply_sqlite_pragmas(engine: Engine) -> None:
    """SQLite needs these turned on explicitly.

    * ``foreign_keys`` – SQLite ignores FK constraints unless asked.
    * ``journal_mode=WAL`` – readers do not block the single writer.
    * ``busy_timeout`` – wait instead of raising "database is locked".
    """

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: object, _record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


def create_engine_for_url(url: str) -> Engine:
    """Build an engine with the settings our SQLite usage needs."""
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):
        _apply_sqlite_pragmas(engine)
    return engine


def get_engine() -> Engine:
    """Process wide engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.resolved_database_url
        if url.startswith("sqlite:///") and ":memory:" not in url:
            db_path = Path(url.replace("sqlite:///", "", 1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine_for_url(url)
        logger.info("Database engine created")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Process wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
    return _session_factory


def reset_engine() -> None:
    """Drop the cached engine (used by the test suite)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


#: The database session a request works with.
DbSession = Annotated[Session, Depends(get_db)]
