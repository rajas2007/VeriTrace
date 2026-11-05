"""ExtractedField domain entity representing parsed text and key-value pairs."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.exceptions.base import (
    ConfidenceRangeError,
    ValidationError,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import (
    ENT_PREFIX,
    FLD_PREFIX,
    PAGE_PREFIX,
    generate_id,
    validate_id,
)


@dataclass(slots=True)
class ExtractedField:
    """Stores granular OCR tokens and parsed key-values with provenance and verbatim raw text.

    INVARIANT: raw_text preserves verbatim source glyphs (e.g. Indic conjuncts, matras,
    and numerals) without translation or lossy alteration.
    """

    id: str
    page_id: str
    field_name: str
    field_value: str
    raw_text: str
    confidence: float
    field_type: str | None = None
    entity_id: str | None = None
    language: str | None = None
    script: str | None = None
    lang_confidence: float | None = None
    normalized_bbox: NormalizedBoundingBox | None = None
    extraction_source: ExtractionSourceType = ExtractionSourceType.DIGITAL_TEXT
    ocr_engine: str | None = None
    ocr_model_version: str | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, FLD_PREFIX, "ExtractedField.id")
        self.page_id = validate_id(self.page_id, PAGE_PREFIX, "ExtractedField.page_id")
        if not self.field_name or not self.field_name.strip():
            raise ValidationError("field_name must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.lang_confidence is not None and not (0.0 <= self.lang_confidence <= 1.0):
            raise ConfidenceRangeError(
                f"lang_confidence must be in [0.0, 1.0], got {self.lang_confidence}"
            )
        if self.entity_id is not None:
            self.entity_id = validate_id(self.entity_id, ENT_PREFIX, "ExtractedField.entity_id")

    def map_to_entity(self, entity_id: str) -> None:
        """Link this extracted field to a reconciled canonical Entity."""
        self.entity_id = validate_id(entity_id, ENT_PREFIX, "entity_id")

    @classmethod
    def create(
        cls,
        page_id: str,
        field_name: str,
        field_value: str,
        raw_text: str,
        confidence: float,
        field_id: str | None = None,
        field_type: str | None = None,
        entity_id: str | None = None,
        language: str | None = None,
        script: str | None = None,
        lang_confidence: float | None = None,
        normalized_bbox: NormalizedBoundingBox | None = None,
        extraction_source: ExtractionSourceType = ExtractionSourceType.DIGITAL_TEXT,
        ocr_engine: str | None = None,
        ocr_model_version: str | None = None,
    ) -> ExtractedField:
        """Factory method creating an ExtractedField entity."""
        fid = field_id or generate_id(FLD_PREFIX)
        return cls(
            id=fid,
            page_id=page_id,
            field_name=field_name.strip(),
            field_value=field_value.strip(),
            raw_text=raw_text,
            confidence=confidence,
            field_type=field_type.strip() if field_type else None,
            entity_id=entity_id,
            language=language,
            script=script,
            lang_confidence=lang_confidence,
            normalized_bbox=normalized_bbox,
            extraction_source=extraction_source,
            ocr_engine=ocr_engine,
            ocr_model_version=ocr_model_version,
        )
