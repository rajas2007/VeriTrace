"""Extraction provenance, diagnostics, and token-level value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.exceptions.base import ConfidenceRangeError, ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.multilingual import LanguageDetectionProfile


@dataclass(frozen=True, slots=True)
class ExtractedToken:
    """Individual word or symbol token extracted from a document page."""

    token_id: str  # Format: "tok_<uuid4_hex>"
    text: str
    raw_text: str  # Verbatim glyphs preserving Indic script without alteration
    normalized_bbox: NormalizedBoundingBox
    confidence: float  # [0.0 - 1.0]
    page_number: int  # 1-based
    source_type: ExtractionSourceType
    language: str | None = None
    script: str | None = None

    def __post_init__(self) -> None:
        if not self.token_id:
            raise ValidationError("token_id must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.page_number < 1:
            raise ValidationError(f"page_number must be >= 1, got {self.page_number}")


@dataclass(frozen=True, slots=True)
class ProcessingWarning:
    """Recoverable or non-fatal anomaly encountered during processing."""

    warning_code: str
    message: str
    page_number: int | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.warning_code:
            raise ValidationError("warning_code must not be empty")
        if not self.message:
            raise ValidationError("message must not be empty")


@dataclass(frozen=True, slots=True)
class ProcessingError:
    """Structured diagnostic for a document or system processing failure."""

    error_code: str
    message: str
    is_fatal: bool = True
    recoverable: bool = False
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.error_code:
            raise ValidationError("error_code must not be empty")
        if not self.message:
            raise ValidationError("message must not be empty")


@dataclass(frozen=True, slots=True)
class ExtractionProvenance:
    """Immutable audit trail recording how text or field data was extracted.

    INVARIANT: OCR confidence measures character recognizer probability;
    it must never be treated as legal or factual correctness.
    """

    document_id: str
    page_number: int
    extractor_name: str  # e.g., "PyMuPDF", "Tesseract", "PaddleOCR"
    extractor_version: str
    execution_time_ms: float
    source_type: ExtractionSourceType
    bounding_box: NormalizedBoundingBox | None = None
    extraction_confidence: float | None = None
    ocr_engine: str | None = None
    ocr_model_version: str | None = None
    language_profile: LanguageDetectionProfile | None = None
    warnings: tuple[ProcessingWarning, ...] = ()

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValidationError("document_id must not be empty")
        if self.page_number < 1:
            raise ValidationError(f"page_number must be >= 1, got {self.page_number}")
        if self.execution_time_ms < 0.0:
            raise ValidationError("execution_time_ms must be non-negative")
        if self.extraction_confidence is not None and not (
            0.0 <= self.extraction_confidence <= 1.0
        ):
            raise ConfidenceRangeError(
                f"extraction_confidence must be in [0.0, 1.0], got {self.extraction_confidence}"
            )
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True, slots=True)
class ForensicEvidenceProvenance:
    """Complete measurement provenance for visual forensic findings."""

    algorithm_name: str  # "ELA", "BASELINE_REGRESSION", "ORB_CLONE", "SIAMESE_ONNX"
    algorithm_version: str
    input_image_dpi: int
    quality_score: float
    parameters: dict[str, Any] = field(default_factory=dict)
    calibrated_dataset_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.algorithm_name:
            raise ValidationError("algorithm_name must not be empty")
        if self.input_image_dpi <= 0:
            raise ValidationError("input_image_dpi must be positive")
        if not (0.0 <= self.quality_score <= 1.0):
            raise ConfidenceRangeError(
                f"quality_score must be in [0.0, 1.0], got {self.quality_score}"
            )
