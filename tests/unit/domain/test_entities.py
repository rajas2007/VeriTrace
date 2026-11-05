"""Unit tests covering all domain entities and their invariant constraints."""

from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.cross_document_relation import CrossDocumentRelation
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.entity import Entity
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.organization import Organization
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.enums.audit import ActorType, AuditEventType, EntityType, IndustrySector
from veritrace.domain.enums.document import (
    DocumentStatus,
    ExtractionSourceType,
    QualityStatus,
    TextLayerType,
)
from veritrace.domain.enums.forensic import RelationType, ReviewDecisionType
from veritrace.domain.exceptions import (
    ConfidenceRangeError,
    InvalidIdentifierError,
    RelationshipConstraintError,
    UnsupportedFormatError,
    ValidationError,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox, PageDimensions
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    DOS_PREFIX,
    ENT_PREFIX,
    EVD_PREFIX,
    FLD_PREFIX,
    FND_PREFIX,
    INV_PREFIX,
    ORG_PREFIX,
    PAGE_PREFIX,
    REL_PREFIX,
    REV_PREFIX,
    SIGREF_PREFIX,
    SUBJ_PREFIX,
    generate_id,
    utc_now,
)
from veritrace.domain.value_objects.multilingual import (
    LanguageDetectionProfile,
)

SAMPLE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _sample_box() -> NormalizedBoundingBox:
    return NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.5, xmax=0.5)


def test_organization_entity() -> None:
    """Verify Organization creation and invariant validation."""
    org = Organization.create(
        name="Tata Steel Procurement",
        industry_sector=IndustrySector.MANUFACTURING,
    )
    assert org.id.startswith(ORG_PREFIX)
    assert org.name == "Tata Steel Procurement"
    assert org.industry_sector == IndustrySector.MANUFACTURING

    with pytest.raises(ValidationError):
        Organization.create(name="", industry_sector=IndustrySector.MANUFACTURING)


def test_authorized_subject_entity() -> None:
    """Verify AuthorizedSubject creation and organization membership check."""
    org_id = generate_id(ORG_PREFIX)
    subj = AuthorizedSubject.create(
        organization_id=org_id,
        full_name="Rajesh Sharma",
        designation="Quality Assurance Head",
        id_reference="EMP-QA-9021",
    )
    assert subj.id.startswith(SUBJ_PREFIX)
    assert subj.belongs_to_organization(org_id) is True
    assert subj.belongs_to_organization("org_other123456789012345678901234") is False

    with pytest.raises(ValidationError):
        AuthorizedSubject.create(org_id, "", "Designation", "REF-1")


def test_signature_reference_profile_entity() -> None:
    """Verify SignatureReferenceProfile chain of custody and expiry checking."""
    org_id = generate_id(ORG_PREFIX)
    subj_id = generate_id(SUBJ_PREFIX)
    now = utc_now()
    expiry = now + timedelta(days=365)

    profile = SignatureReferenceProfile.create(
        subject_id=subj_id,
        organization_id=org_id,
        crop_image_path="/storage/signatures/sample1.png",
        sha256_hash=SAMPLE_SHA256,
        source_document_ref="DOC-ENROLL-2026-01",
        consent_mandate_ref="CONSENT-FORM-SIGNED-2026-01-15",
        enrollment_date=now,
        retention_expiry_date=expiry,
        access_role_required="FORENSIC_INVESTIGATOR",
    )

    assert profile.id.startswith(SIGREF_PREFIX)
    assert profile.is_expired() is False
    assert profile.is_expired(as_of=expiry + timedelta(days=1)) is True
    assert profile.is_authorized_for_role("FORENSIC_INVESTIGATOR") is True
    assert profile.is_authorized_for_role("LEAD_AUDITOR") is True
    assert profile.is_authorized_for_role("VIEWER") is False

    # Mandatory consent mandate invariant
    with pytest.raises(ValidationError):
        SignatureReferenceProfile.create(
            subject_id=subj_id,
            organization_id=org_id,
            crop_image_path="/path.png",
            sha256_hash=SAMPLE_SHA256,
            source_document_ref="REF-1",
            consent_mandate_ref="",  # Empty mandate forbidden
        )

    # Expiry before enrollment forbidden
    with pytest.raises(ValidationError):
        SignatureReferenceProfile.create(
            subject_id=subj_id,
            organization_id=org_id,
            crop_image_path="/path.png",
            sha256_hash=SAMPLE_SHA256,
            source_document_ref="REF-1",
            consent_mandate_ref="MANDATE-1",
            enrollment_date=now,
            retention_expiry_date=now - timedelta(days=1),
        )


