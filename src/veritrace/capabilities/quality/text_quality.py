"""Text Quality Analyzer.

Evaluates quality, density, and integrity of extracted text strings:
- Empty or very short extracted text
- Unicode replacement characters (e.g. '\ufffd') and unmapped glyph artifacts
- Excessive symbol-to-text ratio
- Excessive whitespace and word fragmentation
- Character density relative to page area
- Intra-document text extraction inconsistency across pages

Boundary: This module accepts text as input; it does NOT perform OCR or extraction.
"""

from veritrace.capabilities.quality.models import (
    QualityDimension,
    QualityIssue,
    QualitySeverity,
    TextQualityMetrics,
)
from veritrace.capabilities.quality.rules import DEFAULT_THRESHOLDS, QualityThresholds


class TextQualityAnalyzer:
    """Evaluates raw or OCR-extracted text strings without performing extraction."""

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def analyze_page_text(
        self,
        text: str | None,
        page_number: int = 1,
        page_width_points: float | None = None,
        page_height_points: float | None = None,
    ) -> tuple[TextQualityMetrics, list[QualityIssue]]:
        """Assess the quality of extracted text for an individual page.

        Args:
            text: Extracted text string (or None/empty).
            page_number: 1-based page index.
            page_width_points: Optional page width in points (72 pt/inch).
            page_height_points: Optional page height in points.

        Returns:
            Tuple of (TextQualityMetrics, list[QualityIssue]).
        """
        issues: list[QualityIssue] = []

        if text is None or not text.strip():
            metrics = TextQualityMetrics(
                char_count=0,
                word_count=0,
                line_count=0,
                replacement_char_count=0,
                symbol_ratio=0.0,
                whitespace_ratio=1.0 if text is not None else 0.0,
                fragmented_word_ratio=0.0,
                text_density_cpi=0.0,
            )
            issues.append(
                QualityIssue(
                    code="TXT_EMPTY_EXTRACTION",
                    title="Empty Text Extraction",
                    message="No text characters were extracted from this page.",
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.HIGH,
                    confidence=1.0,
                    measured_value=0.0,
                    threshold=float(self.thresholds.text_min_chars_per_page),
                    page_number=page_number,
                )
            )
            return metrics, issues

        cleaned_text = text
        char_count = len(cleaned_text)
        stripped_len = len(cleaned_text.strip())

        lines = [ln for ln in cleaned_text.splitlines() if ln.strip()]
        line_count = len(lines)

        words = cleaned_text.split()
        word_count = len(words)

        # 1. Very short text
        if stripped_len < self.thresholds.text_very_short_chars:
            issues.append(
                QualityIssue(
                    code="TXT_VERY_SHORT",
                    title="Extremely Sparse Text Content",
                    message=(
                        f"Only {stripped_len} characters extracted; page appears abnormally sparse."
                    ),
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.HIGH,
                    confidence=0.95,
                    measured_value=float(stripped_len),
                    threshold=float(self.thresholds.text_very_short_chars),
                    page_number=page_number,
                    details={"char_count": stripped_len},
                )
            )
        elif stripped_len < self.thresholds.text_min_chars_per_page:
            issues.append(
                QualityIssue(
                    code="TXT_VERY_SHORT",
                    title="Sparse Text Content",
                    message=(
                        f"Page yielded only {stripped_len} characters, below expected document min."
                    ),
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.85,
                    measured_value=float(stripped_len),
                    threshold=float(self.thresholds.text_min_chars_per_page),
                    page_number=page_number,
                    details={"char_count": stripped_len},
                )
            )

        # 2. Replacement characters & null bytes
        replacement_count = cleaned_text.count("\ufffd") + cleaned_text.count("\x00")
        if replacement_count > 0:
            severity = QualitySeverity.HIGH if replacement_count >= 5 else QualitySeverity.MEDIUM
            issues.append(
                QualityIssue(
                    code="TXT_REPLACEMENT_CHARS",
                    title=f"Unicode Replacement / Damaged Glyphs ({replacement_count})",
                    message=(
                        f"Detected {replacement_count} replacement or null characters (\\ufffd),"
                        " indicating unmapped fonts, damaged encoding, or OCR decoding errors."
                    ),
                    dimension=QualityDimension.TEXT,
                    severity=severity,
                    confidence=1.0,
                    measured_value=float(replacement_count),
                    threshold=0.0,
                    page_number=page_number,
                    details={"replacement_char_count": replacement_count},
                )
            )

        # 3. Symbol ratio
        alphanumeric_count = sum(1 for c in cleaned_text if c.isalnum())
        whitespace_count = sum(1 for c in cleaned_text if c.isspace())
        symbol_count = char_count - alphanumeric_count - whitespace_count
        symbol_ratio = symbol_count / (char_count + 1e-6)

        if symbol_ratio > self.thresholds.text_max_symbol_ratio:
            issues.append(
                QualityIssue(
                    code="TXT_EXCESSIVE_SYMBOLS",
                    title="Excessive Symbol-to-Text Ratio",
                    message=(
                        f"Symbols account for {symbol_ratio * 100:.1f}% of extracted text, "
                        "typically indicating OCR garbage or unhandled graphics."
                    ),
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.90,
                    measured_value=round(symbol_ratio, 3),
                    threshold=self.thresholds.text_max_symbol_ratio,
                    page_number=page_number,
                    details={"symbol_count": symbol_count, "symbol_ratio": round(symbol_ratio, 3)},
                )
            )

        # 4. Whitespace ratio & unusual spacing
        whitespace_ratio = whitespace_count / (char_count + 1e-6)
        if whitespace_ratio > self.thresholds.text_max_whitespace_ratio:
            issues.append(
                QualityIssue(
                    code="TXT_UNUSUAL_WHITESPACE",
                    title="High Whitespace Ratio",
                    message="Extracted text contains excessive whitespace or scattered spacing.",
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.LOW,
                    confidence=0.80,
                    measured_value=round(whitespace_ratio, 3),
                    threshold=self.thresholds.text_max_whitespace_ratio,
                    page_number=page_number,
                    details={"whitespace_ratio": round(whitespace_ratio, 3)},
                )
            )

        # 5. Fragmented words (isolated 1-character words)
        single_char_words = sum(1 for w in words if len(w) == 1 and w.isalnum())
        fragmented_ratio = single_char_words / (word_count + 1e-6)
        if word_count >= 10 and fragmented_ratio > self.thresholds.text_max_fragmented_word_ratio:
            issues.append(
                QualityIssue(
                    code="TXT_FRAGMENTED_WORDS",
                    title="Fragmented Word Segmentation",
                    message=(
                        f"{fragmented_ratio * 100:.1f}% of words are single isolated characters, "
                        "indicating word-boundary failure or broken kerning."
                    ),
                    dimension=QualityDimension.TEXT,
                    severity=QualitySeverity.MEDIUM,
                    confidence=0.88,
                    measured_value=round(fragmented_ratio, 3),
                    threshold=self.thresholds.text_max_fragmented_word_ratio,
                    page_number=page_number,
                    details={
                        "single_char_words": single_char_words,
                        "fragmented_ratio": round(fragmented_ratio, 3),
                    },
                )
            )

        # 6. Text density (characters per square inch)
        density_cpi: float | None = None
        if (
            page_width_points
            and page_height_points
            and page_width_points > 0
            and page_height_points > 0
        ):
            area_sq_inches = (page_width_points / 72.0) * (page_height_points / 72.0)
            if area_sq_inches > 0:
                density_cpi = char_count / area_sq_inches

        metrics = TextQualityMetrics(
            char_count=char_count,
            word_count=word_count,
            line_count=line_count,
            replacement_char_count=replacement_count,
            symbol_ratio=round(symbol_ratio, 3),
            whitespace_ratio=round(whitespace_ratio, 3),
            fragmented_word_ratio=round(fragmented_ratio, 3),
            text_density_cpi=round(density_cpi, 2) if density_cpi is not None else None,
        )

        return metrics, issues

    def analyze_cross_page_consistency(
        self,
        page_texts: list[str],
    ) -> list[QualityIssue]:
        """Detect inconsistent text extraction quality across multi-page documents."""
        if len(page_texts) <= 1:
            return []

        counts = [len(t.strip()) for t in page_texts]
        mean_c = sum(counts) / len(counts)
        if mean_c <= 0:
            return []

        variance = sum((c - mean_c) ** 2 for c in counts) / len(counts)
        std_c = variance**0.5
        cv = std_c / mean_c

        issues: list[QualityIssue] = []
        if cv > self.thresholds.text_cross_page_cv_threshold:
            has_dense = any(c > 200 for c in counts)
            has_empty = any(c < 20 for c in counts)
            if has_dense and has_empty:
                issues.append(
                    QualityIssue(
                        code="TXT_INCONSISTENT_ACROSS_PAGES",
                        title="Inconsistent Extraction Across Pages",
                        message=(
                            "Significant variation in extracted text volume detected across pages "
                            f"(CV = {cv:.2f}). Some pages have rich text while others appear blank."
                        ),
                        dimension=QualityDimension.TEXT,
                        severity=QualitySeverity.MEDIUM,
                        confidence=0.90,
                        measured_value=round(cv, 3),
                        threshold=self.thresholds.text_cross_page_cv_threshold,
                        details={"page_char_counts": counts, "mean_chars": round(mean_c, 1)},
                    )
                )

        return issues
