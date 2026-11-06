"""Unit tests for ErrorLevelAnalyzer."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.ela import ErrorLevelAnalyzer
from veritrace.capabilities.forensics.models import ELAResult


@pytest.fixture
def clean_image(tmp_path: Path) -> Path:
    """Create a clean document image with uniform compression characteristics."""
    img = np.full((600, 800, 3), 245, dtype=np.uint8)
    # Add simple text-like lines
    cv2.putText(
        img,
        "Authentic Official Document",
        (50, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (20, 20, 20),
        2,
    )
    p = tmp_path / "clean.png"
    cv2.imwrite(str(p), img)
    return p


@pytest.fixture
def spliced_image(tmp_path: Path) -> Path:
    """Create an image simulating a spliced/modified patch with compression mismatch."""
    import io

    from PIL import Image

    # 1. Base document image saved at quality 75
    base = np.full((600, 800, 3), 245, dtype=np.uint8)
    cv2.putText(
        base,
        "Official Document Text Header",
        (50, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (30, 30, 30),
        2,
    )
    # Add subtle background texture
    np.random.seed(42)
    noise = np.random.randint(-10, 10, base.shape).astype(np.int16)
    base_noisy = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    buf1 = io.BytesIO()
    Image.fromarray(base_noisy).save(buf1, format="JPEG", quality=75)
    buf1.seek(0)
    base_gen1 = np.array(Image.open(buf1))

    # 2. Spliced patch: an alien texture/stamp with sharp details
    patch = np.full((120, 180, 3), 200, dtype=np.uint8)
    cv2.circle(patch, (90, 60), 40, (180, 20, 20), 4)
    cv2.putText(patch, "MODIFIED", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 20, 20), 2)

    # Insert patch into base_gen1
    tampered = base_gen1.copy()
    tampered[250:370, 300:480] = patch

    # Save tampered image at quality 75
    spliced_path = tmp_path / "spliced.jpg"
    Image.fromarray(tampered).save(str(spliced_path), format="JPEG", quality=75)
    return spliced_path


def test_ela_on_clean_image(clean_image: Path, tmp_path: Path):
    """Verify ELA runs cleanly and returns valid statistical metrics."""
    analyzer = ErrorLevelAnalyzer(quality=95)
    heatmap_path = tmp_path / "clean_heatmap.png"

    result = analyzer.compute_ela(clean_image, output_heatmap_path=heatmap_path)

    assert isinstance(result, ELAResult)
    assert result.global_mean_error >= 0.0
    assert result.global_std_error >= 0.0
    assert result.max_local_error >= 0.0
    assert heatmap_path.exists()


def test_ela_detects_spliced_patch(spliced_image: Path, tmp_path: Path):
    """Verify ELA detects localized compression differential and generates bounding box."""
    analyzer = ErrorLevelAnalyzer(quality=95, anomaly_sigma_threshold=2.5, min_region_area_px=50)
    heatmap_path = tmp_path / "spliced_heatmap.png"

    result = analyzer.compute_ela(spliced_image, output_heatmap_path=heatmap_path)

    assert isinstance(result, ELAResult)
    assert result.anomaly_detected is True
    assert result.anomaly_score > 0.0
    assert len(result.anomalous_regions) > 0
    assert heatmap_path.exists()

    # Bounding box should overlap with the spliced region [ymin ~0.33, xmin ~0.25]
    detected_box = result.anomalous_regions[0]
    assert 0.0 <= detected_box.ymin <= 1.0
    assert 0.0 <= detected_box.xmin <= 1.0