def test_document_entity() -> None:
    """Verify Document creation, status transitions, structured content, and profile."""
    inv_id = generate_id(INV_PREFIX)
    doc = Document.create(
        investigation_id=inv_id,
        original_filename="Mill_Test_Certificate_882.pdf",
        file_hash_sha256=SAMPLE_SHA256,
        mime_type="application/pdf",
        page_count=3,
        file_size_bytes=1048576,
        structured_content={"tables": 1, "fields": 15},
        metadata_json={"Producer": "ReportLab 3.6"},
    )
    assert doc.id.startswith(DOC_PREFIX)
    assert doc.status == DocumentStatus.UPLOADED
    assert doc.structured_content == {"tables": 1, "fields": 15}
    assert doc.metadata_json == {"Producer": "ReportLab 3.6"}

    # Unsupported format
    with pytest.raises(UnsupportedFormatError):
        Document.create(inv_id, "file.exe", SAMPLE_SHA256, "application/x-msdownload")

    # Bad hash
    with pytest.raises(ValidationError):
        Document.create(inv_id, "file.pdf", "bad-hash", "application/pdf")

    # Status updates
    doc.mark_processed(QualityStatus.VERIFIED_HIGH)
    assert doc.status == DocumentStatus.PROCESSED
    assert doc.quality_status == QualityStatus.VERIFIED_HIGH

    # Language profile update
    profile = LanguageDetectionProfile(
        primary_language="hin",
        primary_script="Deva",
        confidence=0.98,
    )
    doc.set_language_profile(profile)
    assert doc.primary_language == "hin"
    assert doc.primary_script == "Deva"


def test_document_page_entity() -> None:
    """Verify DocumentPage creation, dimensions, and property accessors."""
    doc_id = generate_id(DOC_PREFIX)
    dims = PageDimensions(width_pixels=2480, height_pixels=3508, dpi=300)
    page = DocumentPage.create(
        document_id=doc_id,
        page_number=1,
        dimensions=dims,
        image_storage_path="/storage/pages/p1.png",
        has_digital_text=True,
        text_layer_type=TextLayerType.VECTOR_NATIVE,
    )
    assert page.id.startswith(PAGE_PREFIX)
    assert page.page_number == 1
    assert page.width_pixels == 2480
    assert page.height_pixels == 3508
    assert page.dpi == 300

    with pytest.raises(ValidationError):
        DocumentPage.create(doc_id, 0, dims, "/storage/p.png")


def test_extracted_field_entity() -> None:
    """Verify ExtractedField verbatim raw_text, field_type, and confidence."""
    page_id = generate_id(PAGE_PREFIX)
    field = ExtractedField.create(
        page_id=page_id,
        field_name="total_amount_inr",
        field_value="1450000.00",
        raw_text="₹ 14,50,000.00 /-",
        field_type="CURRENCY",
        confidence=0.96,
        extraction_source=ExtractionSourceType.DIGITAL_TEXT,
        normalized_bbox=_sample_box(),
    )
    assert field.id.startswith(FLD_PREFIX)
    assert field.raw_text == "₹ 14,50,000.00 /-"
    assert field.field_value == "1450000.00"
    assert field.field_type == "CURRENCY"

    with pytest.raises(ConfidenceRangeError):
        ExtractedField.create(page_id, "field", "val", "raw", 1.2)


def test_entity_model() -> None:
    """Verify Entity canonical value creation."""
    inv_id = generate_id(INV_PREFIX)
    entity = Entity.create(
        investigation_id=inv_id,
        entity_type=EntityType.ORGANIZATION_NAME,
        canonical_value="JSW Steel Ltd.",
    )
    assert entity.id.startswith(ENT_PREFIX)
    assert entity.canonical_value == "JSW Steel Ltd."

    with pytest.raises(ValidationError):
        Entity.create(inv_id, EntityType.PERSON_NAME, "")


