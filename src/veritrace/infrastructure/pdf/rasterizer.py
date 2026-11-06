"""High-DPI PDF page rasterizer adapter using PyMuPDF.

Provides high-resolution (300 DPI) page rasterization to disk or in-memory arrays,
strictly respecting immutable original document storage and coordinate fidelity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import pymupdf
from PIL import Image

from veritrace.domain.exceptions.base import CorruptedDocumentError, ValidationError
from veritrace.domain.value_objects.geometry import PageDimensions


class DocumentRasterizerProtocol(Protocol):
    """Protocol for rasterizing document pages into high-resolution images."""

    def render_pages(self, pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
        """Render all pages of a PDF to high-resolution PNG images in output_dir."""
        ...


class PyMuPdfPageRasterizer:
    """Production rasterizer engine utilizing PyMuPDF for sub-pixel precision."""

    def __init__(self, default_dpi: int = 300) -> None:
        self._default_dpi = default_dpi

    def render_pages(self, pdf_path: Path, output_dir: Path, dpi: int | None = None) -> list[Path]:
        """Render all pages of a PDF to PNG files on disk.

        Args:
            pdf_path: Path to the source PDF file.
            output_dir: Directory where rasterized PNG images will be saved.
            dpi: Rendering resolution (default: 300 DPI).

        Returns:
            List of Paths to generated PNG files, ordered by page number (1-based).
        """
        if not pdf_path.exists():
            raise ValidationError(f"Source PDF does not exist: {pdf_path}")

        effective_dpi = dpi or self._default_dpi
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            doc = pymupdf.open(str(pdf_path))
        except Exception as exc:
            raise CorruptedDocumentError(f"Cannot open PDF for rasterization: {exc}") from exc

        rendered_paths: list[Path] = []
        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise CorruptedDocumentError(f"PDF contains 0 pages: {pdf_path}")

            zoom = effective_dpi / 72.0
            matrix = pymupdf.Matrix(zoom, zoom)

            for page_idx in range(total_pages):
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                out_path = output_dir / f"page_{page_idx + 1:04d}.png"
                pix.save(str(out_path))
                rendered_paths.append(out_path)

            return rendered_paths
        finally:
            doc.close()

    def render_page_to_bytes(
        self,
        content_or_path: bytes | str | Path,
        page_number: int,
        dpi: int | None = None,
    ) -> tuple[bytes, PageDimensions]:
        """Render an individual page (1-based) to PNG bytes and return dimensions.

        Args:
            content_or_path: PDF raw bytes or Path.
            page_number: 1-based page index.
            dpi: Target DPI.

        Returns:
            Tuple of (png_bytes, PageDimensions).
        """
        effective_dpi = dpi or self._default_dpi

        try:
            if isinstance(content_or_path, (str, Path)):
                doc = pymupdf.open(str(content_or_path))
            else:
                doc = pymupdf.open(stream=content_or_path, filetype="pdf")
        except Exception as exc:
            raise CorruptedDocumentError(f"Cannot open PDF: {exc}") from exc

        try:
            if page_number < 1 or page_number > len(doc):
                raise ValidationError(f"Page number {page_number} out of range [1, {len(doc)}]")

            page = doc[page_number - 1]
            zoom = effective_dpi / 72.0
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes(output="png")
            dims = PageDimensions(
                width_pixels=pix.width,
                height_pixels=pix.height,
                dpi=effective_dpi,
            )
            return png_bytes, dims
        finally:
            doc.close()

    def render_page_to_cv2(
        self,
        content_or_path: bytes | str | Path,
        page_number: int,
        dpi: int | None = None,
    ) -> tuple[np.ndarray, PageDimensions]:
        """Render an individual page (1-based) directly to an OpenCV BGR numpy array."""
        png_bytes, dims = self.render_page_to_bytes(content_or_path, page_number, dpi)
        nparr = np.frombuffer(png_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise CorruptedDocumentError(f"Failed to decode page {page_number} to image array")
        return img_bgr, dims

    def rasterize_image_file(
        self, image_path: Path, output_dir: Path, target_dpi: int | None = None
    ) -> tuple[Path, PageDimensions]:
        """Normalize an input image file (PNG, JPEG, TIFF) into the raster cache."""
        if not image_path.exists():
            raise ValidationError(f"Image file does not exist: {image_path}")

        effective_dpi = target_dpi or self._default_dpi
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"page_0001_{image_path.name}"

        try:
            with Image.open(image_path) as img:
                # Convert to RGB to strip alpha or palette modes
                rgb_img = img.convert("RGB")
                w, h = rgb_img.size
                rgb_img.save(out_path, format="PNG", dpi=(effective_dpi, effective_dpi))
                dims = PageDimensions(width_pixels=w, height_pixels=h, dpi=effective_dpi)
                return out_path, dims
        except Exception as exc:
            raise CorruptedDocumentError(f"Cannot process image file: {exc}") from exc
