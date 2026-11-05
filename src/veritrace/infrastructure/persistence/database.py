"""Database configuration, engine initialization, and session management for VeriTrace.

Provides SQLite connection setup with WAL mode, foreign keys, busy timeout,
and clean transaction lifecycle management.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from veritrace.bootstrap import resolve_data_directory
from veritrace.infrastructure.persistence.base import Base


def get_default_database_url() -> str:
    """Resolve the default SQLite database connection URL.

    Checks VERITRACE_DATABASE_URL environment variable first.
    If not specified, places the database at %LOCALAPPDATA%/VeriTrace/database/veritrace.sqlite
    (outside the repository and isolated from cloud sync paths).
    """
    env_url = os.environ.get("VERITRACE_DATABASE_URL")
    if env_url and env_url.strip():
        return env_url.strip()

    data_dir = resolve_data_directory()
    db_dir = data_dir / "database"
    db_path = db_dir / "veritrace.sqlite"
    # Normalize forward slashes for SQLite URL compatibility on Windows
    return f"sqlite:///{db_path.as_posix()}"


def _ensure_sqlite_directory(database_url: str) -> None:
    """Ensure parent directory exists for file-based SQLite database URLs."""
    if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:///:memory:"):
        raw_path = database_url.replace("sqlite:///", "")
        db_file = Path(raw_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Enforce strict SQLite integrity PRAGMAs on each connection.

    1. foreign_keys = ON: Enforces referential integrity across relational tables.
    2. busy_timeout = 5000: Mitigates lock contention by waiting up to 5s before busy error.
    3. journal_mode = WAL: Write-Ahead Logging for non-blocking concurrent readers.
       NOTE: WAL mode permits multiple concurrent readers alongside a single serialized
       background writer. It does NOT provide unrestricted multi-process concurrent writes;
       SQLite strictly serializes write operations to prevent database corruption.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA journal_mode = WAL")
    finally:
        cursor.close()


def create_db_engine(
    database_url: str | None = None,
    echo: bool = False,
    **engine_kwargs: Any,
) -> Engine:
    """Create and configure a SQLAlchemy Engine instance.

    Args:
        database_url: Connection URL string (defaults to get_default_database_url()).
        echo: If True, logs SQL statements.
        **engine_kwargs: Additional arguments forwarded to sqlalchemy.create_engine.

    Returns:
        Configured SQLAlchemy Engine.
    """
    url = database_url or get_default_database_url()
    _ensure_sqlite_directory(url)

    engine = create_engine(url, echo=echo, **engine_kwargs)

    # Attach SQLite PRAGMA listener if using SQLite
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _configure_sqlite_pragmas)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a configured sessionmaker bound to the given engine."""
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Yields:
        Active SQLAlchemy Session.

    Commits on successful completion, rolls back on exception,
    and unconditionally closes the session on exit.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine) -> None:
    """Initialize all tables defined in metadata.

    Imports all models to register them with Base.metadata before creating tables.
    """
    # Import models package to register all declarative models
    import veritrace.infrastructure.persistence.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
