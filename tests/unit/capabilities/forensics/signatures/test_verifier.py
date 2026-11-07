"""Unit tests for SignatureVerifier forensic comparison and epistemic assessment."""

import hashlib
from datetime import timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from veritrace.capabilities.forensics.signatures.verifier import (
    SignatureForensicsProtocol,
    SignatureVerifier,
)
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    SignatureAssessmentLevel,
)
from veritrace.domain.exceptions.base import UnauthorizedActionError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import (
    ORG_PREFIX,
    SIGREF_PREFIX,
    SUBJ_PREFIX,
    generate_id,
    utc_now,
)


def create_sample_signature(variant: int = 1) -> np.ndarray:
    """Generate reproducible synthetic signature crop."""
    crop = np.full((120, 280, 3), 255, dtype=np.uint8)
    if variant == 1:
        # Standard signature A
        pts = [(30, 60), (70, 30), (100, 90), (140, 40), (180, 80), (220, 50), (260, 90)]
        for i in range(len(pts) - 1):
            cv2.line(crop, pts[i], pts[i + 1], (0, 0, 0), thickness=3)
        cv2.ellipse(crop, (150, 95), (100, 15), 0, 0, 180, (0, 0, 0), thickness=2)
    elif variant == 2:
        # Very similar signature A' with slight jitter
        pts = [(32, 62), (68, 32), (102, 88), (138, 42), (182, 78), (218, 52), (258, 88)]
        for i in range(len(pts) - 1):
            cv2.line(crop, pts[i], pts[i + 1], (0, 0, 0), thickness=3)
        cv2.ellipse(crop, (150, 94), (98, 16), 0, 0, 180, (0, 0, 0), thickness=2)
    else:
        # Completely different signature B (vertical loop strokes)
        pts = [(50, 20), (50, 100), (90, 20), (90, 100), (140, 20), (140, 100), (200, 60)]
        for i in range(len(pts) - 1):
            cv2.line(crop, pts[i], pts[i + 1], (0, 0, 0), thickness=5)
        cv2.circle(crop, (240, 60), 25, (0, 0, 0), thickness=3)
    return crop


def test_verifier_protocol_conformance():
    """Verify SignatureVerifier satisfies SignatureForensicsProtocol at runtime."""
    verifier = SignatureVerifier()
    assert isinstance(verifier, SignatureForensicsProtocol)


def test_compute_embedding_format():
    """Verify compute_embedding returns serialized float32 binary array of length 44 bytes."""
    crop = create_sample_signature(1)
    verifier = SignatureVerifier()
    emb = verifier.compute_embedding(crop)

    assert isinstance(emb, bytes)
    assert len(emb) == 11 * 4  # 11 float32 values = 44 bytes
    arr = np.frombuffer(emb, dtype=np.float32)
    assert len(arr) == 11
    # Check that values are finite
    assert np.all(np.isfinite(arr))


def test_verify_identical_signature():
    """Verify comparing identical signature crops produces SIMILARITY_WITH_REFERENCE."""
    crop1 = create_sample_signature(1)
    crop2 = create_sample_signature(1)
    verifier = SignatureVerifier()

    res = verifier.verify_against_reference(
        questioned_crop=crop1,
        reference_profile_or_crop=crop2,
        document_id="doc_test_001",
        page_number=1,
    )

    assert res.assessment == SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE
    assert res.estimate.metric_embedding_distance is not None
    assert res.estimate.metric_embedding_distance < 0.10
    assert res.uncertainty_score < 0.20
    # Invariant: note must mention legal neutrality
    assert "Machine similarity does NOT prove legal authorship" in res.notes


def test_verify_divergent_signature():
    """Verify comparing different signatures produces high distance anomaly or manipulation."""
    crop_a = create_sample_signature(1)
    crop_b = create_sample_signature(3)  # Completely different shape
    verifier = SignatureVerifier()

    res = verifier.verify_against_reference(
        questioned_crop=crop_a,
        reference_profile_or_crop=crop_b,
        document_id="doc_test_002",
        page_number=2,
    )

    assert res.assessment in (
        SignatureAssessmentLevel.VISUAL_ANOMALY_OBSERVED,
        SignatureAssessmentLevel.POSSIBLE_MANIPULATION_INDICATOR,
    )
    assert res.estimate.metric_embedding_distance is not None
    assert res.estimate.metric_embedding_distance > 0.35


def test_verify_insufficient_evidence():
    """Verify blank or tiny signature crops yield INSUFFICIENT_EVIDENCE."""
    blank = np.full((100, 200, 3), 255, dtype=np.uint8)
    verifier = SignatureVerifier()

    res = verifier.verify_against_reference(
        questioned_crop=blank,
        reference_profile_or_crop=create_sample_signature(1),
        document_id="doc_test_003",
        page_number=1,
    )

    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.uncertainty_score >= 0.85
    assert "Insufficient stroke density" in res.notes


