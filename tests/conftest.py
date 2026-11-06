"""Global pytest fixtures for VeriTrace test suites."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from PySide6.QtWidgets import QApplication

from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    init_db,
)
from veritrace.infrastructure.persistence.models.organization import (
    OrganizationModel,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@pytest.fixture
def test_uow_factory(tmp_path):
    """Create temporary SQLite database and return unit of work factory."""
    db_path = tmp_path / "test_workspace.db"
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        session.add(
            OrganizationModel(
                id="org_11111111111111111111111111111111",
                name="Default Manufacturing Organization",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
    return lambda: SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def app_instance():
    """Ensure a QApplication instance exists in offscreen mode."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
