"""PDF Structural Quality Analyzer.

Uses PyMuPDF (fitz) to inspect physical and structural properties of PDF documents:
- Corrupted or unreadable PDF structures
- Password protection / encryption
- Empty documents (0 pages)
- Inaccessible or unreadable individual pages
- Blank pages (zero vector text, zero images, uniform raster)
- Unusual page dimensions (abnormally tiny or huge pages)
- Mixed page orientations or aspect ratios across the document
"""

from pathlib import Path

import pymupdf as fitz

from veritrace.capabilities.quality.models import (
    PdfStructuralMetrics,
    QualityDimension,
    QualityIssue,
    QualitySeverity,
)
from veritrace.capabilities.quality.rules import DEFAULT_THRESHOLDS, QualityThresholds


class PdfQualityAnalyzer:
    """Safely inspects PDF document structure and per-page metrics without altering files."""

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def analyze_pdf(
        self,
        pdf_input: str | Path | bytes,
    ) -> tuple[list[PdfStructuralMetrics], list[QualityIssue], int]:
        """Inspect PDF structure across all pages.

        Args:
            pdf_input: Path to PDF file or raw bytes.

        Returns:
            Tuple of (list[PdfStructuralMetrics], list[QualityIssue], page_count).
        """
        doc: fitz.Document | None = None
        issues: list[QualityIssue] = []
        page_metrics: list[PdfStructuralMetrics] = []

        try:
            if isinstance(pdf_input, bytes):
                doc = fitz.open(stream=pdf_input, filetype="pdf")
            else:
                pdf_path = Path(pdf_input)
                if not pdf_path.exists():
                    issues.append(
                        QualityIssue(
                            code="PDF_FILE_NOT_FOUND",
                            title="PDF File Not Found",
                            message=f"The specified PDF path does not exist: {pdf_path}",
                            dimension=QualityDimension.PDF_STRUCTURE,
                            severity=QualitySeverity.CRITICAL,
                            confidence=1.0,
                        )
                    )
                    return [], issues, 0
                doc = fitz.open(str(pdf_path))

            # 1. Encryption / Password protection
            if doc.is_encrypted:
                issues.append(
                    QualityIssue(
                        code="PDF_ENCRYPTED",
                        title="Password Protected / Encrypted PDF",
                        message=(
                            "The PDF file is encrypted and cannot be parsed without password."
                        ),
                        dimension=QualityDimension.PDF_STRUCTURE,
                        severity=QualitySeverity.CRITICAL,
                        confidence=1.0,
                        details={"is_encrypted": True, "needs_pass": doc.needs_pass},
                    )
                )
                return [], issues, 0

            page_count = doc.page_count

            # 2. Empty document
            if page_count == 0:
                issues.append(
                    QualityIssue(
                        code="PDF_EMPTY",
                        title="Empty PDF Document",
                        message="The PDF file contains 0 pages.",
                        dimension=QualityDimension.PDF_STRUCTURE,
                        severity=QualitySeverity.CRITICAL,
                        confidence=1.0,
                        measured_value=0.0,
                        threshold=1.0,
                    )
                )
                return [], issues, 0

            orientations: set[int] = set()
            aspect_ratios: list[float] = []

            for pno in range(page_count):
                page_num_1based = pno + 1
                try:
                    page = doc.load_page(pno)
                except Exception as ex:
                    issues.append(
                        QualityIssue(
                            code="PDF_UNREADABLE_PAGE",
                            title=f"Unreadable Page {page_num_1based}",
                            message=f"Page {page_num_1based} could not be loaded: {ex}",
                            dimension=QualityDimension.PDF_STRUCTURE,
                            severity=QualitySeverity.CRITICAL,
                            confidence=1.0,
                            page_number=page_num_1based,
                            details={"error": str(ex)},
                        )
                    )
                    continue

                rect = page.rect
                width = float(rect.width)
                height = float(rect.height)
                aspect = float(width / (height + 1e-6))
                rotation = int(page.rotation)

                orientations.add(rotation)
                aspect_ratios.append(aspect)

                # Check text layer and image presence
                text = page.get_text("text").strip()
                has_text = len(text) > 0
                img_list = page.get_images()
                image_count = len(img_list)

                # Check blank page
                is_blank = (not has_text) and (image_count == 0)
                if is_blank:
                    issues.append(
                        QualityIssue(
                            code="PDF_BLANK_PAGE",
                            title=f"Blank PDF Page {page_num_1based}",
                            message=(
                                f"Page {page_num_1based} contains neither digital text streams "
                                "nor embedded raster images."
                            ),
                            dimension=QualityDimension.PDF_STRUCTURE,
                            severity=QualitySeverity.HIGH,
                            confidence=0.98,
                            page_number=page_num_1based,
                            details={"text_length": len(text), "image_count": image_count},
                        )
                    )

                # Check unusual page dimensions
                is_unusual_dim = (
                    width < self.thresholds.pdf_min_dimension_points
                    or height < self.thresholds.pdf_min_dimension_points
                    or width > self.thresholds.pdf_max_dimension_points
                    or height > self.thresholds.pdf_max_dimension_points
                )
                if is_unusual_dim:
                    issues.append(
                        QualityIssue(
                            code="PDF_UNUSUAL_DIMENSIONS",
                            title=f"Unusual Dimensions on Page {page_num_1based}",
                            message=(
                                f"Page {page_num_1based} dimensions ({width:.1f} x {height:.1f} pt)"
                                " deviate significantly from standard document sizes."
                            ),
                            dimension=QualityDimension.PDF_STRUCTURE,
                            severity=QualitySeverity.LOW,
                            confidence=0.90,
                            page_number=page_num_1based,
                            details={"width_pt": width, "height_pt": height},
                        )
                    )

                m = PdfStructuralMetrics(
                    page_number=page_num_1based,
                    width_points=round(width, 1),
                    height_points=round(height, 1),
                    aspect_ratio=round(aspect, 3),
                    rotation_degrees=rotation,
                    has_text_layer=has_text,
                    image_count=image_count,
                    is_blank=is_blank,
                    is_unusual_dimensions=is_unusual_dim,
                )
                page_metrics.append(m)

            # 3. Document-wide checks: mixed orientations
            if len(orientations) > 1:
                rot_str = str(sorted(orientations))
                issues.append(
                    QualityIssue(
                        code="PDF_MIXED_ORIENTATIONS",
                        title="Mixed Page Orientations in PDF",
                        message=(
                            f"The document contains pages with differing rotations ({rot_str}°), "
                            "indicating inconsistent scan alignment."
                        ),
                        dimension=QualityDimension.PDF_STRUCTURE,
                        severity=QualitySeverity.LOW,
                        confidence=1.0,
                        details={"rotations": sorted(orientations)},
                    )
                )

            # Check mixed aspect ratios (e.g., portrait and landscape mix)
            has_portrait = any(a < 0.9 for a in aspect_ratios)
            has_landscape = any(a > 1.1 for a in aspect_ratios)
            if has_portrait and has_landscape and len(orientations) <= 1:
                issues.append(
                    QualityIssue(
                        code="PDF_MIXED_ASPECT_RATIOS",
                        title="Mixed Page Formats (Portrait & Landscape)",
                        message="Document contains both portrait and landscape formatted pages.",
                        dimension=QualityDimension.PDF_STRUCTURE,
                        severity=QualitySeverity.INFO,
                        confidence=0.95,
                        details={"aspect_ratios": [round(a, 2) for a in aspect_ratios]},
                    )
                )

            return page_metrics, issues, page_count

        except fitz.FileDataError as ex:
            issues.append(
                QualityIssue(
                    code="PDF_CORRUPT",
                    title="Corrupted PDF File Structure",
                    message=f"PDF header or xref table is damaged and cannot be parsed: {ex}",
                    dimension=QualityDimension.PDF_STRUCTURE,
                    severity=QualitySeverity.CRITICAL,
                    confidence=1.0,
                    details={"error": str(ex)},
                )
            )
            return [], issues, 0
        except Exception as ex:
            issues.append(
                QualityIssue(
                    code="PDF_CORRUPT",
                    title="Unreadable PDF File",
                    message=f"An unexpected error occurred while reading the PDF: {ex}",
                    dimension=QualityDimension.PDF_STRUCTURE,
                    severity=QualitySeverity.CRITICAL,
                    confidence=0.95,
                    details={"error": str(ex)},
                )
            )
            return [], issues, 0
        finally:
            if doc is not None:
                doc.close()
