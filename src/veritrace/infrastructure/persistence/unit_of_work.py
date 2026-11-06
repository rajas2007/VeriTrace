"""SQLAlchemy implementation of UnitOfWork protocol."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

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


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy transaction coordinator implementing UnitOfWork protocol.

    Provides explicit transactional boundaries, automatic rollback on unhandled errors,
    and shared session context across all tenant repositories.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._investigations: InvestigationRepository | None = None
        self._documents: DocumentRepository | None = None
        self._findings: FindingRepository | None = None
        self._evidence: EvidenceRepository | None = None
        self._audit_events: AuditEventRepository | None = None

    @property
    def session(self) -> Session:
        """Internal active session handle (infrastructure-internal)."""
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._session

    @property
    def investigations(self) -> InvestigationRepository:
        """Investigation repository scoped to this unit of work."""
        if self._investigations is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._investigations

    @property
    def documents(self) -> DocumentRepository:
        """Document repository scoped to this unit of work."""
        if self._documents is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._documents

    @property
    def findings(self) -> FindingRepository:
        """Finding repository scoped to this unit of work."""
        if self._findings is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._findings

    @property
    def evidence(self) -> EvidenceRepository:
        """Evidence repository scoped to this unit of work."""
        if self._evidence is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._evidence

    @property
    def audit_events(self) -> AuditEventRepository:
        """Audit event repository scoped to this unit of work."""
        if self._audit_events is None:
            raise RuntimeError("UnitOfWork is not active. Use within a 'with' block.")
        return self._audit_events

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        """Initialize session and instantiate shared repositories."""
        self._session = self._session_factory()
        self._investigations = SqliteInvestigationRepository(self._session)
        self._documents = SqliteDocumentRepository(self._session)
        self._findings = SqliteFindingRepository(self._session)
        self._evidence = SqliteEvidenceRepository(self._session)
        self._audit_events = SqliteAuditEventRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Commit or rollback and cleanly close session."""
        try:
            if exc_type is not None:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None
                self._investigations = None
                self._documents = None
                self._findings = None
                self._evidence = None
                self._audit_events = None

    def commit(self) -> None:
        """Explicitly commit the current transaction."""
        if self._session is not None:
            self._session.commit()

    def rollback(self) -> None:
        """Explicitly roll back the current transaction."""
        if self._session is not None:
            self._session.rollback()
