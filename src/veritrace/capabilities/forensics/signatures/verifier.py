"""Signature verification engine comparing questioned signatures against enrolled references."""

from __future__ import annotations

import hashlib
import logging
import math
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import cv2
import numpy as np

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.capabilities.forensics.signatures.crop_quality import SignatureCropQualityAssessor
from veritrace.capabilities.forensics.signatures.detector import SignatureDetector
from veritrace.capabilities.forensics.signatures.onnx_engine import SiameseOnnxSignatureEngine
from veritrace.capabilities.forensics.signatures.stroke_analyzer import SignatureStrokeAnalyzer
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    SignatureAssessmentLevel,
)
from veritrace.domain.exceptions.base import UnauthorizedActionError, ValidationError
from veritrace.domain.value_objects.forensic import (
    SignatureAnalysisResult,
    SignatureEstimate,
    SignatureMeasurement,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import generate_id

logger = logging.getLogger("veritrace.capabilities.forensics.signatures.verifier")


@runtime_checkable
class SignatureForensicsProtocol(Protocol):
    """Protocol for signature detection, stroke analysis, and reference verification."""

    def detect_signatures(
        self,
        image_or_path: np.ndarray | Path | bytes,
    ) -> list[NormalizedBoundingBox]:
        """Detect candidate handwritten signature regions on a document canvas."""
        ...

    def analyze_stroke(
        self,
        crop_image_or_path: np.ndarray | Path | bytes,
        normalized_bbox: NormalizedBoundingBox,
    ) -> tuple[SignatureMeasurement, SignatureEstimate]:
        """Compute stroke measurements and optical estimates for a cropped signature."""
        ...

    def verify_against_reference(
        self,
        questioned_crop: np.ndarray | Path | bytes,
        reference_profile_or_crop: SignatureReferenceProfile | np.ndarray | Path | bytes,
        document_id: str = "doc_questioned",
        page_number: int = 1,
        normalized_bbox: NormalizedBoundingBox | None = None,
        user_role: str | None = None,
        expected_reference_hash: str | None = None,
    ) -> SignatureAnalysisResult:
        """Compare a questioned signature crop against an enrolled reference profile or image."""
        ...


class SignatureVerifier:
    """Forensic signature comparison engine evaluating optical stroke geometry,

    Hu moment shape descriptors, and enrolled chain-of-custody reference samples.
    Adheres strictly to the Six-Level Epistemic Assessment Scale.

    NOTE: Hu moment distances, stroke thresholds, and 6-level epistemic assessments
    are VeriTrace application-defined optical heuristics. They are NOT certified forensic
    standards and do NOT establish legal signature authenticity or authorship.
    Qualified human document examination remains strictly necessary.
    """

    def __init__(
        self,
        detector: SignatureDetector | None = None,
        stroke_analyzer: SignatureStrokeAnalyzer | None = None,
        quality_assessor: SignatureCropQualityAssessor | None = None,
        onnx_engine: SiameseOnnxSignatureEngine | None = None,
        distance_threshold_match: float = 0.25,
        distance_threshold_anomaly: float = 0.55,
    ) -> None:
        self._detector = detector or SignatureDetector()
        self._stroke_analyzer = stroke_analyzer or SignatureStrokeAnalyzer()
        self._quality_assessor = quality_assessor or SignatureCropQualityAssessor()
        self._onnx_engine = onnx_engine or SiameseOnnxSignatureEngine()
        self._distance_threshold_match = distance_threshold_match
        self._distance_threshold_anomaly = distance_threshold_anomaly

    def detect_signatures(
        self, image_or_path: np.ndarray | Path | bytes
    ) -> list[NormalizedBoundingBox]:
        """Delegate signature region localization to SignatureDetector."""
        return self._detector.detect_candidate_regions(image_or_path)

    def analyze_stroke(
        self,
        crop_image_or_path: np.ndarray | Path | bytes,
        normalized_bbox: NormalizedBoundingBox,
    ) -> tuple[SignatureMeasurement, SignatureEstimate]:
        """Delegate stroke measurements to SignatureStrokeAnalyzer."""
        return self._stroke_analyzer.analyze_crop(crop_image_or_path, normalized_bbox)

    def compute_embedding(self, crop_image_or_path: np.ndarray | Path | bytes) -> bytes:
        """Compute compact, normalized 11-dimensional float32 feature vector

        suitable for enrollment in SignatureReferenceProfile.embedding_vector.
        """
        features = self._extract_feature_vector(crop_image_or_path)
        return features.astype(np.float32).tobytes()

    def verify_against_reference(
        self,
        questioned_crop: np.ndarray | Path | bytes,
        reference_profile_or_crop: SignatureReferenceProfile | np.ndarray | Path | bytes,
        document_id: str = "doc_questioned",
        page_number: int = 1,
        normalized_bbox: NormalizedBoundingBox | None = None,
        user_role: str | None = None,
        expected_reference_hash: str | None = None,
    ) -> SignatureAnalysisResult:
        """Compare a questioned signature crop against an enrolled reference profile or image.

        Args:
            questioned_crop: Questioned signature image crop.
            reference_profile_or_crop: Enrolled SignatureReferenceProfile or image array/path/bytes.
            document_id: Source document identifier.
            page_number: 1-based page number where signature was detected.
            normalized_bbox: Spatial position on page.
            user_role: Optional user RBAC role string to enforce chain-of-custody permissions.

        Returns:
            SignatureAnalysisResult domain value object.
        """
        bbox = normalized_bbox or NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0)
        sig_id = generate_id("sig_")

        # 1. RBAC chain-of-custody verification if reference profile is provided
        ref_id: str | None = None
        if isinstance(reference_profile_or_crop, SignatureReferenceProfile):
            ref_id = reference_profile_or_crop.id
            if user_role is not None and not reference_profile_or_crop.is_authorized_for_role(
                user_role
            ):
                req_role = reference_profile_or_crop.access_role_required
                raise UnauthorizedActionError(
                    f"User role '{user_role}' is not authorized to access reference profile "
                    f"'{ref_id}' (requires '{req_role}')"
                )

            # Check retention expiration
            if reference_profile_or_crop.is_expired():
                meas, est = self.analyze_stroke(questioned_crop, bbox)
                return SignatureAnalysisResult(
                    signature_id=sig_id,
                    document_id=document_id,
                    page_number=page_number,
                    measurement=meas,
                    estimate=SignatureEstimate(
                        apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                        metric_embedding_distance=None,
                        comparison_reference_id=ref_id,
                    ),
                    assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                    uncertainty_score=0.95,
                    notes=(
                        f"Enrolled reference profile {ref_id} has passed its mandatory retention "
                        f"expiry date ({reference_profile_or_crop.retention_expiry_date}). "
                        "Forensic comparison disallowed under data governance policy."
                    ),
                )

            # Check reference image file integrity against enrolled sha256_hash
            ref_path = Path(reference_profile_or_crop.crop_image_path)
            if not ref_path.is_file():
                meas, est = self.analyze_stroke(questioned_crop, bbox)
                return SignatureAnalysisResult(
                    signature_id=sig_id,
                    document_id=document_id,
                    page_number=page_number,
                    measurement=meas,
                    estimate=SignatureEstimate(
                        apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                        metric_embedding_distance=None,
                        comparison_reference_id=ref_id,
                    ),
                    assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                    uncertainty_score=1.0,
                    notes=(
                        f"Enrolled reference image file not found on disk at '{ref_path}'. "
                        "Forensic comparison aborted under chain-of-custody integrity policy."
                    ),
                )

            try:
                ref_bytes = ref_path.read_bytes()
                computed_hash = hashlib.sha256(ref_bytes).hexdigest()
            except Exception as e:
                meas, est = self.analyze_stroke(questioned_crop, bbox)
                return SignatureAnalysisResult(
                    signature_id=sig_id,
                    document_id=document_id,
                    page_number=page_number,
                    measurement=meas,
                    estimate=SignatureEstimate(
                        apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                        metric_embedding_distance=None,
                        comparison_reference_id=ref_id,
                    ),
                    assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                    uncertainty_score=1.0,
                    notes=f"Failed to read enrolled reference file '{ref_path}': {e}",
                )

            if computed_hash != reference_profile_or_crop.sha256_hash:
                meas, est = self.analyze_stroke(questioned_crop, bbox)
                return SignatureAnalysisResult(
                    signature_id=sig_id,
                    document_id=document_id,
                    page_number=page_number,
                    measurement=meas,
                    estimate=SignatureEstimate(
                        apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                        metric_embedding_distance=None,
                        comparison_reference_id=ref_id,
                    ),
                    assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                    uncertainty_score=1.0,
                    notes=(
                        f"Chain-of-Custody Integrity Violation: Reference signature crop for "
                        f"profile '{ref_id}' failed SHA-256 integrity verification "
                        f"(expected {reference_profile_or_crop.sha256_hash[:16]}..., "
                        f"actual {computed_hash[:16]}...). "
                        "Automated comparison aborted to prevent corrupted evidence "
                        "from entering the dossier."
                    ),
                )
        elif expected_reference_hash is not None:
            computed_ref_hash: str | None = None
            if isinstance(reference_profile_or_crop, (Path, str)):
                r_p = Path(reference_profile_or_crop)
                if not r_p.is_file():
                    meas, est = self.analyze_stroke(questioned_crop, bbox)
                    return SignatureAnalysisResult(
                        signature_id=sig_id,
                        document_id=document_id,
                        page_number=page_number,
                        measurement=meas,
                        estimate=SignatureEstimate(
                            apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                            metric_embedding_distance=None,
                        ),
                        assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                        uncertainty_score=1.0,
                        notes=f"Reference signature image file not found on disk at '{r_p}'.",
                    )
                try:
                    computed_ref_hash = hashlib.sha256(r_p.read_bytes()).hexdigest()
                except Exception as e:
                    meas, est = self.analyze_stroke(questioned_crop, bbox)
                    return SignatureAnalysisResult(
                        signature_id=sig_id,
                        document_id=document_id,
                        page_number=page_number,
                        measurement=meas,
                        estimate=SignatureEstimate(
                            apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                            metric_embedding_distance=None,
                        ),
                        assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                        uncertainty_score=1.0,
                        notes=f"Failed to read reference file: {e}",
                    )
            elif isinstance(reference_profile_or_crop, bytes):
                computed_ref_hash = hashlib.sha256(reference_profile_or_crop).hexdigest()

            if computed_ref_hash is not None and computed_ref_hash != expected_reference_hash:
                meas, est = self.analyze_stroke(questioned_crop, bbox)
                return SignatureAnalysisResult(
                    signature_id=sig_id,
                    document_id=document_id,
                    page_number=page_number,
                    measurement=meas,
                    estimate=SignatureEstimate(
                        apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                        metric_embedding_distance=None,
                    ),
                    assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                    uncertainty_score=1.0,
                    notes=(
                        f"Chain-of-Custody Integrity Violation: Reference signature crop "
                        f"failed SHA-256 verification (expected {expected_reference_hash[:16]}..., "
                        f"actual {computed_ref_hash[:16]}...). Comparison aborted."
                    ),
                )

        # 1.5 Quality Assessment Gate: Verify resolution, blur, contrast, and boundary completeness
        quality = self._quality_assessor.evaluate(questioned_crop)
        if not quality.is_adequate:
            return SignatureAnalysisResult(
                signature_id=sig_id,
                document_id=document_id,
                page_number=page_number,
                measurement=SignatureMeasurement(
                    normalized_bbox=bbox,
                    apparent_stroke_width_mean_px=0.0,
                    apparent_stroke_width_variance_px=0.0,
                    stroke_pixel_coverage_pct=quality.stroke_coverage_pct,
                    boundary_mask_discontinuity=quality.boundary_discontinuity,
                ),
                estimate=SignatureEstimate(
                    apparent_stroke_smoothness=0.0,
                    metric_embedding_distance=None,
                    comparison_reference_id=ref_id,
                ),
                assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                uncertainty_score=0.95,
                notes=(
                    f"Signature crop quality limitation: {'; '.join(quality.reasons)}. "
                    "Automated optical comparison aborted under forensic reliability policy. "
                    "Epistemic rating: INSUFFICIENT_EVIDENCE. Human review required."
                ),
            )

        # 2. Extract measurements and optical estimate
        try:
            meas, est = self.analyze_stroke(questioned_crop, bbox)
        except Exception as e:
            return SignatureAnalysisResult(
                signature_id=sig_id,
                document_id=document_id,
                page_number=page_number,
                measurement=SignatureMeasurement(
                    normalized_bbox=bbox,
                    apparent_stroke_width_mean_px=0.0,
                    apparent_stroke_width_variance_px=0.0,
                    stroke_pixel_coverage_pct=0.0,
                    boundary_mask_discontinuity=0.0,
                ),
                estimate=SignatureEstimate(apparent_stroke_smoothness=0.0),
                assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                uncertainty_score=1.0,
                notes=f"Failed to process signature crop: {e}",
            )

        # 3. Check for insufficient physical evidence (e.g. blank patch or tiny fragment)
        if meas.stroke_pixel_coverage_pct < 0.20 or meas.apparent_stroke_width_mean_px < 0.5:
            return SignatureAnalysisResult(
                signature_id=sig_id,
                document_id=document_id,
                page_number=page_number,
                measurement=meas,
                estimate=SignatureEstimate(
                    apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                    metric_embedding_distance=None,
                    comparison_reference_id=ref_id,
                ),
                assessment=SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE,
                uncertainty_score=0.90,
                notes=(
                    "Insufficient stroke density or resolution in cropped signature candidate. "
                    "Cannot establish meaningful morphological comparison."
                ),
            )

        # 4. Check for boundary clipping discontinuity (cut-and-paste artifact)
        if meas.boundary_mask_discontinuity > 0.45:
            disc = meas.boundary_mask_discontinuity
            return SignatureAnalysisResult(
                signature_id=sig_id,
                document_id=document_id,
                page_number=page_number,
                measurement=meas,
                estimate=SignatureEstimate(
                    apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                    metric_embedding_distance=None,
                    comparison_reference_id=ref_id,
                ),
                assessment=SignatureAssessmentLevel.POSSIBLE_MANIPULATION_INDICATOR,
                uncertainty_score=0.25,
                notes=(
                    f"Sharp boundary clipping discontinuity detected ({disc:.2f}). "
                    "Ink strokes terminate abruptly along the rectangular bounding perimeter, "
                    "indicating probable digital cropping or paste artifact."
                ),
            )

        # 5. Compute metric distance to reference
        dist, orb_sim = self._compute_distance(questioned_crop, reference_profile_or_crop)

        # 6. Epistemic Assessment Scale Mapping
        if dist <= self._distance_threshold_match:
            assessment = SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE
            uncertainty = max(0.10, dist * 0.5)
            notes = (
                f"Close visual correspondence observed against reference (dist {dist:.3f}). "
                "SCIENTIFIC INVARIANT: Machine similarity does NOT prove legal authorship; "
                "examiner verification is required."
            )
        elif dist <= self._distance_threshold_anomaly:
            assessment = SignatureAssessmentLevel.VISUAL_ANOMALY_OBSERVED
            uncertainty = 0.40 + (dist - self._distance_threshold_match)
            notes = (
                f"Moderate optical divergence from reference (metric distance {dist:.3f}). "
                "SCIENTIFIC INVARIANT: Visual difference does NOT prove forgery; "
                "intra-writer variability and writing conditions must be considered."
            )
        else:
            assessment = SignatureAssessmentLevel.POSSIBLE_MANIPULATION_INDICATOR
            uncertainty = min(0.85, 0.50 + (dist * 0.35))
            notes = (
                f"Significant optical divergence from reference profile (dist {dist:.3f}). "
                "Substantial morphological and stroke disparity detected. "
                "Referred for comprehensive forensic document examination."
            )

        return SignatureAnalysisResult(
            signature_id=sig_id,
            document_id=document_id,
            page_number=page_number,
            measurement=meas,
            estimate=SignatureEstimate(
                apparent_stroke_smoothness=est.apparent_stroke_smoothness,
                metric_embedding_distance=round(dist, 4),
                comparison_reference_id=ref_id,
            ),
            assessment=assessment,
            uncertainty_score=round(min(1.0, max(0.0, uncertainty)), 4),
            notes=notes,
        )

    def create_proposal(
        self,
        result: SignatureAnalysisResult,
        evidence_crop_path: Path | None = None,
    ) -> ForensicProposal | None:
        """Create a candidate ForensicProposal for findings requiring investigator review."""
        if result.assessment == SignatureAssessmentLevel.POSSIBLE_MANIPULATION_INDICATOR:
            return ForensicProposal(
                category=FindingCategory.SIGNATURE_VERIFICATION,
                epistemic_tier=EpistemicTier.SUSPECTED_MANIPULATION,
                severity=FindingSeverity.HIGH,
                title="Signature Manipulation Indicator Detected",
                narrative_explanation=(
                    f"Signature '{result.signature_id}' on page {result.page_number} exhibited "
                    f"indicators of manipulation: {result.notes}"
                ),
                confidence=round(1.0 - result.uncertainty_score, 4),
                normalized_bbox=result.measurement.normalized_bbox,
                evidence_crop_path=evidence_crop_path,
                measurements={
                    "signature_id": result.signature_id,
                    "metric_distance": (
                        result.estimate.metric_embedding_distance
                        if result.estimate.metric_embedding_distance is not None
                        else -1.0
                    ),
                    "boundary_discontinuity": result.measurement.boundary_mask_discontinuity,
                    "stroke_width_mean": result.measurement.apparent_stroke_width_mean_px,
                    "comparison_reference_id": (
                        result.estimate.comparison_reference_id
                        if result.estimate.comparison_reference_id
                        else "none"
                    ),
                },
            )

        if result.assessment == SignatureAssessmentLevel.VISUAL_ANOMALY_OBSERVED:
            return ForensicProposal(
                category=FindingCategory.SIGNATURE_VERIFICATION,
                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                severity=FindingSeverity.MEDIUM,
                title="Signature Visual Divergence Observed",
                narrative_explanation=(
                    f"Signature '{result.signature_id}' on page {result.page_number} showed "
                    f"optical deviation from enrolled reference: {result.notes}"
                ),
                confidence=round(1.0 - result.uncertainty_score, 4),
                normalized_bbox=result.measurement.normalized_bbox,
                evidence_crop_path=evidence_crop_path,
                measurements={
                    "signature_id": result.signature_id,
                    "metric_distance": (
                        result.estimate.metric_embedding_distance
                        if result.estimate.metric_embedding_distance is not None
                        else -1.0
                    ),
                    "boundary_discontinuity": result.measurement.boundary_mask_discontinuity,
                    "comparison_reference_id": (
                        result.estimate.comparison_reference_id
                        if result.estimate.comparison_reference_id
                        else "none"
                    ),
                },
            )

        return None

    def _compute_distance(
        self,
        questioned_crop: np.ndarray | Path | bytes,
        reference_profile_or_crop: SignatureReferenceProfile | np.ndarray | Path | bytes,
    ) -> tuple[float, float]:
        """Compute normalized metric embedding distance in [0.0, 1.0]."""
        # If neural ONNX Siamese model is configured and available, use deep metric distance
        if self._onnx_engine is not None and self._onnx_engine.is_available():
            try:
                ref_input: Any = reference_profile_or_crop
                if isinstance(reference_profile_or_crop, SignatureReferenceProfile):
                    ref_input = Path(reference_profile_or_crop.crop_image_path)
                neural_dist = self._onnx_engine.compute_metric_distance(questioned_crop, ref_input)
                orb_sim = self._match_orb(questioned_crop, ref_input)
                return neural_dist, orb_sim
            except Exception as exc:
                logger.warning(
                    "Neural ONNX verification failed (%s); falling back to classical heuristics.",
                    exc,
                )

        q_features = self._extract_feature_vector(questioned_crop)

        ref_features: np.ndarray
        orb_similarity: float = 0.0

        if isinstance(reference_profile_or_crop, SignatureReferenceProfile):
            if reference_profile_or_crop.embedding_vector is not None:
                ref_features = np.frombuffer(
                    reference_profile_or_crop.embedding_vector, dtype=np.float32
                )
            else:
                ref_path = Path(reference_profile_or_crop.crop_image_path)
                ref_features = self._extract_feature_vector(ref_path)
                orb_similarity = self._match_orb(questioned_crop, ref_path)
        elif isinstance(reference_profile_or_crop, (np.ndarray, Path, bytes)):
            ref_features = self._extract_feature_vector(reference_profile_or_crop)
            orb_similarity = self._match_orb(questioned_crop, reference_profile_or_crop)
        else:
            raise ValidationError(f"Unsupported reference type: {type(reference_profile_or_crop)}")

        if len(q_features) != len(ref_features):
            return 1.0, 0.0

        # 1. Hu moments difference in inverse log space (scale invariant)
        hu_diffs = []
        for i in range(7):
            val_q = float(q_features[i])
            val_r = float(ref_features[i])
            inv_q = 1.0 / val_q if abs(val_q) > 0.01 else 0.0
            inv_r = 1.0 / val_r if abs(val_r) > 0.01 else 0.0
            hu_diffs.append(abs(inv_q - inv_r))
        d_hu = min(1.0, float(np.sum(hu_diffs)) * 5.0)

        # 2. Topological metrics (aspect ratio, coverage, stroke width mean and variance)
        d_aspect = abs(q_features[7] - ref_features[7]) / max(
            float(q_features[7]), float(ref_features[7]), 1.0
        )
        d_cov = abs(q_features[8] - ref_features[8]) / max(
            float(q_features[8]), float(ref_features[8]), 0.01
        )
        d_width = abs(q_features[9] - ref_features[9]) / max(
            float(q_features[9]), float(ref_features[9]), 1.0
        )
        d_var = abs(q_features[10] - ref_features[10]) / max(
            float(q_features[10]), float(ref_features[10]), 0.1
        )
        d_topo = min(1.0, (float(d_aspect) + float(d_cov) + float(d_width) + float(d_var)) / 4.0)

        # Base feature distance
        base_dist = 0.50 * d_hu + 0.50 * d_topo

        metric_distance = float(min(1.0, max(0.0, base_dist)))
        return metric_distance, orb_similarity

    def _extract_feature_vector(self, image_or_path: np.ndarray | Path | bytes) -> np.ndarray:
        """Extract 11-dimensional float32 feature vector (7 Hu moments + 4 topological features)."""
        img = self._load_image(image_or_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        h, w = gray.shape[:2]
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Hu moments on binary stroke silhouette
        moments = cv2.moments(binary)
        hu = cv2.HuMoments(moments).flatten()
        log_hu = np.zeros(7, dtype=np.float32)
        for i in range(7):
            val = float(hu[i])
            if abs(val) > 1e-12:
                log_hu[i] = -float(np.sign(val)) * math.log10(abs(val))
            else:
                log_hu[i] = 0.0

        # Topological attributes
        aspect_ratio = float(w) / max(1.0, float(h))
        coverage = float(np.count_nonzero(binary)) / max(1.0, float(h * w))

        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        radii = dist[binary > 0]
        if len(radii) > 0:
            stroke_mean = float(np.mean(radii * 2.0))
            stroke_var = float(np.var(radii * 2.0))
        else:
            stroke_mean = 0.0
            stroke_var = 0.0

        features = np.concatenate(
            [
                log_hu,
                np.array([aspect_ratio, coverage, stroke_mean, stroke_var], dtype=np.float32),
            ]
        )
        return features.astype(np.float32)

    def _match_orb(
        self,
        img1_input: np.ndarray | Path | bytes,
        img2_input: np.ndarray | Path | bytes,
    ) -> float:
        """Calculate keypoint similarity in [0.0, 1.0] using ORB descriptors."""
        try:
            img1 = self._load_image(img1_input)
            img2 = self._load_image(img2_input)

            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2

            orb = cv2.ORB_create(nfeatures=500)  # type: ignore[attr-defined]
            kp1, des1 = orb.detectAndCompute(gray1, None)
            kp2, des2 = orb.detectAndCompute(gray2, None)

            if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
                return 0.0

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            if not matches:
                return 0.0

            # Filter good matches with Hamming distance < 50
            good_matches = [m for m in matches if m.distance < 50]
            similarity = min(1.0, len(good_matches) / 20.0)
            return float(similarity)
        except Exception:
            return 0.0

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> np.ndarray:
        """Decode input into OpenCV BGR ndarray."""
        if isinstance(image_or_path, np.ndarray):
            return image_or_path

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise ValidationError(f"Image not found: {image_or_path}")
            img = cv2.imread(str(image_or_path))
            if img is None:
                raise ValidationError(f"Failed to decode image from path: {image_or_path}")
            return img

        if isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValidationError("Failed to decode image from bytes")
            return img

        raise TypeError(f"Unsupported image type: {type(image_or_path)}")
