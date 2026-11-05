"""DocumentPage domain entity representing an individual rasterized page."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.enums.document import TextLayerType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    PAGE_PREFIX,
    generate_id,
    validate_id,
)
from veritrace.domain.value_objects.multilingual import LanguageDetectionProfile


@dataclass(slots=True)
class DocumentPage:
    """Represents a single rasterized page of an ingested document."""

    id: str
    document_id: str
    page_number: int
    dimensions: PageDimensions
    image_storage_path: str
    has_digital_text: bool = False
    text_layer_type: TextLayerType = TextLayerType.SCANNED_RASTER
    primary_language: str = "eng"
    primary_script: str = "Latn"
    language_profile: LanguageDetectionProfile | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, PAGE_PREFIX, "DocumentPage.id")
        self.document_id = validate_id(self.document_id, DOC_PREFIX, "DocumentPage.document_id")
        if self.page_number < 1:
            raise ValidationError(f"page_number must be >= 1, got {self.page_number}")
        if not self.image_storage_path or not self.image_storage_path.strip():
            raise ValidationError("image_storage_path must not be empty")

    @property
    def width_pixels(self) -> int:
        """Page pixel width at rendered resolution."""
        return self.dimensions.width_pixels

    @property
    def height_pixels(self) -> int:
        """Page pixel height at rendered resolution."""
        return self.dimensions.height_pixels

    @property
    def dpi(self) -> int:
        """Rendered raster DPI."""
        return self.dimensions.dpi

    def set_language_profile(self, profile: LanguageDetectionProfile) -> None:
        """Assign language detection profile with multi-region spatial script support."""
        self.language_profile = profile
        self.primary_language = profile.primary_language
        self.primary_script = profile.primary_script

    @classmethod
    def create(
        cls,
        document_id: str,
        page_number: int,
        dimensions: PageDimensions,
        image_storage_path: str,
        page_id: str | None = None,
        has_digital_text: bool = False,
        text_layer_type: TextLayerType = TextLayerType.SCANNED_RASTER,
        language_profile: LanguageDetectionProfile | None = None,
    ) -> DocumentPage:
        """Factory method creating a DocumentPage entity."""
        pid = page_id or generate_id(PAGE_PREFIX)
        primary_lang = language_profile.primary_language if language_profile else "eng"
        primary_script = language_profile.primary_script if language_profile else "Latn"
        return cls(
            id=pid,
            document_id=document_id,
            page_number=page_number,
            dimensions=dimensions,
            image_storage_path=image_storage_path.strip(),
            has_digital_text=has_digital_text,
            text_layer_type=text_layer_type,
            primary_language=primary_lang,
            primary_script=primary_script,
            language_profile=language_profile,
        )
