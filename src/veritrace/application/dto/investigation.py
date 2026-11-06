"""Data Transfer Objects for Investigation operations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    RelationType,
    ReviewDecisionType,
    ReviewStatus,
)
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    RiskClassification,
)


class InvestigationCreateDTO(BaseModel):
    """Payload for creating a new forensic investigation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(..., min_length=1, max_length=255, description="Investigation title")
    reference_code: str = Field(
        ..., min_length=1, max_length=64, description="Unique reference code"
    )
    organization_id: str = Field(
        ..., min_length=1, max_length=64, description="Owning organization ID"
    )


class InvestigationUpdateDTO(BaseModel):
    """Payload for updating permitted investigation metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    reference_code: str | None = Field(default=None, min_length=1, max_length=64)
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_classification: RiskClassification | None = Field(default=None)


class InvestigationResponseDTO(BaseModel):
    """Structured response representation of an Investigation."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    organization_id: str
    title: str
    reference_code: str
    status: InvestigationStatus
    risk_score: float
    risk_classification: RiskClassification
    created_at: datetime
    updated_at: datetime


class ReviewDecisionDTO(BaseModel):
    """Structured representation of an analyst's review decision."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    finding_id: str
    reviewer_id: str
    decision: ReviewDecisionType
    rationale: str
    timestamp: datetime


class FindingResponseDTO(BaseModel):
    """Structured response representation of a forensic Finding."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    investigation_id: str
    category: FindingCategory
    epistemic_tier: EpistemicTier
    severity: FindingSeverity
    title: str
    narrative_explanation: str
    confidence: float
    investigator_guidance: str | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    evidence_ids: list[str] = Field(default_factory=list)
    signature_reference_id: str | None = None
    created_at: datetime
    review_decisions: list[ReviewDecisionDTO] = Field(default_factory=list)


class ReviewFindingRequestDTO(BaseModel):
    """Analyst request to review/adjudicate a forensic finding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(..., min_length=1)
    decision: ReviewDecisionType
    rationale: str = Field(..., min_length=1)
    reviewer_id: str = Field(default="analyst_01", min_length=1)


class EvidenceResponseDTO(BaseModel):
    """Structured response representation of a visual Evidence anchor."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    page_id: str
    crop_image_path: str
    norm_ymin: float
    norm_xmin: float
    norm_ymax: float
    norm_xmax: float
    pixel_x: int = 0
    pixel_y: int = 0
    pixel_width: int = 0
    pixel_height: int = 0
    heatmap_image_path: str | None = None
    grounding_explanation: str | None = None


class RelationResponseDTO(BaseModel):
    """Structured response representation of a CrossDocumentRelation."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    investigation_id: str
    source_document_id: str
    target_document_id: str
    relation_type: RelationType
    description: str
    finding_id: str | None = None
    similarity_score: float | None = None
