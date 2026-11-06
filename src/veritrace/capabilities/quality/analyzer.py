"""Document Quality Assessment Orchestrator.

Provides the primary public API for VeriTrace quality assessment.
Evaluates industrial documents (PDF, PNG, JPEG, TIFF) across image,
structural, and text dimensions with deterministic scoring and explanations.
"""

import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz
from PIL import Image

from veritrace.capabilities.quality.image_quality import ImageQualityAnalyzer
from veritrace.capabilities.quality.models import (
    DocumentQualityResult,
    PageQualityResult,
    ProcessingRecommendation,
    QualityCategory,
    QualityDimension,
    QualityIssue,
    QualitySeverity,
    TextQualityMetrics,
)
from veritrace.capabilities.quality.page_quality import PageQualityAnalyzer
from veritrace.capabilities.quality.pdf_quality import PdfQualityAnalyzer
from veritrace.capabilities.quality.rules import DEFAULT_THRESHOLDS, QualityThresholds
from veritrace.capabilities.quality.scoring import QualityScorer
from veritrace.capabilities.quality.text_quality import TextQualityAnalyzer


class DocumentQualityAnalyzer:
    """Primary entry point for document and page quality assessment.

    Follows strict forensic neutrality and layered monolith boundaries:
    - Independent of GUI and persistence layers
    - Deterministic scoring in [0.0, 100.0]
    - Transparent explanations and raw empirical measurements
    """

    def __init__(
        self,
        thresholds: QualityThresholds | None = None,
        scoring_config: QualityScorer | None = None,
    ) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.scorer = scoring_config or QualityScorer()
        self.pdf_analyzer = PdfQualityAnalyzer(self.thresholds)
        self.image_analyzer = ImageQualityAnalyzer(self.thresholds)
        self.text_analyzer = TextQualityAnalyzer(self.thresholds)
        self.page_analyzer = PageQualityAnalyzer(self.thresholds, self.scorer)

    def analyze_document(
        self,
        file_path: str | Path,
        page_texts: list[str] | None = None,
        document_id: str | None = None,
    ) -> DocumentQualityResult:
        """Run full multi-factor quality assessment on a document file.

        Args:
            file_path: Path to PDF or image file (PNG, JPEG, TIFF, BMP).
            page_texts: Optional list of extracted text strings per page.
            document_id: Optional UUID or reference code for tracking.

        Returns:
            DocumentQualityResult with overall score, recommendation, and per-page metrics.
        """
        start_time = time.perf_counter()
        path = Path(file_path)

        if not path.exists():
            issue = QualityIssue(
                code="FILE_NOT_FOUND",
                title="File Not Found",
                message=f"The requested file was not found on disk: {path}",
                dimension=QualityDimension.PDF_STRUCTURE,
                severity=QualitySeverity.CRITICAL,
                confidence=1.0,
            )
            return DocumentQualityResult(
                document_id=document_id,
                file_path=str(path),
                file_type="UNKNOWN",
                page_count=0,
                overall_score=0.0,
                category=QualityCategory.UNUSABLE,
                recommendation=ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING,
                is_processable=False,
                issues=[issue],
                pages=[],
                summary="Quality assessment failed: file does not exist on disk.",
                metadata={"elapsed_seconds": round(time.perf_counter() - start_time, 4)},
            )

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            result = self.analyze_pdf(path, page_texts=page_texts, document_id=document_id)
        elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}:
            result = self._analyze_image_file(path, page_texts=page_texts, document_id=document_id)
        else:
            issue = QualityIssue(
                code="UNSUPPORTED_FORMAT",
                title="Unsupported File Format",
                message=f"File extension '{suffix}' is not supported for quality evaluation.",
                dimension=QualityDimension.IMAGE,
                severity=QualitySeverity.CRITICAL,
                confidence=1.0,
                details={"suffix": suffix},
            )
            return DocumentQualityResult(
                document_id=document_id,
                file_path=str(path),
                file_type=suffix.upper().lstrip("."),
                page_count=0,
                overall_score=0.0,
                category=QualityCategory.UNUSABLE,
                recommendation=ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING,
                is_processable=False,
                issues=[issue],
                pages=[],
                summary=f"Quality assessment failed: unsupported file extension '{suffix}'.",
                metadata={"elapsed_seconds": round(time.perf_counter() - start_time, 4)},
            )

        elapsed = round(time.perf_counter() - start_time, 4)
        result.metadata["elapsed_seconds"] = elapsed
        return result

    def analyze_pdf(
        self,
        pdf_path: str | Path,
        page_texts: list[str] | None = None,
        document_id: str | None = None,
    ) -> DocumentQualityResult:
        """Inspect and score a multi-page PDF document."""
        path = Path(pdf_path)
        pdf_metrics, pdf_issues, page_count = self.pdf_analyzer.analyze_pdf(path)

        # Fatal PDF failure (e.g. encrypted or corrupt)
        fatal_codes = {"PDF_CORRUPT", "PDF_ENCRYPTED", "PDF_EMPTY", "PDF_FILE_NOT_FOUND"}
        if any(i.code in fatal_codes for i in pdf_issues) or page_count == 0:
            return DocumentQualityResult(
                document_id=document_id,
                file_path=str(path),
                file_type="PDF",
                page_count=page_count,
                overall_score=0.0,
                category=QualityCategory.UNUSABLE,
                recommendation=ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING,
                is_processable=False,
                issues=pdf_issues,
                pages=[],
                summary="PDF document is structurally unreadable, corrupted, or encrypted.",
            )

        doc = fitz.open(str(path))
        page_results: list[PageQualityResult] = []
        all_issues: list[QualityIssue] = list(pdf_issues)

        try:
            for pno in range(page_count):
                page_num = pno + 1
                p_metric = pdf_metrics[pno] if pno < len(pdf_metrics) else None

                page = doc.load_page(pno)
                pix = page.get_pixmap(dpi=150)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                if pix.n == 4:
                    img_data = img_data[:, :, :3]

                p_text = None
                if page_texts and pno < len(page_texts):
                    p_text = page_texts[pno]

                p_result = self.page_analyzer.analyze_page(
                    image_input=img_data,
                    text_input=p_text,
                    pdf_metrics=p_metric,
                    page_number=page_num,
                )
                page_results.append(p_result)
                all_issues.extend(p_result.issues)

        finally:
            doc.close()

        # Check cross-page text consistency if texts provided
        if page_texts and len(page_texts) > 1:
            consistency_issues = self.text_analyzer.analyze_cross_page_consistency(page_texts)
            all_issues.extend(consistency_issues)

        # Aggregate score
        page_scores = [pr.score for pr in page_results]
        overall_score, category, recommendation = self.scorer.aggregate_document_quality(
            page_scores=page_scores,
            all_issues=all_issues,
        )

        summary = self._generate_summary(
            overall_score, category, recommendation, all_issues, page_count
        )
        is_processable = (
            recommendation != ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING
        )

        return DocumentQualityResult(
            document_id=document_id,
            file_path=str(path),
            file_type="PDF",
            page_count=page_count,
            overall_score=overall_score,
            category=category,
            recommendation=recommendation,
            is_processable=is_processable,
            issues=all_issues,
            pages=page_results,
            summary=summary,
        )

    def _analyze_image_file(
        self,
        image_path: Path,
        page_texts: list[str] | None = None,
        document_id: str | None = None,
    ) -> DocumentQualityResult:
        """Inspect and score a single image file (PNG, JPEG, TIFF, etc.)."""
        suffix = image_path.suffix.upper().lstrip(".")
        p_text = page_texts[0] if (page_texts and len(page_texts) > 0) else None

        try:
            page_result = self.page_analyzer.analyze_page(
                image_input=image_path,
                text_input=p_text,
                page_number=1,
            )
        except (ValueError, cv2.error, OSError) as ex:
            issue = QualityIssue(
                code="IMG_CORRUPT",
                title="Corrupted or Unreadable Image File",
                message=f"Failed to decode or parse image file: {ex}",
                dimension=QualityDimension.IMAGE,
                severity=QualitySeverity.CRITICAL,
                confidence=1.0,
                details={"error": str(ex)},
            )
            return DocumentQualityResult(
                document_id=document_id,
                file_path=str(image_path),
                file_type=suffix,
                page_count=0,
                overall_score=0.0,
                category=QualityCategory.UNUSABLE,
                recommendation=ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING,
                is_processable=False,
                issues=[issue],
                pages=[],
                summary=f"Image quality assessment failed: file is corrupted or unreadable ({ex}).",
            )

        overall_score = page_result.score
        category = page_result.category
        recommendation = page_result.recommendation

        summary = self._generate_summary(
            overall_score, category, recommendation, page_result.issues, 1
        )
        is_processable = (
            recommendation != ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING
        )

        return DocumentQualityResult(
            document_id=document_id,
            file_path=str(image_path),
            file_type=suffix,
            page_count=1,
            overall_score=overall_score,
            category=category,
            recommendation=recommendation,
            is_processable=is_processable,
            issues=page_result.issues,
            pages=[page_result],
            summary=summary,
        )

    def analyze_image(
        self,
        image_input: str | Path | Image.Image | np.ndarray,
        page_text: str | None = None,
        page_number: int = 1,
    ) -> PageQualityResult:
        """Directly analyze an in-memory image or image file path for a single page."""
        return self.page_analyzer.analyze_page(
            image_input=image_input,
            text_input=page_text,
            page_number=page_number,
        )

    def analyze_text(
        self,
        text: str | None,
        page_number: int = 1,
    ) -> tuple[TextQualityMetrics, list[QualityIssue]]:
        """Directly evaluate text quality for an extracted string."""
        return self.text_analyzer.analyze_page_text(text=text, page_number=page_number)

    def _generate_summary(
        self,
        score: float,
        category: QualityCategory,
        rec: ProcessingRecommendation,
        issues: list[QualityIssue],
        page_count: int,
    ) -> str:
        """Build human-readable summary of document quality and readiness."""
        p_str = f"{page_count} page{'s' if page_count != 1 else ''}"
        i_str = f"{len(issues)} detected issue{'s' if len(issues) != 1 else ''}"
        lines = [
            f"Quality Score: {score}/100 ({category.value}). Recommendation: {rec.value}.",
            f"Evaluated {p_str} with {i_str}.",
        ]

        criticals = [i for i in issues if i.severity == QualitySeverity.CRITICAL]
        highs = [i for i in issues if i.severity == QualitySeverity.HIGH]
        mediums = [i for i in issues if i.severity == QualitySeverity.MEDIUM]

        if criticals:
            crit_titles = "; ".join(c.title for c in criticals[:3])
            lines.append(f"Critical Blockers ({len(criticals)}): {crit_titles}")
        if highs:
            high_titles = "; ".join(h.title for h in highs[:3])
            lines.append(f"High-Severity Issues ({len(highs)}): {high_titles}")
        if mediums and not highs and not criticals:
            med_titles = "; ".join(m.title for m in mediums[:3])
            lines.append(f"Warnings ({len(mediums)}): {med_titles}")

        return " ".join(lines)
