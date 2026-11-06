"""Unit tests for FontBaselineAnalyzer."""

from veritrace.capabilities.forensics.baseline import FontBaselineAnalyzer
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.provenance import ExtractedToken


def make_token(text: str, ymin: float, xmin: float, ymax: float, xmax: float) -> ExtractedToken:
    """Helper to build a mock token with normalized bounding box."""
    return ExtractedToken(
        token_id=f"tok_{text}",
        text=text,
        raw_text=text,
        normalized_bbox=NormalizedBoundingBox(ymin=ymin, xmin=xmin, ymax=ymax, xmax=xmax),
        confidence=0.99,
        page_number=1,
        source_type=ExtractionSourceType.DIGITAL_TEXT,
    )


def test_baseline_group_tokens_into_lines():
    """Verify horizontal tokens are correctly grouped into physical text lines."""
    analyzer = FontBaselineAnalyzer()

    # Line 1: 3 tokens around y ~ 0.1
    t1 = make_token("Monthly", 0.09, 0.1, 0.12, 0.2)
    t2 = make_token("Gross", 0.091, 0.25, 0.121, 0.35)
    t3 = make_token("Salary", 0.09, 0.4, 0.12, 0.5)

    # Line 2: 2 tokens around y ~ 0.2
    t4 = make_token("Net", 0.19, 0.1, 0.22, 0.2)
    t5 = make_token("Payable", 0.191, 0.25, 0.221, 0.35)

    tokens = [t4, t1, t5, t3, t2]  # Unordered
    lines = analyzer.group_tokens_into_lines(tokens)

    assert len(lines) == 2
    # Verify line 1 has 3 tokens in left-to-right order
    assert len(lines[0]) == 3
    assert [t.raw_text for t in lines[0]] == ["Monthly", "Gross", "Salary"]
    # Line 2 has 2 tokens
    assert len(lines[1]) == 2
    assert [t.raw_text for t in lines[1]] == ["Net", "Payable"]


def test_detect_baseline_misalignment_spliced_digit():
    """Verify detection of an elevated/dropped spliced digit (> 2.5 sigma)."""
    analyzer = FontBaselineAnalyzer(sigma_threshold=2.5, min_residual_px=3.0)

    # Line of tokens representing: "Amount: ₹ 1 85,000 Verified"
    # Page height = 3000px
    # Normal baseline is ymax = 0.100 (300px)
    # Token "1" is spliced with ymax = 0.092 (276px, an elevation of 24 pixels!)
    tokens = [
        make_token("Amount:", 0.08, 0.10, 0.100, 0.18),
        make_token("INR", 0.08, 0.20, 0.100, 0.26),
        make_token("1", 0.072, 0.28, 0.092, 0.30),  # Spliced elevated digit '1'
        make_token("85,000", 0.08, 0.31, 0.100, 0.40),
        make_token("Net", 0.08, 0.42, 0.100, 0.48),
        make_token("Salary", 0.08, 0.50, 0.100, 0.58),
    ]

    anomalies = analyzer.detect_baseline_misalignments(
        tokens, page_width_px=2000, page_height_px=3000
    )

    assert len(anomalies) >= 1
    spliced_anom = next((a for a in anomalies if a.token_text == "1"), None)
    assert spliced_anom is not None
    assert spliced_anom.baseline_residual_px > 15.0
    assert spliced_anom.baseline_residual_sigma >= 2.5


def test_clean_aligned_line_produces_no_anomalies():
    """Verify a normally printed line with minor optical jitter produces zero anomalies."""
    analyzer = FontBaselineAnalyzer(sigma_threshold=2.5, min_residual_px=3.0)

    # Naturally aligned line with sub-pixel variations
    tokens = [
        make_token("Employee", 0.10, 0.10, 0.12, 0.22),
        make_token("Name:", 0.1005, 0.24, 0.1205, 0.32),
        make_token("Shravan", 0.10, 0.34, 0.12, 0.44),
        make_token("Kumar", 0.1002, 0.46, 0.1202, 0.54),
        make_token("Verified", 0.10, 0.56, 0.12, 0.66),
    ]

    anomalies = analyzer.detect_baseline_misalignments(
        tokens, page_width_px=2000, page_height_px=3000
    )
    assert len(anomalies) == 0
