"""Unit tests for Document Quality Assessment Orchestrator (DocumentQualityAnalyzer).

Tests:
- End-to-end PDF evaluation with text concordance
- End-to-end image evaluation (PNG/JPEG)
- File not found and unsupported format handling
- Executive summary generation
- Direct image and text evaluation methods
- Processing performance benchmarks
"""

import time
from pathlib import Path

import cv2
import pytest

from tests.fixtures.quality.generators import (
    create_clean_document_image,
    create_synthetic_pdf,
)
from veritrace.capabilities.quality.analyzer import DocumentQualityAnalyzer
from veritrace.capabilities.quality.models import (
    ProcessingRecommendation,
    QualityCategory,
)


@pytest.fixture
def analyzer() -> DocumentQualityAnalyzer:
    return DocumentQualityAnalyzer()


def test_analyze_clean_pdf(analyzer: DocumentQualityAnalyzer, tmp_path: Path):
    """Verify end-to-end evaluation of a clean 2-page PDF document."""
    pdf_path = tmp_path / "valid_doc.pdf"
    create_synthetic_pdf(pdf_path, num_pages=2)

    page_texts = [
        (
            "VERITRACE SYNTHETIC AUDIT REPORT - PAGE 1 Monthly Basic Pay: "
            "INR 85,000.00 Gross: INR 1,00,000.00"
        ),
        "VERITRACE SYNTHETIC AUDIT REPORT - PAGE 2 Verified audit trail for forensic evaluation.",
    ]

    result = analyzer.analyze_document(
        pdf_path,
        page_texts=page_texts,
        document_id="DOC-TEST-001",
    )

    assert result.document_id == "DOC-TEST-001"
    assert result.file_type == "PDF"
    assert result.page_count == 2
    assert result.overall_score >= 85.0
    assert result.category in (QualityCategory.EXCELLENT, QualityCategory.GOOD)
    assert result.is_processable is True
    assert len(result.pages) == 2
    assert "Quality Score:" in result.summary


def test_analyze_image_file(analyzer: DocumentQualityAnalyzer, tmp_path: Path):
    """Verify end-to-end evaluation of a PNG image file."""
    img_path = tmp_path / "salary_slip.png"
    img = create_clean_document_image(1200, 1600)
    cv2.imwrite(str(img_path), img)

    result = analyzer.analyze_document(
        img_path,
        page_texts=[
            "VERITRACE AUDIT CERTIFICATE Record Entry 1000 Verified compliance status VALID"
        ],
        document_id="IMG-TEST-002",
    )

    assert result.document_id == "IMG-TEST-002"
    assert result.file_type == "PNG"
    assert result.page_count == 1
    assert result.overall_score >= 85.0
    assert result.is_processable is True


def test_file_not_found(analyzer: DocumentQualityAnalyzer, tmp_path: Path):
    """Verify non-existent file path returns clean failure without unhandled crash."""
    missing = tmp_path / "missing_file.pdf"
    result = analyzer.analyze_document(missing)

    assert result.overall_score == 0.0
    assert result.is_processable is False
    assert result.recommendation == ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING
    assert any(i.code == "FILE_NOT_FOUND" for i in result.issues)


def test_unsupported_format(analyzer: DocumentQualityAnalyzer, tmp_path: Path):
    """Verify unsupported file format (e.g. .exe or .zip) returns typed error."""
    bad_file = tmp_path / "archive.zip"
    bad_file.write_bytes(b"PK\x03\x04DummyZipContent")

    result = analyzer.analyze_document(bad_file)

    assert result.overall_score == 0.0
    assert result.is_processable is False
    assert any(i.code == "UNSUPPORTED_FORMAT" for i in result.issues)


def test_direct_image_analysis(analyzer: DocumentQualityAnalyzer):
    """Verify direct in-memory numpy array image evaluation."""
    img = create_clean_document_image(1200, 1600)
    page_res = analyzer.analyze_image(
        img,
        page_text="This is a valid extracted page text for audit verification.",
        page_number=1,
    )

    assert page_res.page_number == 1
    assert page_res.image_metrics is not None
    assert page_res.score >= 80.0


def test_direct_text_analysis(analyzer: DocumentQualityAnalyzer):
    """Verify direct standalone text quality assessment."""
    metrics, issues = analyzer.analyze_text(
        "Clean single sentence audit verification.",
        page_number=1,
    )
    assert metrics.char_count > 20
    assert len(issues) == 0


def test_processing_performance(analyzer: DocumentQualityAnalyzer, tmp_path: Path):
    """Verify that analyzing a standard 2-page document executes well within 1.0 second."""
    pdf_path = tmp_path / "perf_doc.pdf"
    create_synthetic_pdf(pdf_path, num_pages=2)

    t0 = time.perf_counter()
    result = analyzer.analyze_document(pdf_path)
    elapsed = time.perf_counter() - t0

    assert elapsed < 1.0, f"Analysis took {elapsed:.3f}s, expected < 1.0s"
    assert result.overall_score > 0.0
    assert "elapsed_seconds" in result.metadata
