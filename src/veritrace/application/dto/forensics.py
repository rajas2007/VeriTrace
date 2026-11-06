"""Data Transfer Objects for Forensic analysis and visual verification."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SignatureDetectionDTO(BaseModel):
    """Detected signature candidate region."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    document_name: str
    page_number: int
    bbox: tuple[float, float, float, float]
    crop_path: str


class SignatureComparisonDTO(BaseModel):
    """Comparative forensic result between questioned signature and enrolled reference."""

    model_config = ConfigDict(frozen=True)

    questioned_doc_name: str
    questioned_crop_path: str
    reference_doc_name: str
    reference_crop_path: str
    hu_distance: float
    stroke_density_ratio: float
    assessment_level: str
    is_match: bool
    explanation: str


class ContextualAuditItemDTO(BaseModel):
    """Individual mathematical or chronological verification check result."""

    model_config = ConfigDict(frozen=True)

    rule_code: str
    rule_name: str
    category: str
    status: str
    severity: str
    description: str
    expected_value: str
    actual_value: str
    involved_documents: list[str] = Field(default_factory=list)
