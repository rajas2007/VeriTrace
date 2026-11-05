"""Spatial and geometric domain value objects for page layout and evidence crops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from veritrace.domain.exceptions.base import CoordinateBoundsError, ValidationError


@dataclass(frozen=True, slots=True)
class NormalizedBoundingBox:
    """Normalized spatial coordinates [ymin, xmin, ymax, xmax] in range [0.0, 1.0].

    Universal coordinate standard for High-DPI screen rendering, crop extraction,
    and IoU intersection calculations.

    Origin (0.0, 0.0) is the top-left corner of the page.
    X increases from left (0.0) to right (1.0).
    Y increases from top (0.0) to bottom (1.0).
    """

    ymin: float
    xmin: float
    ymax: float
    xmax: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.ymin <= 1.0 and 0.0 <= self.ymax <= 1.0):
            raise CoordinateBoundsError(
                f"Y coordinates must be in [0.0, 1.0]: ymin={self.ymin}, ymax={self.ymax}"
            )
        if not (0.0 <= self.xmin <= 1.0 and 0.0 <= self.xmax <= 1.0):
            raise CoordinateBoundsError(
                f"X coordinates must be in [0.0, 1.0]: xmin={self.xmin}, xmax={self.xmax}"
            )
        if self.ymin >= self.ymax:
            raise CoordinateBoundsError(
                f"ymin must be strictly less than ymax: {self.ymin} >= {self.ymax}"
            )
        if self.xmin >= self.xmax:
            raise CoordinateBoundsError(
                f"xmin must be strictly less than xmax: {self.xmin} >= {self.xmax}"
            )

    def to_pixels(self, page_width_px: int, page_height_px: int) -> tuple[int, int, int, int]:
        """Convert normalized coordinates to integer pixel bounds (x1, y1, x2, y2)."""
        if page_width_px <= 0 or page_height_px <= 0:
            raise ValidationError("Page pixel dimensions must be strictly positive")
        x1 = int(round(self.xmin * page_width_px))
        y1 = int(round(self.ymin * page_height_px))
        x2 = int(round(self.xmax * page_width_px))
        y2 = int(round(self.ymax * page_height_px))
        return (x1, y1, x2, y2)

    @classmethod
    def from_pixels(
        cls,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        page_width_px: int,
        page_height_px: int,
    ) -> Self:
        """Construct a normalized bounding box from absolute pixel bounds."""
        if page_width_px <= 0 or page_height_px <= 0:
            raise ValidationError("Page pixel dimensions must be strictly positive")
        if x1 >= x2:
            raise CoordinateBoundsError(f"x1 must be strictly less than x2: {x1} >= {x2}")
        if y1 >= y2:
            raise CoordinateBoundsError(f"y1 must be strictly less than y2: {y1} >= {y2}")

        norm_xmin = max(0.0, min(1.0, x1 / page_width_px))
        norm_ymin = max(0.0, min(1.0, y1 / page_height_px))
        norm_xmax = max(0.0, min(1.0, x2 / page_width_px))
        norm_ymax = max(0.0, min(1.0, y2 / page_height_px))

        return cls(ymin=norm_ymin, xmin=norm_xmin, ymax=norm_ymax, xmax=norm_xmax)

    def as_list(self) -> list[float]:
        """Return coordinate array [ymin, xmin, ymax, xmax]."""
        return [self.ymin, self.xmin, self.ymax, self.xmax]

    def area(self) -> float:
        """Return normalized bounding box area in [0.0, 1.0]."""
        return (self.ymax - self.ymin) * (self.xmax - self.xmin)

    def intersection_over_union(self, other: NormalizedBoundingBox) -> float:
        """Compute standard Intersection-over-Union (IoU) with another bounding box."""
        inter_ymin = max(self.ymin, other.ymin)
        inter_xmin = max(self.xmin, other.xmin)
        inter_ymax = min(self.ymax, other.ymax)
        inter_xmax = min(self.xmax, other.xmax)

        if inter_ymin >= inter_ymax or inter_xmin >= inter_xmax:
            return 0.0

        inter_area = (inter_ymax - inter_ymin) * (inter_xmax - inter_xmin)
        union_area = self.area() + other.area() - inter_area
        if union_area <= 0.0:
            return 0.0
        return inter_area / union_area


@dataclass(frozen=True, slots=True)
class PageDimensions:
    """Pixel resolution and DPI metadata for a rendered document page."""

    width_pixels: int
    height_pixels: int
    dpi: int = 300

    def __post_init__(self) -> None:
        if self.width_pixels <= 0:
            raise ValidationError(f"width_pixels must be positive, got {self.width_pixels}")
        if self.height_pixels <= 0:
            raise ValidationError(f"height_pixels must be positive, got {self.height_pixels}")
        if self.dpi <= 0:
            raise ValidationError(f"dpi must be positive, got {self.dpi}")


@dataclass(frozen=True, slots=True)
class EvidenceAnchor:
    """Coordinate anchor locating evidence within an ingested document page."""

    document_id: str
    page_number: int
    bbox: NormalizedBoundingBox

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValidationError("document_id must not be empty")
        if self.page_number < 1:
            raise ValidationError(f"page_number must be >= 1, got {self.page_number}")
