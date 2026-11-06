"""Data Transfer Objects for digital text and forensic extraction results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from veritrace.domain.enums.document import TextLayerType


class PageExtractionResultDTO(BaseModel):
    """Structured extraction result for an individual document page."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    page_id: str
    page_number: int
    has_digital_text: bool
    text_layer_type: TextLayerType
    extracted_text: str
    word_count: int
    width_pixels: int
    height_pixels: int
    dpi: int
    extracted_fields_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class DocumentExtractionResultDTO(BaseModel):
    """Structured extraction summary across all pages of a document."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    document_id: str
    investigation_id: str
    total_pages: int
    pages_with_digital_text: int
    extraction_method: str
    timestamp: datetime
    pages: list[PageExtractionResultDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
