"""Data Transfer Objects for Document ingestion and management."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from veritrace.domain.enums.document import DocumentStatus, DocumentType


class DocumentIngestDTO(BaseModel):
    """Payload for submitting a document for ingestion into an investigation."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    investigation_id: str = Field(..., min_length=1, max_length=64)
    organization_id: str = Field(..., min_length=1, max_length=64)
    filename: str = Field(..., min_length=1, max_length=255)
    content: bytes | None = Field(default=None, description="In-memory file bytes")
    file_path: Path | str | None = Field(default=None, description="Filesystem source path")
    document_type: DocumentType = Field(default=DocumentType.UNCLASSIFIED)


class DocumentIngestionResultDTO(BaseModel):
    """Structured response returned upon successful document ingestion."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    document_id: str
    investigation_id: str
    organization_id: str
    original_filename: str
    file_hash_sha256: str
    mime_type: str
    document_type: DocumentType
    page_count: int
    file_size_bytes: int
    storage_path: str
    status: DocumentStatus
    created_at: datetime
    page_ids: list[str] = Field(default_factory=list)
