"""Domain repository protocols and Unit of Work interfaces."""

from veritrace.domain.interfaces.audit_event_repository import AuditEventRepository
from veritrace.domain.interfaces.document_repository import DocumentRepository
from veritrace.domain.interfaces.evidence_repository import EvidenceRepository
from veritrace.domain.interfaces.finding_repository import FindingRepository
from veritrace.domain.interfaces.investigation_repository import InvestigationRepository
from veritrace.domain.interfaces.unit_of_work import UnitOfWork

__all__ = [
    "AuditEventRepository",
    "DocumentRepository",
    "EvidenceRepository",
    "FindingRepository",
    "InvestigationRepository",
    "UnitOfWork",
]
