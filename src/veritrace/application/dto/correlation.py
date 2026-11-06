"""Data Transfer Objects for Cross-Document Correlation operations."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CorrelationRequestDTO(BaseModel):
    """Request payload to trigger cross-document correlation on an investigation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    investigation_id: str = Field(..., min_length=1, description="Target investigation ID")
    organization_id: str = Field(..., min_length=1, description="Tenant organization ID")
    is_order_closed: bool = Field(
        default=False,
        description="Whether purchase orders are closed/finalized or remain open",
    )


class CorrelationDiscrepancyDTO(BaseModel):
    """Detailed summary of an identified cross-document discrepancy."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    rule_code: str
    category: str
    epistemic_tier: str
    severity: str
    confidence: float
    title: str
    explanation: str
    source_doc_id: str
    target_doc_id: str
    finding_id: str | None = None
    relation_id: str | None = None
    discrepancy_delta: Decimal | None = None
    discrepancy_percent: Decimal | None = None


class CorrelationSummaryDTO(BaseModel):
    """Consolidated summary response for an investigation's correlation run."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    investigation_id: str
    organization_id: str
    documents_analyzed: int
    discrepancies_count: int
    corroborations_count: int
    findings_generated: int
    relations_created: int
    discrepancies: list[CorrelationDiscrepancyDTO] = Field(default_factory=list)
