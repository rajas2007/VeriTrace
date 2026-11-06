"""Strongly typed domain-aligned Pydantic models for cross-document correlation.

CRITICAL INVARIANTS:
1. No unrestricted `Any` types; all fields use explicit strong typing.
2. Exact `Decimal` arithmetic for all quantities, rates, and currency totals.
3. Raw extracted strings are strictly preserved for evidence grounding.
4. Confidence scores are validated within [0.0, 1.0].
5. Ambiguity is explicitly flagged with an explanatory reason.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
)


class AlignmentTier(StrEnum):
    """Categorization of entity and cross-document match confidence."""

    AUTHORITATIVE_MATCH = "AUTHORITATIVE_MATCH"
    HIGH_CONFIDENCE_CANDIDATE = "HIGH_CONFIDENCE_CANDIDATE"
    REVIEW_CANDIDATE = "REVIEW_CANDIDATE"
    NO_MATCH = "NO_MATCH"
    CONFLICTING_IDENTIFIERS = "CONFLICTING_IDENTIFIERS"


class NormalizedQuantity(BaseModel):
    """Normalized physical quantity with canonical unit and confidence."""

    model_config = ConfigDict(frozen=True)

    value: Decimal
    unit: str
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class NormalizedAmount(BaseModel):
    """Normalized financial amount with standard ISO currency code."""

    model_config = ConfigDict(frozen=True)

    value: Decimal
    currency: str
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class NormalizedDate(BaseModel):
    """Normalized ISO calendar date."""

    model_config = ConfigDict(frozen=True)

    value: date
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class NormalizedMaterialGrade(BaseModel):
    """Normalized metallurgical / industrial material alloy specification."""

    model_config = ConfigDict(frozen=True)

    canonical_grade: str
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class NormalizedIdentifier(BaseModel):
    """Standardized reference code, document number, or tax identifier."""

    model_config = ConfigDict(frozen=True)

    canonical_id: str
    identifier_type: str
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class NormalizedOrganizationName(BaseModel):
    """Standardized company / organization name stripped of legal entity suffixes."""

    model_config = ConfigDict(frozen=True)

    canonical_name: str
    raw_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None


class AlignedEntityPair(BaseModel):
    """Result of cross-document entity alignment between two documents."""

    model_config = ConfigDict(frozen=True)

    source_doc_id: str
    source_field_id: str
    target_doc_id: str
    target_field_id: str
    alignment_tier: AlignmentTier
    similarity_score: float = Field(ge=0.0, le=1.0)
    source_entity_name: str
    target_entity_name: str
    source_identifier: str | None = None
    target_identifier: str | None = None
    explanation: str = ""


class LineItemAggregation(BaseModel):
    """Aggregated line-item across PO, Delivery Challans, and Invoices."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    item_key: str
    description: str = ""
    material_grade: str | None = None
    unit: str = "KG"
    total_ordered_quantity: Decimal = Decimal("0.0")
    total_delivered_quantity: Decimal = Decimal("0.0")
    total_invoiced_quantity: Decimal = Decimal("0.0")
    ordered_unit_rate: Decimal | None = None
    invoiced_unit_rate: Decimal | None = None
    invoiced_line_total: Decimal | None = None
    ordered_field_ids: list[str] = Field(default_factory=list)
    delivered_field_ids: list[str] = Field(default_factory=list)
    invoiced_field_ids: list[str] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Result of a cross-document rule comparison."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    rule_code: str
    is_consistent: bool
    category: FindingCategory
    epistemic_tier: EpistemicTier
    severity: FindingSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    explanation: str
    source_doc_id: str
    target_doc_id: str
    evidence_field_ids: list[str] = Field(default_factory=list)
    discrepancy_delta: Decimal | None = None
    discrepancy_percent: Decimal | None = None

    @property
    def is_discrepancy(self) -> bool:
        """True if this comparison identified a discrepancy or contradiction."""
        return not self.is_consistent


class DocumentCorrelationInput(BaseModel):
    """Input encapsulation representing a document and its extracted fields."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc_id: str
    doc_type: str
    filename: str
    extracted_fields: list[ExtractedField] = Field(default_factory=list)


class CrossDocumentCorrelationResult(BaseModel):
    """Comprehensive analytical result produced by the correlation engine."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation_id: str
    documents_analyzed: int
    aligned_entities: list[AlignedEntityPair] = Field(default_factory=list)
    line_items: list[LineItemAggregation] = Field(default_factory=list)
    comparisons: list[ComparisonResult] = Field(default_factory=list)
    discrepancies: list[ComparisonResult] = Field(default_factory=list)
    corroborations: list[ComparisonResult] = Field(default_factory=list)
    missing_references: list[ComparisonResult] = Field(default_factory=list)
