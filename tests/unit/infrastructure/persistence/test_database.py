"""Unit tests for VeriTrace database configuration and session management."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from veritrace.infrastructure.persistence.base import Base
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    get_default_database_url,
    init_db,
    session_scope,
)


def test_get_default_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure VERITRACE_DATABASE_URL environment variable is respected."""
    monkeypatch.setenv("VERITRACE_DATABASE_URL", "sqlite:///custom/path.sqlite")
    url = get_default_database_url()
    assert url == "sqlite:///custom/path.sqlite"


def test_get_default_database_url_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure default URL points to local app data database path."""
    monkeypatch.delenv("VERITRACE_DATABASE_URL", raising=False)
    url = get_default_database_url()
    assert url.startswith("sqlite:///")
    assert "veritrace.sqlite" in url
    assert "VeriTrace" in url


def test_sqlite_pragmas_on_file_database(tmp_path: Path) -> None:
    """Verify that foreign_keys, busy_timeout, and WAL mode are enforced on file-based SQLite."""
    db_file = tmp_path / "test_pragmas.sqlite"
    url = f"sqlite:///{db_file.as_posix()}"
    engine = create_db_engine(url)

    try:
        with engine.connect() as conn:
            fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
            bt = conn.execute(text("PRAGMA busy_timeout")).scalar()
            jm = conn.execute(text("PRAGMA journal_mode")).scalar()

            assert fk == 1, "Foreign keys must be enabled"
            assert bt == 5000, "Busy timeout must be set to 5000ms"
            assert str(jm).lower() == "wal", "Journal mode must be WAL"
    finally:
        engine.dispose()


def test_sqlite_pragmas_on_memory_database() -> None:
    """Verify that foreign_keys and busy_timeout are enforced on in-memory SQLite."""
    engine = create_db_engine("sqlite:///:memory:")

    try:
        with engine.connect() as conn:
            fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
            bt = conn.execute(text("PRAGMA busy_timeout")).scalar()

            assert fk == 1, "Foreign keys must be enabled on in-memory database"
            assert bt == 5000, "Busy timeout must be set to 5000ms"
    finally:
        engine.dispose()


def test_init_db_creates_all_16_tables() -> None:
    """Verify that init_db registers and creates all 16 persistence tables."""
    engine = create_db_engine("sqlite:///:memory:")

    try:
        init_db(engine)
        table_names = sorted(Base.metadata.tables.keys())
        assert len(table_names) == 16
        expected_tables = [
            "audit_events",
            "authorized_subjects",
            "cross_document_relations",
            "document_pages",
            "documents",
            "dossiers",
            "entities",
            "evidence",
            "extracted_fields",
            "finding_evidence_map",
            "findings",
            "investigation_jobs",
            "investigations",
            "organizations",
            "review_decisions",
            "signature_references",
        ]
        assert table_names == expected_tables
    finally:
        engine.dispose()


def test_session_scope_commit_on_success() -> None:
    """Verify session_scope commits changes when no exception is raised."""
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session_factory = create_session_factory(engine)

    try:
        # Create table row inside scope
        with session_scope(session_factory) as session:
            session.execute(
                text(
                    "INSERT INTO organizations (id, name, industry_sector, created_at) "
                    "VALUES ('org_0123456789abcdef0123456789abcdef', 'Test Corp', "
                    "'MANUFACTURING', '2026-01-01 00:00:00')"
                )
            )

        # Verify persisted in a new session
        new_session: Session = session_factory()
        count = new_session.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
        new_session.close()
        assert count == 1
    finally:
        engine.dispose()


def test_session_scope_rollback_on_error() -> None:
    """Verify session_scope rolls back changes when an exception is raised."""
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    session_factory = create_session_factory(engine)

    try:
        with (
            pytest.raises(RuntimeError, match="Simulated failure"),
            session_scope(session_factory) as session,
        ):
            session.execute(
                text(
                    "INSERT INTO organizations (id, name, industry_sector, created_at) "
                    "VALUES ('org_0123456789abcdef0123456789abcdef', 'Test Corp', "
                    "'MANUFACTURING', '2026-01-01 00:00:00')"
                )
            )
            raise RuntimeError("Simulated failure")

        # Verify not persisted
        new_session: Session = session_factory()
        count = new_session.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
        new_session.close()
        assert count == 0
    finally:
        engine.dispose()
