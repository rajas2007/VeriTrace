"""Unit tests for Text Quality Analyzer.

Tests evaluation of extracted text quality without performing OCR:
- Clean multi-sentence text
- Completely empty text (or None)
- Very short / sparse text
- Unicode replacement characters and corrupted glyphs
- Excessive symbol-to-text ratio
- Excessive whitespace and word fragmentation
- Estimated character density per square inch
- Cross-page extraction volume consistency
"""

import pytest

from veritrace.capabilities.quality.models import QualitySeverity
from veritrace.capabilities.quality.text_quality import TextQualityAnalyzer


@pytest.fixture
def text_analyzer() -> TextQualityAnalyzer:
    return TextQualityAnalyzer()


def test_clean_text_evaluation(text_analyzer: TextQualityAnalyzer):
    """Verify that well-formed document text produces high metrics and zero issues."""
    text = (
        "This is an official verification report issued by the internal audit department. "
        "All employee compensation records for the month of October 2026 have been verified "
        "and reconciled against statutory bank transaction ledger statements."
    )
    metrics, issues = text_analyzer.analyze_page_text(text, page_number=1)

    assert metrics.char_count == len(text)
    assert metrics.word_count > 25
    assert metrics.replacement_char_count == 0
    assert metrics.symbol_ratio < 0.10
    assert metrics.fragmented_word_ratio < 0.10
    assert len(issues) == 0


def test_empty_text_evaluation(text_analyzer: TextQualityAnalyzer):
    """Verify that empty string or whitespace triggers TXT_EMPTY_EXTRACTION."""
    metrics, issues = text_analyzer.analyze_page_text("   \n\t  ", page_number=1)

    assert metrics.char_count == 0
    empty_issues = [i for i in issues if i.code == "TXT_EMPTY_EXTRACTION"]
    assert len(empty_issues) == 1
    assert empty_issues[0].severity == QualitySeverity.HIGH


def test_none_text_evaluation(text_analyzer: TextQualityAnalyzer):
    """Verify that None input is safely handled as empty extraction."""
    metrics, issues = text_analyzer.analyze_page_text(None, page_number=1)

    assert metrics.char_count == 0
    empty_issues = [i for i in issues if i.code == "TXT_EMPTY_EXTRACTION"]
    assert len(empty_issues) == 1


def test_very_short_text(text_analyzer: TextQualityAnalyzer):
    """Verify that unusually short text (< 10 chars) triggers TXT_VERY_SHORT with HIGH severity."""
    metrics, issues = text_analyzer.analyze_page_text("Page 1", page_number=1)

    assert metrics.char_count == 6
    short_issues = [i for i in issues if i.code == "TXT_VERY_SHORT"]
    assert len(short_issues) == 1
    assert short_issues[0].severity == QualitySeverity.HIGH


def test_replacement_characters(text_analyzer: TextQualityAnalyzer):
    """Verify that Unicode replacement character '\\ufffd' is detected and counted."""
    damaged_text = (
        "Employee N\ufffdme: R\ufffdjesh Sh\ufffdrma - P\ufffdN: ABCDE\ufffd\ufffd\ufffd\ufffdF"
    )
    metrics, issues = text_analyzer.analyze_page_text(damaged_text, page_number=1)

    assert metrics.replacement_char_count >= 5
    rep_issues = [i for i in issues if i.code == "TXT_REPLACEMENT_CHARS"]
    assert len(rep_issues) == 1
    assert rep_issues[0].severity == QualitySeverity.HIGH


def test_excessive_symbols(text_analyzer: TextQualityAnalyzer):
    """Verify that high symbol density triggers TXT_EXCESSIVE_SYMBOLS."""
    garbage_text = "###@@@!!! ***%%% ^^^&&& $$$ ~~~``` |||| ==== ++++ ???? >>>> <<<<"
    metrics, issues = text_analyzer.analyze_page_text(garbage_text, page_number=1)

    assert metrics.symbol_ratio > 0.40
    sym_issues = [i for i in issues if i.code == "TXT_EXCESSIVE_SYMBOLS"]
    assert len(sym_issues) == 1


def test_fragmented_words(text_analyzer: TextQualityAnalyzer):
    """Verify that excessive 1-character words trigger TXT_FRAGMENTED_WORDS."""
    fragmented = "a b c d e f g h i j k l m n o p q r s t u v w x y z regular word"
    metrics, issues = text_analyzer.analyze_page_text(fragmented, page_number=1)

    assert metrics.fragmented_word_ratio > 0.50
    frag_issues = [i for i in issues if i.code == "TXT_FRAGMENTED_WORDS"]
    assert len(frag_issues) == 1


def test_text_density_calculation(text_analyzer: TextQualityAnalyzer):
    """Verify characters-per-square-inch density calculation when page points are given."""
    text = "A" * 500  # 500 chars
    # Standard A4: 595 x 842 pt -> (595/72) * (842/72) = 8.26 * 11.69 = ~96.6 sq inches
    metrics, issues = text_analyzer.analyze_page_text(
        text,
        page_number=1,
        page_width_points=595.0,
        page_height_points=842.0,
    )
    assert metrics.text_density_cpi is not None
    # 500 / 96.6 = ~5.17 chars/sq inch
    assert 4.5 <= metrics.text_density_cpi <= 6.0


def test_cross_page_inconsistency(text_analyzer: TextQualityAnalyzer):
    """Verify that uneven extraction volume across pages triggers TXT_INCONSISTENT_ACROSS_PAGES."""
    p1 = "Detailed report with abundant information and hundreds of characters. " * 10
    p2 = "Sparse"
    p3 = "Another complete document page with several paragraphs of rich audit information. " * 8

    issues = text_analyzer.analyze_cross_page_consistency([p1, p2, p3])

    inconsistent_issues = [i for i in issues if i.code == "TXT_INCONSISTENT_ACROSS_PAGES"]
    assert len(inconsistent_issues) == 1
    assert inconsistent_issues[0].severity == QualitySeverity.MEDIUM
