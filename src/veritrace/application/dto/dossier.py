"""Data Transfer Objects for Dossier generation and export."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DossierExportRequestDTO(BaseModel):
    """Payload requesting compilation and export of PS-2 Investigation Dossier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    investigation_id: str = Field(..., min_length=1)
    organization_id: str = Field(..., min_length=1)
    output_pdf_path: str | None = None
    output_json_path: str | None = None
    executive_narrative: str | None = None


class DossierExportResultDTO(BaseModel):
    """Result of Dossier compilation containing artifacts and cryptographic hash."""

    model_config = ConfigDict(frozen=True)

    dossier_id: str
    investigation_id: str
    pdf_path: str
    json_path: str
    sha256_hash: str
    documents_count: int
    findings_count: int
    exported_at: datetime