def test_evidence_entity() -> None:
    """Verify Evidence creation, evd_ prefix, and spatial coordinate properties."""
    page_id = generate_id(PAGE_PREFIX)
    ev = Evidence.create(
        page_id=page_id,
        crop_image_path="/storage/crops/crop_01.png",
        normalized_bbox=_sample_box(),
        grounding_explanation="Manipulated rate column on line item 3",
        pixel_x=100,
        pixel_y=200,
        pixel_width=300,
        pixel_height=400,
    )
    assert ev.id.startswith(EVD_PREFIX)
    assert ev.id.startswith("evd_")
    assert ev.pixel_width == 300
    assert ev.norm_ymin == pytest.approx(0.1)
    assert ev.norm_xmin == pytest.approx(0.1)
    assert ev.grounding_explanation == "Manipulated rate column on line item 3"

    with pytest.raises(ValidationError):
        Evidence.create(page_id, "", _sample_box())
    with pytest.raises(ValidationError):
        Evidence.create(page_id, "/path.png", _sample_box(), pixel_width=-10)

    # Legacy ev_ prefix is strictly rejected
    with pytest.raises(InvalidIdentifierError):
        Evidence.create(
            page_id=page_id,
            crop_image_path="/path.png",
            normalized_bbox=_sample_box(),
            evidence_id="ev_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        )


def test_cross_document_relation_entity() -> None:
    """Verify CrossDocumentRelation and self-link prohibition."""
    inv_id = generate_id(INV_PREFIX)
    doc_a = generate_id(DOC_PREFIX)
    doc_b = generate_id(DOC_PREFIX)

    rel = CrossDocumentRelation.create(
        investigation_id=inv_id,
        source_document_id=doc_a,
        target_document_id=doc_b,
        relation_type=RelationType.CONFLICTS_WITH,
        description="PO quantity 500 tons conflicts with Challan delivery 300 tons",
    )
    assert rel.id.startswith(REL_PREFIX)
    assert rel.source_document_id != rel.target_document_id

    # Self-link is strictly forbidden
    with pytest.raises(RelationshipConstraintError) as exc_info:
        CrossDocumentRelation.create(
            investigation_id=inv_id,
            source_document_id=doc_a,
            target_document_id=doc_a,
            relation_type=RelationType.CONFLICTS_WITH,
            description="Self link",
        )
    assert "Cannot link doc to itself" in str(exc_info.value)


def test_review_decision_entity() -> None:
    """Verify ReviewDecision creation and mandatory fields."""
    finding_id = generate_id(FND_PREFIX)
    reviewer_id = generate_id(SUBJ_PREFIX)

    dec = ReviewDecision.create(
        finding_id=finding_id,
        reviewer_id=reviewer_id,
        decision=ReviewDecisionType.CONFIRMED,
        rationale="Discrepancy verified against physical gate pass log.",
    )
    assert dec.id.startswith(REV_PREFIX)
    assert dec.decision == ReviewDecisionType.CONFIRMED

    with pytest.raises(ValidationError):
        ReviewDecision.create(finding_id, "", ReviewDecisionType.CONFIRMED, "Rationale")
    with pytest.raises(ValidationError):
        ReviewDecision.create(finding_id, reviewer_id, ReviewDecisionType.CONFIRMED, "")


def test_dossier_entity() -> None:
    """Verify Dossier report creation, dossier_json property, and hash integrity."""
    inv_id = generate_id(INV_PREFIX)
    dossier = Dossier.create(
        investigation_id=inv_id,
        dossier_data={"summary": "Audit complete", "findings_count": 3},
        pdf_storage_path="/storage/dossiers/dossier_01.pdf",
        pdf_hash_sha256=SAMPLE_SHA256,
    )
    assert dossier.id.startswith(DOS_PREFIX)
    assert dossier.pdf_hash_sha256 == SAMPLE_SHA256
    assert dossier.dossier_json == {"summary": "Audit complete", "findings_count": 3}

    with pytest.raises(ValidationError):
        Dossier.create(inv_id, {}, "", SAMPLE_SHA256)
    with pytest.raises(ValidationError):
        Dossier.create(inv_id, {}, "/path.pdf", "not-a-sha256")


def test_audit_event_immutability() -> None:
    """Verify AuditEvent frozen dataclass immutability."""
    inv_id = generate_id(INV_PREFIX)
    event = AuditEvent.create(
        investigation_id=inv_id,
        event_type=AuditEventType.HUMAN_REVIEW_CONFIRMED,
        actor_type=ActorType.HUMAN_ANALYST,
        actor_id="subj_analyst_01",
        event_payload={"finding_id": "fnd_123"},
    )
    assert event.id.startswith("aud_")
    assert event.event_type == AuditEventType.HUMAN_REVIEW_CONFIRMED

    # Immutability
    with pytest.raises(FrozenInstanceError):
        event.actor_id = "other_actor"  # type: ignore[misc]

    with pytest.raises(ValidationError):
        AuditEvent.create(
            investigation_id=inv_id,
            event_type=AuditEventType.HUMAN_REVIEW_CONFIRMED,
            actor_type=ActorType.HUMAN_ANALYST,
            actor_id="",
        )
