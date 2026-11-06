"""Document domain entity representing an uploaded evidence file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from veritrace.domain.enums.document import (
    DocumentStatus,
    DocumentType,
    QualityStatus,
)
from veritrace.domain.exceptions.base import (
    ConfidenceRangeError,
    UnsupportedFormatError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    INV_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)
from veritrace.domain.value_objects.multilingual import LanguageDetectionProfile

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


@dataclass(slots=True)
class Document:
    """Represents an individual physical or digital file uploaded to an investigation."""

    id: str
    investigation_id: str
    original_filename: str
    file_hash_sha256: str
    mime_type: str
    created_at: datetime
    document_type: DocumentType = DocumentType.UNCLASSIFIED
    primary_language: str = "eng"
    primary_script: str = "Latn"
    language_profile: LanguageDetectionProfile | None = None
    classification_confidence: float = 0.0
    page_count: int = 1
    file_size_bytes: int = 0
    storage_path: str = ""
    quality_status: QualityStatus = QualityStatus.UNVERIFIED
    structured_content: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, DOC_PREFIX, "Document.id")
        self.investigation_id = validate_id(
            self.investigation_id, INV_PREFIX, "Document.investigation_id"
        )
        if not self.original_filename or not self.original_filename.strip():
            raise ValidationError("original_filename must not be empty")

        clean_hash = self.file_hash_sha256.strip().lower()
        if not _SHA256_PATTERN.match(clean_hash):
            raise ValidationError(
                f"file_hash_sha256 must be 64-char lowercase hex: '{self.file_hash_sha256}'"
            )
        self.file_hash_sha256 = clean_hash

        if self.mime_type not in _SUPPORTED_MIME_TYPES:
            raise UnsupportedFormatError(
                f"MIME type '{self.mime_type}' is unsupported. Must be in {_SUPPORTED_MIME_TYPES}"
            )

        if self.page_count < 1:
            raise ValidationError(f"page_count must be >= 1, got {self.page_count}")
        if self.file_size_bytes < 0:
            raise ValidationError("file_size_bytes must be non-negative")
        if not (0.0 <= self.classification_confidence <= 1.0):
            raise ConfidenceRangeError(
                f"classification_confidence must be in [0.0, 1.0]: {self.classification_confidence}"
            )

        self.created_at = ensure_utc(self.created_at, "Document.created_at")

    def set_language_profile(self, profile: LanguageDetectionProfile) -> None:
        """Update language detection profile and synchronize primary summary tags."""
        self.language_profile = profile
        self.primary_language = profile.primary_language
        self.primary_script = profile.primary_script

    def mark_processed(self, quality_status: QualityStatus = QualityStatus.VERIFIED_HIGH) -> None:
        """Mark document as successfully ingested and processed."""
        self.status = DocumentStatus.PROCESSED
        self.quality_status = quality_status

    def mark_corrupted(self) -> None:
        """Mark document as unreadable or corrupted."""
        self.status = DocumentStatus.ERROR_CORRUPTED
        self.quality_status = QualityStatus.DEGRADED_SCAN

    @classmethod
    def create(
        cls,
        investigation_id: str,
        original_filename: str,
        file_hash_sha256: str,
        mime_type: str,
        document_id: str | None = None,
        document_type: DocumentType = DocumentType.UNCLASSIFIED,
        page_count: int = 1,
        file_size_bytes: int = 0,
        storage_path: str = "",
        structured_content: dict[str, Any] | None = None,
        metadata_json: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> Document:
        """Factory method creating a Document entity."""
        did = document_id or generate_id(DOC_PREFIX)
        ts = created_at or utc_now()
        return cls(
            id=did,
            investigation_id=investigation_id,
            original_filename=original_filename.strip(),
            file_hash_sha256=file_hash_sha256.strip().lower(),
            mime_type=mime_type.strip(),
            document_type=document_type,
            page_count=page_count,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path.strip(),
            structured_content=structured_content,
            metadata_json=metadata_json,
            created_at=ts,
        )
