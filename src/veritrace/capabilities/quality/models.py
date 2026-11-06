"""Document Quality Assessment Data Models.

Defines Pydantic v2 schemas and enumerations for quality scoring,
issue tracking, per-page analysis, and document-level aggregation.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class QualityDimension(StrEnum):
    """The analytical dimension where a quality issue was observed."""

    IMAGE = "IMAGE"
    PDF_STRUCTURE = "PDF_STRUCTURE"
    TEXT = "TEXT"


class QualitySeverity(StrEnum):
    """Severity impact of a quality issue."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QualityCategory(StrEnum):
    """Deterministic quality scoring bands."""

    EXCELLENT = "EXCELLENT"  # 90-100
    GOOD = "GOOD"  # 75-89
    ACCEPTABLE = "ACCEPTABLE"  # 50-74
    POOR = "POOR"  # 25-49
    UNUSABLE = "UNUSABLE"  # 0-24


class ProcessingRecommendation(StrEnum):
    """Engine recommendation for automated downstream processing."""

    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    UNSUITABLE_FOR_AUTOMATED_PROCESSING = "UNSUITABLE_FOR_AUTOMATED_PROCESSING"


class QualityIssue(BaseModel):
    """Specific quality defect or anomaly detected during inspection."""

    code: str = Field(..., description="Unique issue code, e.g. 'IMG_BLUR', 'PDF_ENCRYPTED'")
    title: str = Field(..., description="Short human-readable title of the issue")
    message: str = Field(..., description="Detailed explanation of the issue and its implications")
    dimension: QualityDimension = Field(..., description="Dimension: IMAGE, PDF_STRUCTURE, or TEXT")
    severity: QualitySeverity = Field(..., description="Severity level")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence of detector reliability in [0.0, 1.0]",
    )
    measured_value: float | None = Field(
        default=None,
        description="Empirical value measured by detector (if scalar)",
    )
    threshold: float | None = Field(
        default=None,
        description="Threshold against which measurement was evaluated",
    )
    page_number: int | None = Field(
        default=None,
        description="1-based page number where issue occurred, or None if document-wide",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional forensic or technical context for the issue",
    )


class ImageQualityMetrics(BaseModel):
    """Raw explainable computer vision measurements for a single page image."""

    width_pixels: int = Field(default=0, ge=0)
    height_pixels: int = Field(default=0, ge=0)
    total_pixels: int = Field(default=0, ge=0)
    estimated_dpi: float | None = Field(default=None, ge=0.0)
    laplacian_variance: float = Field(
        default=0.0, ge=0.0, description="Variance of Laplacian focus metric"
    )
    edge_energy: float = Field(default=0.0, ge=0.0, description="Sobel/gradient edge energy")
    michelson_contrast: float = Field(default=0.0, ge=0.0, le=1.0)
    rms_contrast: float = Field(
        default=0.0, ge=0.0, description="Standard deviation of pixel intensities"
    )
    noise_sigma: float = Field(
        default=0.0, ge=0.0, description="Estimated high-frequency noise standard deviation"
    )
    brightness_mean: float = Field(default=0.0, ge=0.0, le=255.0)
    brightness_std: float = Field(default=0.0, ge=0.0)
    illumination_uniformity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Ratio of min block luminance to max block luminance (1.0 = perfectly uniform)",
    )
    skew_angle_deg: float = Field(default=0.0, description="Estimated skew angle in degrees")
    detected_orientation_deg: int = Field(
        default=0, description="Detected rotation: 0, 90, 180, or 270 degrees"
    )
    boundary_content_touches: int = Field(
        default=0, ge=0, description="Number of content touches near page margins"
    )
    is_blank: bool = Field(
        default=False, description="True if page image contains virtually no content"
    )


class PdfStructuralMetrics(BaseModel):
    """Structural properties and integrity metrics of a PDF page."""

    page_number: int = Field(..., ge=1)
    width_points: float = Field(default=0.0, ge=0.0)
    height_points: float = Field(default=0.0, ge=0.0)
    aspect_ratio: float = Field(default=1.0, ge=0.0)
    rotation_degrees: int = Field(default=0)
    has_text_layer: bool = Field(default=False)
    image_count: int = Field(default=0, ge=0)
    is_blank: bool = Field(default=False)
    is_unusual_dimensions: bool = Field(default=False)


class TextQualityMetrics(BaseModel):
    """Metrics assessing quality and integrity of extracted text."""

    char_count: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    line_count: int = Field(default=0, ge=0)
    replacement_char_count: int = Field(default=0, ge=0)
    symbol_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    whitespace_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    fragmented_word_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    text_density_cpi: float | None = Field(
        default=None,
        description="Estimated characters per square inch",
    )


class PageQualityResult(BaseModel):
    """Complete quality assessment for a single page."""

    page_number: int = Field(..., ge=1)
    score: float = Field(default=100.0, ge=0.0, le=100.0)
    category: QualityCategory = Field(default=QualityCategory.EXCELLENT)
    recommendation: ProcessingRecommendation = Field(default=ProcessingRecommendation.READY)
    issues: list[QualityIssue] = Field(default_factory=list)
    image_metrics: ImageQualityMetrics | None = Field(default=None)
    pdf_metrics: PdfStructuralMetrics | None = Field(default=None)
    text_metrics: TextQualityMetrics | None = Field(default=None)
    penalties: dict[str, float] = Field(
        default_factory=dict, description="Deductions per issue code"
    )


class DocumentQualityResult(BaseModel):
    """Aggregate document-level quality assessment."""

    document_id: str | None = Field(
        default=None, description="Optional identifier for the document"
    )
    file_path: str | None = Field(default=None, description="Path to evaluated document")
    file_type: str = Field(
        default="UNKNOWN", description="Detected format: PDF, PNG, JPEG, TIFF, etc."
    )
    page_count: int = Field(default=0, ge=0)
    overall_score: float = Field(default=100.0, ge=0.0, le=100.0)
    category: QualityCategory = Field(default=QualityCategory.EXCELLENT)
    recommendation: ProcessingRecommendation = Field(default=ProcessingRecommendation.READY)
    is_processable: bool = Field(
        default=True, description="Whether document is suitable for automated pipeline"
    )
    issues: list[QualityIssue] = Field(
        default_factory=list, description="All document-level and page-level issues"
    )
    pages: list[PageQualityResult] = Field(default_factory=list, description="Per-page breakdown")
    summary: str = Field(default="", description="Executive summary of document quality")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or timing measurements"
    )

    @model_validator(mode="after")
    def sync_processability(self) -> "DocumentQualityResult":
        """Ensure is_processable aligns with recommendation."""
        if self.recommendation == ProcessingRecommendation.UNSUITABLE_FOR_AUTOMATED_PROCESSING:
            self.is_processable = False
        return self
