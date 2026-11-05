"""VeriTrace SQLAlchemy persistence models package.

Exports declarative models representing all 15 domain entities plus the
finding_evidence_map association table (16 tables total).
"""

from __future__ import annotations

from veritrace.infrastructure.persistence.models.audit_event import AuditEventModel
from veritrace.infrastructure.persistence.models.authorized_subject import (
    AuthorizedSubjectModel,
)
from veritrace.infrastructure.persistence.models.cross_document_relation import (
    CrossDocumentRelationModel,
)
from veritrace.infrastructure.persistence.models.document import DocumentModel
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel
from veritrace.infrastructure.persistence.models.dossier import DossierModel
from veritrace.infrastructure.persistence.models.entity import EntityModel
from veritrace.infrastructure.persistence.models.evidence import EvidenceModel
from veritrace.infrastructure.persistence.models.extracted_field import (
    ExtractedFieldModel,
)
from veritrace.infrastructure.persistence.models.finding import FindingModel
from veritrace.infrastructure.persistence.models.finding_evidence import (
    finding_evidence_map,
)
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel
from veritrace.infrastructure.persistence.models.investigation_job import (
    InvestigationJobModel,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.models.review_decision import (
    ReviewDecisionModel,
)
from veritrace.infrastructure.persistence.models.signature_reference import (
    SignatureReferenceProfileModel,
)

__all__ = [
    "AuditEventModel",
    "AuthorizedSubjectModel",
    "CrossDocumentRelationModel",
    "DocumentModel",
    "DocumentPageModel",
    "DossierModel",
    "EntityModel",
    "EvidenceModel",
    "ExtractedFieldModel",
    "FindingModel",
    "InvestigationJobModel",
    "InvestigationModel",
    "OrganizationModel",
    "ReviewDecisionModel",
    "SignatureReferenceProfileModel",
    "finding_evidence_map",
]
