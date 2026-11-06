"""Unit tests for Deterministic Quality Scoring Engine.

Tests:
- Score clamping [0.0, 100.0]
- Category assignments (EXCELLENT, GOOD, ACCEPTABLE, POOR, UNUSABLE)
- Recommendation logic (READY, READY_WITH_WARNINGS, REQUIRES_REVIEW, UNSUITABLE)
- Deterministic repeatability
- Correlated defect dampening
- Multi-page document aggregation
"""

import pytest

from veritrace.capabilities.quality.models import (
    ProcessingRecommendation,
    QualityCategory,
    QualityDimension,
    QualityIssue,
    QualitySeverity,
)
from veritrace.capabilities.quality.scoring import QualityScorer


@pytest.fixture
def scorer() -> QualityScorer:
    return QualityScorer()


def test_zero_issues_perfect_score(scorer: QualityScorer):
    """Verify that empty issues list yields perfect 100.0 score and EXCELLENT/READY."""
    score, category, rec, penalties = scorer.compute_page_score([])
    assert score == 100.0
    assert category == QualityCategory.EXCELLENT
    assert rec == ProcessingRecommendation.READY
    assert len(penalties) == 0


def test_category_score_bands(scorer: QualityScorer):
    """Verify all five quality categories against score thresholds."""
    assert scorer.determine_category(95.0) == QualityCategory.EXCELLENT
    assert scorer.determine_category(90.0) == QualityCategory.EXCELLENT
    assert scorer.determine_category(85.0) == QualityCategory.GOOD
    assert scorer.determine_category(75.0) == QualityCategory.GOOD
    assert scorer.determine_category(60.0) == QualityCategory.ACCEPTABLE
    assert scorer.determine_category(50.0) == QualityCategory.ACCEPTABLE
    assert scorer.determine_category(40.0) == QualityCategory.POOR
    assert scorer.determine_category(25.0) == QualityCategory.POOR
    assert scorer.determine_category(15.0) == QualityCategory.UNUSABLE
    assert scorer.determine_category(0.0) == QualityCategory.UNUSABLE


def test_recommendation_fatal_blocker(scorer: QualityScorer):
    """Verify fatal structural defects yield UNSUITABLE_FOR_AUTOMATED_PROCESSING."""
    fatal_issue = QualityIssue(
        code="PDF_CORRUPT",
        title="Corrupted PDF",
        message="Damaged xref table",
        dimension=QualityDimension.PDF_STRUCTURE,
        severity=QualitySeverity.CRITICAL,
    )
    score, category, rec, penalties = scorer.compute_page_score([fatal_issue])

    assert score == 0.0
    assert category == QualityCategory.UNUSABLE
    assert rec == ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING


def test_recommendation_requires_review(scorer: QualityScorer):
    """Verify that high-severity defects yield REQUIRES_REVIEW."""
    high_blur = QualityIssue(
        code="IMG_BLUR_CRITICAL",
        title="Severe Blur",
        message="Critical defocus",
        dimension=QualityDimension.IMAGE,
        severity=QualitySeverity.HIGH,
    )
    score, category, rec, penalties = scorer.compute_page_score([high_blur])

    assert score == 65.0  # 100 - 35
    assert category == QualityCategory.ACCEPTABLE
    assert rec == ProcessingRecommendation.REQUIRES_REVIEW


def test_recommendation_ready_with_warnings(scorer: QualityScorer):
    """Verify that mild/medium issues yield READY_WITH_WARNINGS."""
    mild_skew = QualityIssue(
        code="IMG_SKEWED",
        title="Tilted text",
        message="Mild tilt",
        dimension=QualityDimension.IMAGE,
        severity=QualitySeverity.LOW,
    )
    score, category, rec, penalties = scorer.compute_page_score([mild_skew])

    assert score == 88.0  # 100 - 12
    assert category == QualityCategory.GOOD
    assert rec == ProcessingRecommendation.READY_WITH_WARNINGS


def test_correlated_defect_dampening(scorer: QualityScorer):
    """Verify that correlated blur + low resolution does not excessively double-penalize."""
    blur = QualityIssue(
        code="IMG_BLUR_WARNING",
        title="Soft focus",
        message="Blurry",
        dimension=QualityDimension.IMAGE,
        severity=QualitySeverity.MEDIUM,
    )
    low_res = QualityIssue(
        code="IMG_LOW_RESOLUTION",
        title="Low resolution",
        message="Low DPI",
        dimension=QualityDimension.IMAGE,
        severity=QualitySeverity.MEDIUM,
    )

    # Individual penalties: blur=15, low_res=25
    # Combined with dampening: max is 25, the other (15) gets dampened by 0.75 -> 11.2
    # Total deduction: 25 + 11.2 = 36.2 -> Score: 63.8
    score, category, rec, penalties = scorer.compute_page_score([blur, low_res])

    assert penalties["IMG_LOW_RESOLUTION"] == 25.0
    assert penalties["IMG_BLUR_WARNING"] == pytest.approx(11.2, abs=0.1)
    assert score == pytest.approx(63.8, abs=0.2)


def test_deterministic_scoring(scorer: QualityScorer):
    """Verify identical inputs produce strictly identical numerical outputs across runs."""
    issues = [
        QualityIssue(
            code="IMG_POOR_CONTRAST",
            title="Poor contrast",
            message="Low contrast",
            dimension=QualityDimension.IMAGE,
            severity=QualitySeverity.MEDIUM,
        ),
        QualityIssue(
            code="TXT_UNUSUAL_WHITESPACE",
            title="High whitespace",
            message="Wide spacing",
            dimension=QualityDimension.TEXT,
            severity=QualitySeverity.LOW,
        ),
    ]

    s1, c1, r1, p1 = scorer.compute_page_score(issues)
    s2, c2, r2, p2 = scorer.compute_page_score(issues)

    assert s1 == s2
    assert c1 == c2
    assert r1 == r2
    assert p1 == p2


def test_document_aggregation(scorer: QualityScorer):
    """Verify multi-page aggregation computes mean score and enforces document-level constraints."""
    page_scores = [90.0, 80.0, 70.0]
    all_issues = [
        QualityIssue(
            code="PDF_MIXED_ORIENTATIONS",
            title="Mixed rotations",
            message="Mixed",
            dimension=QualityDimension.PDF_STRUCTURE,
            severity=QualitySeverity.LOW,
            page_number=None,  # Document-wide issue
        )
    ]

    # Mean of pages = 80.0; doc-wide penalty for PDF_MIXED_ORIENTATIONS is 8.0 -> final = 72.0
    doc_score, doc_cat, doc_rec = scorer.aggregate_document_quality(page_scores, all_issues)

    assert doc_score == 72.0
    assert doc_cat == QualityCategory.ACCEPTABLE
    assert doc_rec == ProcessingRecommendation.READY_WITH_WARNINGS
