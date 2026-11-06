"""Unit tests for EvidenceCropper."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.cropper import EvidenceCropper
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import PAGE_PREFIX, generate_id


@pytest.fixture
def test_canvas(tmp_path: Path) -> Path:
    """Create a 1000x1000 test canvas image with a distinct shape."""
    img = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    # Draw a colored rectangle in the center [400, 400] to [600, 600]
    cv2.rectangle(img, (400, 400), (600, 600), (0, 0, 200), -1)
    img_path = tmp_path / "canvas.png"
    cv2.imwrite(str(img_path), img)
    return img_path


def test_crop_bounding_box_with_padding(test_canvas: Path, tmp_path: Path):
    """Verify crop dimensions reflect original bounding box plus 20px padding."""
    cropper = EvidenceCropper(padding_px=20)
    # Box [0.4, 0.4, 0.6, 0.6] -> 200x200 px
    bbox = NormalizedBoundingBox(ymin=0.4, xmin=0.4, ymax=0.6, xmax=0.6)
    out_path = tmp_path / "crop.png"

    saved_path, px, py, pw, ph = cropper.crop_bounding_box(test_canvas, bbox, out_path)

    assert saved_path.exists()
    assert px == 400
    assert py == 400
    assert pw == 200
    assert ph == 200

    cropped_img = cv2.imread(str(saved_path))
    assert cropped_img is not None
    # 200px + 20px on each side = 240px
    assert cropped_img.shape[0] == 240
    assert cropped_img.shape[1] == 240


def test_crop_clamped_at_canvas_boundaries(test_canvas: Path, tmp_path: Path):
    """Verify crop padding does not exceed canvas bounds at image edges."""
    cropper = EvidenceCropper(padding_px=50)
    # Top-left corner [0.0, 0.0, 0.1, 0.1]
    bbox = NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=0.1, xmax=0.1)
    out_path = tmp_path / "edge_crop.png"

    saved_path, px, py, pw, ph = cropper.crop_bounding_box(test_canvas, bbox, out_path)

    assert saved_path.exists()
    assert px == 0
    assert py == 0
    cropped_img = cv2.imread(str(saved_path))
    assert cropped_img is not None
    # 100px width + 50px right padding = 150px
    assert cropped_img.shape[1] == 150
    assert cropped_img.shape[0] == 150


def test_create_evidence_entity(test_canvas: Path, tmp_path: Path):
    """Verify create_evidence_entity returns fully populated Evidence domain entity."""
    cropper = EvidenceCropper(padding_px=20)
    bbox = NormalizedBoundingBox(ymin=0.2, xmin=0.2, ymax=0.3, xmax=0.4)
    out_path = tmp_path / "evidence_crop.png"

    page_id = generate_id(PAGE_PREFIX)
    ev = cropper.create_evidence_entity(
        page_id=page_id,
        image_or_path=test_canvas,
        bbox=bbox,
        output_crop_path=out_path,
        grounding_explanation="Test grounding note",
    )

    assert isinstance(ev, Evidence)
    assert ev.page_id == page_id
    assert ev.crop_image_path == str(out_path)
    assert ev.normalized_bbox == bbox
    assert ev.grounding_explanation == "Test grounding note"
