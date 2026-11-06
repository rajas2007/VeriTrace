"""Data Transfer Objects for Investigation operations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
