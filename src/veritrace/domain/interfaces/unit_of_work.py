"""Protocol for Unit of Work transaction coordination."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.interfaces.audit_event_repository import AuditEventRepository
from veritrace.domain.interfaces.document_repository import DocumentRepository
from veritrace.domain.interfaces.evidence_repository import EvidenceRepository
from veritrace.domain.interfaces.finding_repository import FindingRepository
from veritrace.domain.interfaces.investigation_repository import InvestigationRepository


@runtime_checkable
class UnitOfWork(Protocol):
    """Atomic transaction boundary coordinating repositories across an operation.

    Guarantees:
    - Atomic commit on successful context exit.
    - Automatic rollback on unhandled exceptions.
    - Deterministic connection/session cleanup.
    - Repositories share a single transactional context.
    """

    @property
    def investigations(self) -> InvestigationRepository:
        """Investigation repository scoped to this unit of work."""
        ...

    @property
    def documents(self) -> DocumentRepository:
        """Document repository scoped to this unit of work."""
        ...

    @property
    def findings(self) -> FindingRepository:
        """Finding repository scoped to this unit of work."""
        ...

    @property
    def evidence(self) -> EvidenceRepository:
        """Evidence repository scoped to this unit of work."""
        ...

    @property
    def audit_events(self) -> AuditEventRepository:
        """Audit event repository scoped to this unit of work."""
        ...

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None: ...

    def commit(self) -> None:
        """Explicitly commit the current transaction."""
        ...

    def rollback(self) -> None:
        """Explicitly roll back the current transaction."""
        ...
