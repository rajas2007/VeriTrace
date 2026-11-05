"""Evidence domain entity representing a pixel-level visual patch and coordinate anchor."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import (
    EVD_PREFIX,
    PAGE_PREFIX,
    generate_id,
    validate_id,
)


@dataclass(slots=True)
class Evidence:
    """Pixel-level visual crop and coordinate anchor that supports one or more findings."""

    id: str
    page_id: str
    crop_image_path: str
    normalized_bbox: NormalizedBoundingBox
    pixel_x: int = 0
    pixel_y: int = 0
    pixel_width: int = 0
    pixel_height: int = 0
    heatmap_image_path: str | None = None
    grounding_explanation: str | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, EVD_PREFIX, "Evidence.id")
        self.page_id = validate_id(self.page_id, PAGE_PREFIX, "Evidence.page_id")
        if not self.crop_image_path or not self.crop_image_path.strip():
            raise ValidationError("crop_image_path must not be empty")
        if self.pixel_width < 0 or self.pixel_height < 0:
            raise ValidationError("Pixel dimensions must be non-negative")

    @property
    def norm_ymin(self) -> float:
        """Top normalized coordinate."""
        return self.normalized_bbox.ymin

    @property
    def norm_xmin(self) -> float:
        """Left normalized coordinate."""
        return self.normalized_bbox.xmin

    @property
    def norm_ymax(self) -> float:
        """Bottom normalized coordinate."""
        return self.normalized_bbox.ymax

    @property
    def norm_xmax(self) -> float:
        """Right normalized coordinate."""
        return self.normalized_bbox.xmax

    @classmethod
    def create(
        cls,
        page_id: str,
        crop_image_path: str,
        normalized_bbox: NormalizedBoundingBox,
        evidence_id: str | None = None,
        heatmap_image_path: str | None = None,
        grounding_explanation: str | None = None,
        pixel_x: int = 0,
        pixel_y: int = 0,
        pixel_width: int = 0,
        pixel_height: int = 0,
    ) -> Evidence:
        """Factory method creating an Evidence entity."""
        eid = evidence_id or generate_id(EVD_PREFIX)
        return cls(
            id=eid,
            page_id=page_id,
            crop_image_path=crop_image_path.strip(),
            normalized_bbox=normalized_bbox,
            heatmap_image_path=heatmap_image_path.strip() if heatmap_image_path else None,
            grounding_explanation=grounding_explanation.strip() if grounding_explanation else None,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
