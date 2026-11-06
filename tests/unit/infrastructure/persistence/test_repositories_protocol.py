"""Unit tests verifying repository and UnitOfWork protocol conformance."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from veritrace.domain.interfaces.audit_event_repository import AuditEventRepository
from veritrace.domain.interfaces.document_repository import DocumentRepository
from veritrace.domain.interfaces.evidence_repository import EvidenceRepository
from veritrace.domain.interfaces.finding_repository import FindingRepository
from veritrace.domain.interfaces.investigation_repository import InvestigationRepository
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.infrastructure.persistence.repositories.audit_event_repository import (
    SqliteAuditEventRepository,
)
from veritrace.infrastructure.persistence.repositories.document_repository import (
    SqliteDocumentRepository,
)
from veritrace.infrastructure.persistence.repositories.evidence_repository import (
    SqliteEvidenceRepository,
)
from veritrace.infrastructure.persistence.repositories.finding_repository import (
    SqliteFindingRepository,
)
from veritrace.infrastructure.persistence.repositories.investigation_repository import (
    SqliteInvestigationRepository,
)
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


def test_repository_protocol_signatures() -> None:
    """Verify that concrete SQLite repository implementations satisfy declared protocols."""
    mock_session = MagicMock()

    inv_repo = SqliteInvestigationRepository(mock_session)
    assert isinstance(inv_repo, InvestigationRepository)

    doc_repo = SqliteDocumentRepository(mock_session)
    assert isinstance(doc_repo, DocumentRepository)

    fnd_repo = SqliteFindingRepository(mock_session)
    assert isinstance(fnd_repo, FindingRepository)

    evd_repo = SqliteEvidenceRepository(mock_session)
    assert isinstance(evd_repo, EvidenceRepository)

    aud_repo = SqliteAuditEventRepository(mock_session)
    assert isinstance(aud_repo, AuditEventRepository)


def test_unit_of_work_protocol_conformance() -> None:
    """Verify SqlAlchemyUnitOfWork satisfies UnitOfWork protocol."""
    mock_factory = MagicMock()
    uow = SqlAlchemyUnitOfWork(mock_factory)
    with uow:
        assert isinstance(uow, UnitOfWork)


def test_audit_event_repository_prohibits_mutators() -> None:
    """Strictly assert that AuditEventRepository and its SQLite implementation omit mutators."""
    for cls in [AuditEventRepository, SqliteAuditEventRepository]:
        assert not hasattr(cls, "update")
        assert not hasattr(cls, "delete")
        assert not hasattr(cls, "remove")
        assert not hasattr(cls, "modify")


def test_domain_interfaces_do_not_import_sqlalchemy() -> None:
    """Strict architectural invariant: domain interfaces must never import SQLAlchemy."""
    import veritrace.domain.interfaces as di

    for _, member in inspect.getmembers(di):
        if inspect.isclass(member) and member.__module__.startswith("veritrace.domain.interfaces"):
            source = inspect.getsource(member)
            assert "sqlalchemy" not in source.lower()
            assert "Session" not in source
