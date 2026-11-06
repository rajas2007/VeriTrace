"""Unit tests for PDF Structural Quality Analyzer.

Tests PyMuPDF structural inspections:
- Clean multi-page PDF
- Empty PDF (0 pages)
- Corrupted PDF structure
- Password-protected / encrypted PDF
- Blank pages in PDF
- Mixed page orientations & aspect ratios
- Non-existent PDF file handling
"""

from pathlib import Path

import pymupdf as fitz
import pytest

from tests.fixtures.quality.generators import create_synthetic_pdf
from veritrace.capabilities.quality.models import QualitySeverity
from veritrace.capabilities.quality.pdf_quality import PdfQualityAnalyzer


@pytest.fixture
def pdf_analyzer() -> PdfQualityAnalyzer:
    return PdfQualityAnalyzer()


def test_clean_multi_page_pdf(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify clean 3-page synthetic PDF produces no structural errors."""
    pdf_path = tmp_path / "clean_sample.pdf"
    create_synthetic_pdf(pdf_path, num_pages=3)

    metrics, issues, count = pdf_analyzer.analyze_pdf(pdf_path)

    assert count == 3
    assert len(metrics) == 3
    for m in metrics:
        assert m.has_text_layer is True
        assert m.is_blank is False
        assert m.width_points == 595.0
        assert m.height_points == 842.0

    criticals = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
    assert len(criticals) == 0


def test_empty_pdf(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify empty PDF (0 pages) is flagged with PDF_EMPTY."""
    pdf_path = tmp_path / "empty.pdf"
    # Construct a valid PDF structure with 0 pages in the page tree
    empty_pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n115\n%%EOF"
    )
    pdf_path.write_bytes(empty_pdf_bytes)

    metrics, issues, count = pdf_analyzer.analyze_pdf(pdf_path)

    assert count == 0
    assert len(metrics) == 0
    empty_issues = [i for i in issues if i.code == "PDF_EMPTY"]
    assert len(empty_issues) == 1
    assert empty_issues[0].severity == QualitySeverity.CRITICAL


def test_corrupted_pdf(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify malformed bytes trigger PDF_CORRUPT."""
    corrupt_path = tmp_path / "corrupt.pdf"
    corrupt_path.write_bytes(b"%PDF-1.7\nCorrupted binary garbage without xref or catalog trailer")

    metrics, issues, count = pdf_analyzer.analyze_pdf(corrupt_path)

    assert count == 0
    corrupt_issues = [i for i in issues if i.code == "PDF_CORRUPT"]
    assert len(corrupt_issues) == 1
    assert corrupt_issues[0].severity == QualitySeverity.CRITICAL


def test_encrypted_pdf(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify password protected PDF triggers PDF_ENCRYPTED."""
    enc_path = tmp_path / "encrypted.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Confidential payroll data")
    # Save with user and owner password
    doc.save(
        str(enc_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,  # type: ignore[attr-defined]
        user_pw="secret123",
        owner_pw="master123",
    )
    doc.close()

    metrics, issues, count = pdf_analyzer.analyze_pdf(enc_path)

    enc_issues = [i for i in issues if i.code == "PDF_ENCRYPTED"]
    assert len(enc_issues) == 1
    assert enc_issues[0].severity == QualitySeverity.CRITICAL


def test_blank_page_in_pdf(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify that a page without text and without images is flagged as PDF_BLANK_PAGE."""
    pdf_path = tmp_path / "has_blank.pdf"
    # Page index 1 (second page) is blank
    create_synthetic_pdf(pdf_path, num_pages=2, blank_page_index=1)

    metrics, issues, count = pdf_analyzer.analyze_pdf(pdf_path)

    assert count == 2
    assert metrics[0].is_blank is False
    assert metrics[1].is_blank is True

    blank_issues = [i for i in issues if i.code == "PDF_BLANK_PAGE"]
    assert len(blank_issues) == 1
    assert blank_issues[0].page_number == 2


def test_mixed_page_orientations(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify that mixing portrait and landscape formats triggers PDF_MIXED_ORIENTATIONS."""
    pdf_path = tmp_path / "mixed_orient.pdf"
    doc = fitz.open()
    # Page 1: 0 degrees rotation
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(fitz.Point(72, 72), "Portrait page")
    # Page 2: 90 degrees rotation
    p2 = doc.new_page(width=595, height=842)
    p2.set_rotation(90)
    p2.insert_text(fitz.Point(72, 72), "Rotated page")
    doc.save(str(pdf_path))
    doc.close()

    metrics, issues, count = pdf_analyzer.analyze_pdf(pdf_path)

    assert count == 2
    mixed_issues = [i for i in issues if i.code == "PDF_MIXED_ORIENTATIONS"]
    assert len(mixed_issues) == 1


def test_nonexistent_pdf_file(pdf_analyzer: PdfQualityAnalyzer, tmp_path: Path):
    """Verify non-existent file path returns PDF_FILE_NOT_FOUND."""
    missing = tmp_path / "nonexistent.pdf"
    metrics, issues, count = pdf_analyzer.analyze_pdf(missing)

    assert count == 0
    missing_issues = [i for i in issues if i.code == "PDF_FILE_NOT_FOUND"]
    assert len(missing_issues) == 1
    assert missing_issues[0].severity == QualitySeverity.CRITICAL