def test_verify_boundary_clipping_discontinuity():
    """Verify signature crop with abrupt boundary yields POSSIBLE_MANIPULATION_INDICATOR."""
    crop = np.full((120, 280, 3), 255, dtype=np.uint8)
    # Heavy rectangular border cutting ink
    crop[0, 10:270] = 0
    crop[119, 10:270] = 0
    crop[5:115, 0] = 0
    crop[5:115, 279] = 0
    cv2.line(crop, (0, 60), (279, 60), (0, 0, 0), thickness=5)

    verifier = SignatureVerifier()
    res = verifier.verify_against_reference(
        questioned_crop=crop,
        reference_profile_or_crop=create_sample_signature(1),
        document_id="doc_test_004",
        page_number=1,
    )

    assert res.assessment == SignatureAssessmentLevel.POSSIBLE_MANIPULATION_INDICATOR
    assert res.measurement.boundary_mask_discontinuity > 0.40
    assert "boundary clipping discontinuity" in res.notes.lower()


def test_verify_enrolled_reference_profile(tmp_path: Path):
    """Verify verification against enrolled SignatureReferenceProfile entity."""
    crop_ref = create_sample_signature(1)
    ref_path = tmp_path / "ref_sig.png"
    cv2.imwrite(str(ref_path), crop_ref)

    verifier = SignatureVerifier()
    emb = verifier.compute_embedding(crop_ref)

    real_hash = hashlib.sha256(ref_path.read_bytes()).hexdigest()
    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash=real_hash,
        source_document_ref="doc_onboarding_scan",
        consent_mandate_ref="consent_form_2026_01",
        embedding_vector=emb,
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    questioned = create_sample_signature(2)  # Similar variant
    res = verifier.verify_against_reference(
        questioned_crop=questioned,
        reference_profile_or_crop=profile,
        document_id="doc_questioned_100",
        page_number=1,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.estimate.comparison_reference_id == profile.id
    assert res.assessment == SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE


def test_verify_unauthorized_role_raises_error(tmp_path: Path):
    """Verify unauthorized role attempting reference comparison raises UnauthorizedActionError."""
    ref_path = tmp_path / "ref_sig.png"
    cv2.imwrite(str(ref_path), create_sample_signature(1))

    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        source_document_ref="doc_onboarding",
        consent_mandate_ref="mandate_01",
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    verifier = SignatureVerifier()
    with pytest.raises(UnauthorizedActionError):
        verifier.verify_against_reference(
            questioned_crop=create_sample_signature(1),
            reference_profile_or_crop=profile,
            user_role="VIEWER",  # Insufficient role
        )


def test_verify_expired_reference_profile(tmp_path: Path):
    """Verify expired reference profile yields INSUFFICIENT_EVIDENCE under data retention rules."""
    ref_path = tmp_path / "ref_sig.png"
    cv2.imwrite(str(ref_path), create_sample_signature(1))

    now = utc_now()
    profile = SignatureReferenceProfile(
        id=generate_id(SIGREF_PREFIX),
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        source_document_ref="doc_old",
        consent_mandate_ref="mandate_old",
        enrollment_date=now - timedelta(days=400),
        retention_expiry_date=now - timedelta(days=35),  # Expired
    )

    verifier = SignatureVerifier()
    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="ADMIN",
    )

    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert "retention expiry date" in res.notes


def test_create_proposal_for_anomalous_signature():
    """Verify create_proposal constructs valid ForensicProposal with SIGNATURE_VERIFICATION."""
    crop_divergent = create_sample_signature(3)
    verifier = SignatureVerifier()

    res = verifier.verify_against_reference(
        questioned_crop=crop_divergent,
        reference_profile_or_crop=create_sample_signature(1),
        document_id="doc_check_99",
        page_number=3,
        normalized_bbox=NormalizedBoundingBox(ymin=0.7, xmin=0.6, ymax=0.85, xmax=0.9),
    )

    proposal = verifier.create_proposal(res, evidence_crop_path=Path("crop.png"))
    assert proposal is not None
    assert proposal.category == FindingCategory.SIGNATURE_VERIFICATION
    assert proposal.epistemic_tier in (
        EpistemicTier.DETECTED_INCONSISTENCY,
        EpistemicTier.SUSPECTED_MANIPULATION,
    )
    assert proposal.severity in (FindingSeverity.MEDIUM, FindingSeverity.HIGH)
    assert proposal.confidence > 0.0
    assert "signature_id" in proposal.measurements


