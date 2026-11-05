"""Multilingual and multi-script domain value objects for Indian document intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.exceptions.base import ConfidenceRangeError, ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


@dataclass(frozen=True, slots=True)
class LanguageScriptIdentification:
    """Detected language and script identification pair with confidence."""

    language: str  # ISO 639-2/3 (e.g., 'eng', 'hin', 'mar')
    script: str  # ISO 15924 (e.g., 'Latn', 'Deva')
    confidence: float  # [0.0 - 1.0]

    def __post_init__(self) -> None:
        if not self.language or not self.language.strip():
            raise ValidationError("language code must not be empty")
        if not self.script or not self.script.strip():
            raise ValidationError("script code must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass(frozen=True, slots=True)
class LanguageScriptRegion:
    """Spatial bounding box region with localized language and script identification.

    Enables multi-script pages (e.g. an English invoice header alongside
    Devanagari tabular line items) without requiring extra relational tables.
    """

    language: str  # ISO 639-2/3
    script: str  # ISO 15924
    confidence: float  # [0.0 - 1.0]
    normalized_bbox: NormalizedBoundingBox

    def __post_init__(self) -> None:
        if not self.language or not self.language.strip():
            raise ValidationError("language code must not be empty")
        if not self.script or not self.script.strip():
            raise ValidationError("script code must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass(frozen=True, slots=True)
class LanguageDetectionProfile:
    """Multi-script language detection profile across document, page, or region.

    Explicitly models multi-lingual and multi-region documents, capturing primary
    language/script classification, language distribution tuples, and spatial
    sub-regions with normalized bounding boxes.
    """

    primary_language: str
    primary_script: str
    confidence: float  # [0.0 - 1.0]
    detected_languages: tuple[LanguageScriptIdentification, ...] = ()
    regions: tuple[LanguageScriptRegion, ...] = ()
    detection_engine: str = "fasttext-lid"
    model_version: str | None = None

    def __post_init__(self) -> None:
        if not self.primary_language or not self.primary_language.strip():
            raise ValidationError("primary_language must not be empty")
        if not self.primary_script or not self.primary_script.strip():
            raise ValidationError("primary_script must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ConfidenceRangeError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        # Ensure immutable tuples
        if not isinstance(self.detected_languages, tuple):
            object.__setattr__(self, "detected_languages", tuple(self.detected_languages))
        if not isinstance(self.regions, tuple):
            object.__setattr__(self, "regions", tuple(self.regions))

    def has_multiple_languages(self) -> bool:
        """Return True if multiple languages are detected with confidence > 0.1."""
        return len(self.detected_languages) > 1 or len(self.regions) > 1

    def get_regions_for_script(self, script: str) -> tuple[LanguageScriptRegion, ...]:
        """Return all spatial regions identified with the specified script."""
        return tuple(r for r in self.regions if r.script == script)
