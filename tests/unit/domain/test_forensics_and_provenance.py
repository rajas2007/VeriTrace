"""Unit tests for forensic and provenance value objects."""

import pytest

from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.enums.forensic import SignatureAssessmentLevel
from veritrace.domain.exceptions import ConfidenceRangeError, ValidationError
from veritrace.domain.value_objects.forensic import (
    SignatureAnalysisResult,
    SignatureEstimate,
    SignatureMeasurement,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.provenance import (
    ExtractedToken,
    ExtractionProvenance,
    ForensicEvidenceProvenance,
    ProcessingError,
    ProcessingWarning,
)


def _sample_bbox() -> NormalizedBoundingBox:
    return NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.4)


def test_signature_measurement_valid() -> None:
    """Verify SignatureMeasurement initialization."""
    meas = SignatureMeasurement(
        normalized_bbox=_sample_bbox(),
        apparent_stroke_width_mean_px=3.2,
        apparent_stroke_width_variance_px=0.45,
        stroke_pixel_coverage_pct=15.5,
        boundary_mask_discontinuity=0.12,
        is_clone_suspect=False,
    )
    assert meas.apparent_stroke_width_mean_px == 3.2
    assert meas.boundary_mask_discontinuity == 0.12


def test_signature_measurement_invalid_raises() -> None:
    """Verify validation boundaries on stroke measurements."""
    bbox = _sample_bbox()
    with pytest.raises(ValidationError):
        SignatureMeasurement(bbox, -1.0, 0.5, 10.0, 0.2)
    with pytest.raises(ValidationError):
        SignatureMeasurement(bbox, 2.0, -0.5, 10.0, 0.2)
    with pytest.raises(ValidationError):
        SignatureMeasurement(bbox, 2.0, 0.5, 105.0, 0.2)
    with pytest.raises(ConfidenceRangeError):
        SignatureMeasurement(bbox, 2.0, 0.5, 50.0, 1.5)


def test_signature_estimate_valid() -> None:
    """Verify SignatureEstimate initialization and boundaries."""
    est = SignatureEstimate(
        apparent_stroke_smoothness=0.88,
        metric_embedding_distance=0.15,
        comparison_reference_id="sigref_1234",
    )
    assert est.apparent_stroke_smoothness == 0.88
    assert est.metric_embedding_distance == 0.15

    with pytest.raises(ConfidenceRangeError):
        SignatureEstimate(apparent_stroke_smoothness=1.2)
    with pytest.raises(ValidationError):
        SignatureEstimate(apparent_stroke_smoothness=0.5, metric_embedding_distance=-0.1)


def test_signature_analysis_result() -> None:
    """Verify full forensic evaluation payload and boundaries."""
    meas = SignatureMeasurement(_sample_bbox(), 2.5, 0.3, 12.0, 0.05)
    est = SignatureEstimate(0.85)
    res = SignatureAnalysisResult(
        signature_id="sig_abc123",
        document_id="doc_xyz789",
        page_number=1,
        measurement=meas,
        estimate=est,
        assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
        uncertainty_score=0.35,
    )
    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.uncertainty_score == 0.35

    with pytest.raises(ValidationError):
        SignatureAnalysisResult(
            "", "doc_xyz789", 1, meas, est, SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE, 0.1
        )
    with pytest.raises(ValidationError):
        SignatureAnalysisResult(
            "sig_123",
            "doc_xyz789",
            0,
            meas,
            est,
            SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
            0.1,
        )
    with pytest.raises(ConfidenceRangeError):
        SignatureAnalysisResult(
            "sig_123",
            "doc_xyz789",
            1,
            meas,
            est,
            SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
            1.2,
        )


def test_extracted_token() -> None:
    """Verify ExtractedToken preserves raw Indic text and enforces confidence."""
    token = ExtractedToken(
        token_id="tok_123",
        text="भारत",
        raw_text="भारत",
        normalized_bbox=_sample_bbox(),
        confidence=0.97,
        page_number=1,
        source_type=ExtractionSourceType.DIGITAL_TEXT,
        language="hin",
        script="Deva",
    )
    assert token.raw_text == "भारत"
    assert token.script == "Deva"

    with pytest.raises(ValidationError):
        ExtractedToken("", "test", "test", _sample_bbox(), 0.9, 1, ExtractionSourceType.OCR)
    with pytest.raises(ConfidenceRangeError):
        ExtractedToken("tok_1", "test", "test", _sample_bbox(), 1.5, 1, ExtractionSourceType.OCR)
    with pytest.raises(ValidationError):
        ExtractedToken("tok_1", "test", "test", _sample_bbox(), 0.9, 0, ExtractionSourceType.OCR)


def test_processing_diagnostics() -> None:
    """Verify warning and error diagnostics."""
    warn = ProcessingWarning(
        warning_code="WARN_SKEW", message="Page tilted 2 degrees", page_number=1
    )
    assert warn.warning_code == "WARN_SKEW"
    with pytest.raises(ValidationError):
        ProcessingWarning("", "message")

    err = ProcessingError(error_code="ERR_PARSE", message="Corrupt font stream", is_fatal=True)
    assert err.is_fatal is True
    with pytest.raises(ValidationError):
        ProcessingError("ERR_1", "")


def test_extraction_provenance() -> None:
    """Verify ExtractionProvenance metadata and warning immutability."""
    warn = ProcessingWarning("WARN_LOW_DPI", "DPI below 200", 1)
    prov = ExtractionProvenance(
        document_id="doc_123",
        page_number=1,
        extractor_name="PyMuPDF",
        extractor_version="1.24.1",
        execution_time_ms=45.2,
        source_type=ExtractionSourceType.DIGITAL_TEXT,
        extraction_confidence=0.99,
        warnings=[warn],  # type: ignore[arg-type]
    )
    assert isinstance(prov.warnings, tuple)
    assert prov.warnings[0].warning_code == "WARN_LOW_DPI"

    with pytest.raises(ValidationError):
        ExtractionProvenance("", 1, "PyMuPDF", "1.0", 10.0, ExtractionSourceType.OCR)
    with pytest.raises(ValidationError):
        ExtractionProvenance("doc_1", 0, "PyMuPDF", "1.0", 10.0, ExtractionSourceType.OCR)
    with pytest.raises(ValidationError):
        ExtractionProvenance("doc_1", 1, "PyMuPDF", "1.0", -5.0, ExtractionSourceType.OCR)
    with pytest.raises(ConfidenceRangeError):
        ExtractionProvenance(
            "doc_1", 1, "PyMuPDF", "1.0", 5.0, ExtractionSourceType.OCR, extraction_confidence=1.5
        )


def test_forensic_evidence_provenance() -> None:
    """Verify ForensicEvidenceProvenance."""
    forensic_prov = ForensicEvidenceProvenance(
        algorithm_name="ELA",
        algorithm_version="1.4.0",
        input_image_dpi=300,
        quality_score=0.92,
        parameters={"scale": 15, "quality": 90},
    )
    assert forensic_prov.algorithm_name == "ELA"
    assert forensic_prov.input_image_dpi == 300
    assert forensic_prov.quality_score == 0.92

    with pytest.raises(ValidationError):
        ForensicEvidenceProvenance("", "1.0", 300, 0.9)
    with pytest.raises(ValidationError):
        ForensicEvidenceProvenance("ELA", "1.0", 0, 0.9)
    with pytest.raises(ConfidenceRangeError):
        ForensicEvidenceProvenance("ELA", "1.0", 300, 1.2)
