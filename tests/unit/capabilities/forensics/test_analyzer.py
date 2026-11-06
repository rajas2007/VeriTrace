"""Unit tests for VisualForensicsAnalyzer orchestration facade."""

from pathlib import Path

import cv2
import numpy as np

from veritrace.capabilities.forensics.analyzer import (
    VisualForensicsAnalyzer,
    VisualForensicsProtocol,
)
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import PAGE_PREFIX, generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken


def make_token(text: str, ymin: float, xmin: float, ymax: float, xmax: float) -> ExtractedToken:
    """Helper to build token for testing."""
    return ExtractedToken(
        token_id=f"tok_{text}",
        text=text,
        raw_text=text,
        normalized_bbox=NormalizedBoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax),
        confidence=0.98,
        page_number=1,
        source_type="digital_text",  # type: ignore[arg-type]
    )


def test_analyzer_protocol_conformance():
    """Verify VisualForensicsAnalyzer conforms to VisualForensicsProtocol."""
    analyzer = VisualForensicsAnalyzer()
    assert isinstance(analyzer, VisualForensicsProtocol)


def test_analyze_page_with_spliced_token(tmp_path: Path):
    """Verify end-to-end page analysis generates findings and evidence entities."""
    analyzer = VisualForensicsAnalyzer()

    # Create dummy white page canvas
    canvas = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    canvas_path = tmp_path / "page_1.png"
    cv2.imwrite(str(canvas_path), canvas)

    # Line of tokens with a spliced digit '1'
    tokens = [
        make_token("Salary:", 0.10, 0.10, 0.13, 0.20),
        make_token("INR", 0.10, 0.22, 0.13, 0.28),
        make_token("1", 0.08, 0.30, 0.11, 0.33),  # Spliced higher baseline
        make_token("85,000", 0.10, 0.34, 0.13, 0.45),
        make_token("Payable", 0.10, 0.48, 0.13, 0.60),
    ]

    page_id = generate_id(PAGE_PREFIX)
    out_dir = tmp_path / "forensic_artifacts"
    proposals, evidence = analyzer.analyze_page(
        image_or_path=canvas_path,
        tokens=tokens,
        output_dir=out_dir,
        page_number=1,
        page_id=page_id,
    )

    # Should detect at least one font baseline anomaly proposal
    baseline_props = [
        p for p in proposals if p.category == FindingCategory.FONT_BASELINE_MISALIGNMENT
    ]
    assert len(baseline_props) >= 1

    prop = baseline_props[0]
    assert prop.epistemic_tier == EpistemicTier.SUSPECTED_MANIPULATION
    assert "Font Baseline Misalignment" in prop.title
    assert prop.confidence > 0.6
    assert prop.evidence_crop_path is not None
    assert prop.evidence_crop_path.exists()

    # Evidence entity should be created
    assert len(evidence) >= 1
    assert evidence[0].page_id == page_id
    assert Path(evidence[0].crop_image_path).exists()
