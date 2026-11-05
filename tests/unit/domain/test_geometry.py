"""Unit tests for spatial and geometric value objects."""

import pytest

from veritrace.domain.exceptions import CoordinateBoundsError, ValidationError
from veritrace.domain.value_objects.geometry import (
    EvidenceAnchor,
    NormalizedBoundingBox,
    PageDimensions,
)


def test_normalized_bounding_box_valid() -> None:
    """Verify valid normalized coordinates create instance successfully."""
    box = NormalizedBoundingBox(ymin=0.1, xmin=0.2, ymax=0.8, xmax=0.9)
    assert box.ymin == 0.1
    assert box.xmin == 0.2
    assert box.ymax == 0.8
    assert box.xmax == 0.9
    assert box.as_list() == [0.1, 0.2, 0.8, 0.9]


def test_normalized_bounding_box_boundary_limits() -> None:
    """Verify full-page bounds [0.0, 0.0, 1.0, 1.0] are valid."""
    box = NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0)
    assert box.area() == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("ymin", "xmin", "ymax", "xmax"),
    [
        (-0.1, 0.1, 0.5, 0.5),  # negative ymin
        (0.1, -0.1, 0.5, 0.5),  # negative xmin
        (0.1, 0.1, 1.1, 0.5),  # ymax > 1.0
        (0.1, 0.1, 0.5, 1.2),  # xmax > 1.0
        (0.5, 0.1, 0.5, 0.5),  # ymin == ymax
        (0.6, 0.1, 0.4, 0.5),  # ymin > ymax
        (0.1, 0.5, 0.5, 0.5),  # xmin == xmax
        (0.1, 0.6, 0.5, 0.4),  # xmin > xmax
    ],
)
def test_normalized_bounding_box_invalid_raises(
    ymin: float, xmin: float, ymax: float, xmax: float
) -> None:
    """Verify invalid or inverted coordinates raise CoordinateBoundsError."""
    with pytest.raises(CoordinateBoundsError):
        NormalizedBoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax)


def test_to_pixels() -> None:
    """Verify conversion to absolute pixel bounds."""
    box = NormalizedBoundingBox(ymin=0.25, xmin=0.2, ymax=0.75, xmax=0.8)
    # On 1000 x 2000 image:
    # x1 = 0.2 * 1000 = 200, y1 = 0.25 * 2000 = 500
    # x2 = 0.8 * 1000 = 800, y2 = 0.75 * 2000 = 1500
    pixels = box.to_pixels(page_width_px=1000, page_height_px=2000)
    assert pixels == (200, 500, 800, 1500)


def test_to_pixels_invalid_dimensions_raises() -> None:
    """Verify to_pixels raises ValidationError for non-positive dimensions."""
    box = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.9, xmax=0.9)
    with pytest.raises(ValidationError):
        box.to_pixels(0, 100)
    with pytest.raises(ValidationError):
        box.to_pixels(100, -50)


def test_from_pixels() -> None:
    """Verify construction from absolute pixel coordinates."""
    box = NormalizedBoundingBox.from_pixels(
        x1=200,
        y1=500,
        x2=800,
        y2=1500,
        page_width_px=1000,
        page_height_px=2000,
    )
    assert box.ymin == pytest.approx(0.25)
    assert box.xmin == pytest.approx(0.2)
    assert box.ymax == pytest.approx(0.75)
    assert box.xmax == pytest.approx(0.8)


def test_from_pixels_invalid_raises() -> None:
    """Verify from_pixels raises on non-positive dimensions or inverted coords."""
    with pytest.raises(ValidationError):
        NormalizedBoundingBox.from_pixels(10, 10, 50, 50, 0, 100)
    with pytest.raises(CoordinateBoundsError):
        NormalizedBoundingBox.from_pixels(50, 10, 10, 50, 100, 100)
    with pytest.raises(CoordinateBoundsError):
        NormalizedBoundingBox.from_pixels(10, 50, 50, 10, 100, 100)


def test_intersection_over_union() -> None:
    """Verify IoU calculation for identical, disjoint, and overlapping boxes."""
    box1 = NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=0.5, xmax=0.5)
    box2 = NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=0.5, xmax=0.5)
    # Identical boxes IoU = 1.0
    assert box1.intersection_over_union(box2) == pytest.approx(1.0)

    # Disjoint boxes IoU = 0.0
    box3 = NormalizedBoundingBox(ymin=0.6, xmin=0.6, ymax=1.0, xmax=1.0)
    assert box1.intersection_over_union(box3) == pytest.approx(0.0)

    # Partial overlap
    # box1: [0.0, 0.0, 0.5, 0.5], area = 0.25
    # box4: [0.25, 0.25, 0.75, 0.75], area = 0.25
    # intersection: [0.25, 0.25, 0.5, 0.5], area = 0.25 * 0.25 = 0.0625
    # union: 0.25 + 0.25 - 0.0625 = 0.4375
    # iou: 0.0625 / 0.4375 = 1 / 7
    box4 = NormalizedBoundingBox(ymin=0.25, xmin=0.25, ymax=0.75, xmax=0.75)
    assert box1.intersection_over_union(box4) == pytest.approx(1.0 / 7.0)


def test_page_dimensions() -> None:
    """Verify PageDimensions initialization and validation."""
    dims = PageDimensions(width_pixels=2480, height_pixels=3508, dpi=300)
    assert dims.width_pixels == 2480
    assert dims.height_pixels == 3508
    assert dims.dpi == 300

    with pytest.raises(ValidationError):
        PageDimensions(width_pixels=0, height_pixels=100)
    with pytest.raises(ValidationError):
        PageDimensions(width_pixels=100, height_pixels=-5)
    with pytest.raises(ValidationError):
        PageDimensions(width_pixels=100, height_pixels=100, dpi=0)


def test_evidence_anchor() -> None:
    """Verify EvidenceAnchor creation and validation."""
    box = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.5, xmax=0.5)
    anchor = EvidenceAnchor(document_id="doc_123", page_number=2, bbox=box)
    assert anchor.document_id == "doc_123"
    assert anchor.page_number == 2
    assert anchor.bbox == box

    with pytest.raises(ValidationError):
        EvidenceAnchor(document_id="", page_number=1, bbox=box)
    with pytest.raises(ValidationError):
        EvidenceAnchor(document_id="doc_123", page_number=0, bbox=box)
