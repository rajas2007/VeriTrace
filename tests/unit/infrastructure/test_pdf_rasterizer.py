"""Unit tests for PyMuPdfPageRasterizer in infrastructure/pdf."""

from pathlib import Path

import pymupdf
import pytest

from veritrace.domain.exceptions.base import ValidationError
from veritrace.infrastructure.pdf.rasterizer import PyMuPdfPageRasterizer


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Generate a clean 2-page vector test PDF."""
    pdf_path = tmp_path / "test_doc.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(pymupdf.Point(72, 100), "VeriTrace Page One Test Content", fontsize=14)

    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(pymupdf.Point(72, 100), "VeriTrace Page Two Test Content", fontsize=14)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_rasterizer_render_pages(sample_pdf: Path, tmp_path: Path):
    """Verify render_pages writes PNG files for all pages with 300 DPI scaling."""
    rasterizer = PyMuPdfPageRasterizer(default_dpi=150)
    out_dir = tmp_path / "rendered"
    png_paths = rasterizer.render_pages(sample_pdf, out_dir, dpi=150)

    assert len(png_paths) == 2
    for p in png_paths:
        assert p.exists()
        assert p.suffix == ".png"
        assert p.stat().st_size > 0


def test_rasterizer_render_page_to_bytes(sample_pdf: Path):
    """Verify in-memory page rendering to PNG bytes and dimensions."""
    rasterizer = PyMuPdfPageRasterizer()
    png_bytes, dims = rasterizer.render_page_to_bytes(sample_pdf, page_number=1, dpi=300)

    assert len(png_bytes) > 0
    assert dims.dpi == 300
    assert dims.width_pixels > 2000
    assert dims.height_pixels > 3000


def test_rasterizer_render_page_to_cv2(sample_pdf: Path):
    """Verify direct OpenCV BGR ndarray rendering."""
    rasterizer = PyMuPdfPageRasterizer()
    img_bgr, dims = rasterizer.render_page_to_cv2(sample_pdf, page_number=1, dpi=150)

    assert img_bgr is not None
    assert len(img_bgr.shape) == 3
    assert img_bgr.shape[2] == 3
    assert img_bgr.shape[0] == dims.height_pixels
    assert img_bgr.shape[1] == dims.width_pixels


def test_rasterizer_invalid_page_number(sample_pdf: Path):
    """Verify out-of-range page numbers raise ValidationError."""
    rasterizer = PyMuPdfPageRasterizer()
    with pytest.raises(ValidationError, match="out of range"):
        rasterizer.render_page_to_bytes(sample_pdf, page_number=99)


def test_rasterizer_missing_file(tmp_path: Path):
    """Verify missing file raises ValidationError."""
    rasterizer = PyMuPdfPageRasterizer()
    with pytest.raises(ValidationError, match="does not exist"):
        rasterizer.render_pages(tmp_path / "non_existent.pdf", tmp_path / "out")