def test_unmodified_reference_passes_integrity_verification(tmp_path: Path):
    """Verify unmodified enrolled reference passes SHA-256 integrity check."""
    crop_ref = create_sample_signature(1)
    ref_path = tmp_path / "valid_ref.png"
    cv2.imwrite(str(ref_path), crop_ref)

    file_bytes = ref_path.read_bytes()
    expected_hash = hashlib.sha256(file_bytes).hexdigest()

    verifier = SignatureVerifier()
    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash=expected_hash,
        source_document_ref="doc_ref_101",
        consent_mandate_ref="mandate_ref_101",
        embedding_vector=verifier.compute_embedding(crop_ref),
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.assessment == SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE
    assert res.estimate.metric_embedding_distance is not None
    assert res.estimate.metric_embedding_distance < 0.10
    assert res.uncertainty_score < 0.20


def test_modified_reference_image_bytes_fail_verification(tmp_path: Path):
    """Verify modifying reference bytes aborts comparison with INSUFFICIENT_EVIDENCE."""
    crop_ref = create_sample_signature(1)
    ref_path = tmp_path / "tampered_ref.png"
    cv2.imwrite(str(ref_path), crop_ref)

    file_bytes = ref_path.read_bytes()
    expected_hash = hashlib.sha256(file_bytes).hexdigest()

    verifier = SignatureVerifier()
    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash=expected_hash,
        source_document_ref="doc_ref_102",
        consent_mandate_ref="mandate_ref_102",
        embedding_vector=verifier.compute_embedding(crop_ref),
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    # Tamper with the physical file on disk by appending a byte
    with open(ref_path, "ab") as f:
        f.write(b"\x00")

    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.estimate.metric_embedding_distance is None
    assert res.uncertainty_score == 1.0
    assert "Chain-of-Custody Integrity Violation" in res.notes
    assert profile.sha256_hash == expected_hash  # Stored hash must never be overwritten


def test_replaced_reference_file_with_different_image_fails(tmp_path: Path):
    """Verify replacing enrolled reference with a different image fails integrity verification."""
    crop_ref = create_sample_signature(1)
    ref_path = tmp_path / "replaced_ref.png"
    cv2.imwrite(str(ref_path), crop_ref)

    expected_hash = hashlib.sha256(ref_path.read_bytes()).hexdigest()

    verifier = SignatureVerifier()
    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash=expected_hash,
        source_document_ref="doc_ref_103",
        consent_mandate_ref="mandate_ref_103",
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    # Replace with completely different image
    cv2.imwrite(str(ref_path), create_sample_signature(3))

    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.estimate.metric_embedding_distance is None
    assert "failed SHA-256 integrity verification" in res.notes


def test_missing_reference_file_remains_safely_inconclusive(tmp_path: Path):
    """Verify missing reference image file cleanly returns inconclusive without crashing."""
    missing_path = tmp_path / "deleted_specimen.png"
    fake_hash = "a" * 64

    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(missing_path),
        sha256_hash=fake_hash,
        source_document_ref="doc_ref_104",
        consent_mandate_ref="mandate_ref_104",
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    verifier = SignatureVerifier()
    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.estimate.metric_embedding_distance is None
    assert res.uncertainty_score == 1.0
    assert "file not found on disk" in res.notes


def test_failed_integrity_check_never_produces_similarity_result(tmp_path: Path):
    """Verify corrupted reference NEVER produces a similarity score even if embedding is stored."""
    crop_ref = create_sample_signature(1)
    ref_path = tmp_path / "corrupted_specimen.png"
    cv2.imwrite(str(ref_path), crop_ref)

    expected_hash = hashlib.sha256(ref_path.read_bytes()).hexdigest()

    verifier = SignatureVerifier()
    stored_embedding = verifier.compute_embedding(crop_ref)

    profile = SignatureReferenceProfile.create(
        subject_id=generate_id(SUBJ_PREFIX),
        organization_id=generate_id(ORG_PREFIX),
        crop_image_path=str(ref_path),
        sha256_hash=expected_hash,
        source_document_ref="doc_ref_105",
        consent_mandate_ref="mandate_ref_105",
        embedding_vector=stored_embedding,
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    # Corrupt the image on disk
    ref_path.write_bytes(b"corrupted raw data")

    res = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=profile,
        user_role="FORENSIC_INVESTIGATOR",
    )

    assert res.assessment != SignatureAssessmentLevel.SIMILARITY_WITH_REFERENCE
    assert res.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res.estimate.metric_embedding_distance is None
    assert res.uncertainty_score == 1.0

    # Also verify expected_reference_hash check directly on path input
    res_direct = verifier.verify_against_reference(
        questioned_crop=create_sample_signature(1),
        reference_profile_or_crop=ref_path,
        expected_reference_hash=expected_hash,
    )
    assert res_direct.assessment == SignatureAssessmentLevel.INSUFFICIENT_EVIDENCE
    assert res_direct.estimate.metric_embedding_distance is None
