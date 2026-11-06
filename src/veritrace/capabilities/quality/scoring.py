"""Deterministic Quality Scoring Engine.

Calculates transparent, explainable scores in [0.0, 100.0],
assigns standardized quality categories (EXCELLENT, GOOD, ACCEPTABLE, POOR, UNUSABLE),
and maps findings to explicit processing recommendations.
"""

from veritrace.capabilities.quality.models import (
    ProcessingRecommendation,
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from veritrace.capabilities.quality.rules import DEFAULT_SCORING_CONFIG, ScoringConfig


class QualityScorer:
    """Calculates deterministic quality scores and recommendations."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or DEFAULT_SCORING_CONFIG

    def compute_page_score(
        self, issues: list[QualityIssue]
    ) -> tuple[float, QualityCategory, ProcessingRecommendation, dict[str, float]]:
        """Calculate score, category, recommendation, and itemized penalties for a page.

        Args:
            issues: List of QualityIssue instances detected on this page.

        Returns:
            Tuple of (score, category, recommendation, penalties_dict).
        """
        if not issues:
            return (
                100.0,
                QualityCategory.EXCELLENT,
                ProcessingRecommendation.READY,
                {},
            )

        # Calculate itemized penalties
        raw_penalties: dict[str, float] = {}
        for issue in issues:
            deduction = self._get_deduction(issue)
            if issue.code in raw_penalties:
                raw_penalties[issue.code] = max(raw_penalties[issue.code], deduction)
            else:
                raw_penalties[issue.code] = deduction

        # Apply correlated defect dampening
        penalties = self._dampen_correlated_defects(raw_penalties)

        total_deduction = sum(penalties.values())
        score = max(0.0, min(100.0, 100.0 - total_deduction))
        score = round(score, 1)

        category = self.determine_category(score)
        recommendation = self.determine_recommendation(score, issues)

        return score, category, recommendation, penalties

    def determine_category(self, score: float) -> QualityCategory:
        """Map numerical score to standard quality band."""
        if score >= self.config.SCORE_EXCELLENT_MIN:
            return QualityCategory.EXCELLENT
        if score >= self.config.SCORE_GOOD_MIN:
            return QualityCategory.GOOD
        if score >= self.config.SCORE_ACCEPTABLE_MIN:
            return QualityCategory.ACCEPTABLE
        if score >= self.config.SCORE_POOR_MIN:
            return QualityCategory.POOR
        return QualityCategory.UNUSABLE

    def determine_recommendation(
        self, score: float, issues: list[QualityIssue]
    ) -> ProcessingRecommendation:
        """Determine downstream processing viability using deterministic rules."""
        has_critical = any(i.severity == QualitySeverity.CRITICAL for i in issues)
        has_high = any(i.severity == QualitySeverity.HIGH for i in issues)
        has_medium = any(i.severity == QualitySeverity.MEDIUM for i in issues)

        fatal_codes = {
            "PDF_CORRUPT",
            "PDF_ENCRYPTED",
            "PDF_EMPTY",
            "PDF_UNREADABLE_PAGE",
            "IMG_CRITICAL_LOW_RES",
            "PDF_FILE_NOT_FOUND",
        }
        has_fatal = any(i.code in fatal_codes for i in issues)

        if has_fatal or score < self.config.SCORE_POOR_MIN:
            return ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING

        if has_critical or has_high or score < self.config.SCORE_ACCEPTABLE_MIN:
            return ProcessingRecommendation.REQUIRES_REVIEW

        has_low = any(i.severity == QualitySeverity.LOW for i in issues)
        if has_medium or has_low or score < self.config.SCORE_EXCELLENT_MIN:
            return ProcessingRecommendation.READY_WITH_WARNINGS

        return ProcessingRecommendation.READY

    def aggregate_document_quality(
        self,
        page_scores: list[float],
        all_issues: list[QualityIssue],
    ) -> tuple[float, QualityCategory, ProcessingRecommendation]:
        """Aggregate per-page results into document-level score, category, and recommendation."""
        if not page_scores:
            fatal_codes = {"PDF_CORRUPT", "PDF_ENCRYPTED", "PDF_EMPTY", "PDF_FILE_NOT_FOUND"}
            if any(i.code in fatal_codes for i in all_issues):
                return (
                    0.0,
                    QualityCategory.UNUSABLE,
                    ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING,
                )
            return (
                100.0,
                QualityCategory.EXCELLENT,
                ProcessingRecommendation.READY,
            )

        avg_score = sum(page_scores) / len(page_scores)

        # Deduct for document-wide issues (issues without a page_number)
        doc_wide_issues = [i for i in all_issues if i.page_number is None]
        for d_issue in doc_wide_issues:
            deduction = self._get_deduction(d_issue)
            avg_score -= deduction

        final_score = max(0.0, min(100.0, avg_score))
        final_score = round(final_score, 1)

        category = self.determine_category(final_score)
        recommendation = self.determine_recommendation(final_score, all_issues)

        fatal_codes = {"PDF_CORRUPT", "PDF_ENCRYPTED", "PDF_EMPTY", "PDF_FILE_NOT_FOUND"}
        if any(i.code in fatal_codes for i in all_issues):
            recommendation = ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING

        return final_score, category, recommendation

    def _get_deduction(self, issue: QualityIssue) -> float:
        """Get point deduction for an issue code or fall back to severity default."""
        if issue.code in self.config.PENALTY_MAP:
            return self.config.PENALTY_MAP[issue.code]

        severity_defaults = {
            QualitySeverity.INFO: 0.0,
            QualitySeverity.LOW: 5.0,
            QualitySeverity.MEDIUM: 15.0,
            QualitySeverity.HIGH: 25.0,
            QualitySeverity.CRITICAL: 45.0,
        }
        return severity_defaults.get(issue.severity, 10.0)

    def _dampen_correlated_defects(self, penalties: dict[str, float]) -> dict[str, float]:
        """Dampen secondary penalty when two correlated defects share a root physical cause."""
        dampened = dict(penalties)

        # Correlated pair 1: Blur and Low Resolution
        blur_keys = [k for k in dampened if "BLUR" in k]
        res_keys = [k for k in dampened if "LOW_RES" in k or "RESOLUTION" in k]
        if blur_keys and res_keys:
            b_key = max(blur_keys, key=lambda k: dampened[k])
            r_key = max(res_keys, key=lambda k: dampened[k])
            if dampened[b_key] >= dampened[r_key]:
                dampened[r_key] = round(dampened[r_key] * self.config.CORRELATED_DEFECT_DAMPING, 1)
            else:
                dampened[b_key] = round(dampened[b_key] * self.config.CORRELATED_DEFECT_DAMPING, 1)

        # Correlated pair 2: Blank Page and Empty Text
        blank_keys = [k for k in dampened if "BLANK_PAGE" in k]
        empty_keys = [k for k in dampened if "EMPTY_EXTRACTION" in k]
        if blank_keys and empty_keys:
            e_key = empty_keys[0]
            dampened[e_key] = round(dampened[e_key] * 0.20, 1)

        return dampened
