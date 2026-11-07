"""Domain enumeration types."""

from veritrace.domain.enums.audit import (
    ActorType,
    AuditEventType,
    EntityType,
    IndustrySector,
)
from veritrace.domain.enums.document import (
    DocumentStatus,
    DocumentType,
    ExtractionSourceType,
    QualityStatus,
    TextLayerType,
)
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    RelationType,
    ReviewDecisionType,
    ReviewStatus,
    SignatureAssessmentLevel,
)
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    JobStatus,
    PrivacyMode,
    ProcessingStatus,
    RiskClassification,
)

__all__ = [
    "ActorType",
    "AuditEventType",
    "DocumentStatus",
    "DocumentType",
    "EntityType",
    "EpistemicTier",
    "ExtractionSourceType",
    "FindingCategory",
    "FindingSeverity",
    "IndustrySector",
    "InvestigationStatus",
    "JobStatus",
    "PrivacyMode",
    "ProcessingStatus",
    "QualityStatus",
    "RelationType",
    "ReviewDecisionType",
    "ReviewStatus",
    "RiskClassification",
    "SignatureAssessmentLevel",
    "TextLayerType",
]
