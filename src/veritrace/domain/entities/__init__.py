"""Domain Entities for VeriTrace.

Consolidates the 15 core domain entities across organizational tenancy,
document evidence, forensic analysis, human oversight, and audit trails.
"""

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.cross_document_relation import (
    CrossDocumentRelation,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.entity import Entity
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.entities.investigation_job import InvestigationJob
from veritrace.domain.entities.organization import Organization
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.entities.signature_reference import (
    SignatureReferenceProfile,
)

__all__ = [
    "AuditEvent",
    "AuthorizedSubject",
    "CrossDocumentRelation",
    "Document",
    "DocumentPage",
    "Dossier",
    "Entity",
    "Evidence",
    "ExtractedField",
    "Finding",
    "Investigation",
    "InvestigationJob",
    "Organization",
    "ReviewDecision",
    "SignatureReferenceProfile",
]
