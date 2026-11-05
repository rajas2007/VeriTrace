"""Unit tests for bidirectional domain-to-ORM mappers."""

from __future__ import annotations

from datetime import UTC, datetime

from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.cross_document_relation import (
    CrossDocumentRelation,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.entity import Entity
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.entities.investigation_job import InvestigationJob
from veritrace.domain.entities.organization import Organization
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.entities.signature_reference import (
    SignatureReferenceProfile,
)
from veritrace.domain.enums.audit import (
    ActorType,
    AuditEventType,
    EntityType,
    IndustrySector,
)
from veritrace.domain.enums.document import (
    DocumentStatus,
    DocumentType,
    ExtractionSourceType,
    QualityStatus,
    TextLayerType,
)
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    RelationType,
    ReviewDecisionType,
    ReviewStatus,
)
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    JobStatus,
    RiskClassification,
)
from veritrace.domain.value_objects.geometry import (
    NormalizedBoundingBox,
    PageDimensions,
)
from veritrace.domain.value_objects.multilingual import (
    LanguageDetectionProfile,
    LanguageScriptIdentification,
    LanguageScriptRegion,
)
from veritrace.infrastructure.persistence.mappers import (
    AuditEventMapper,
    AuthorizedSubjectMapper,
    CrossDocumentRelationMapper,
    DocumentMapper,
    DocumentPageMapper,
    DossierMapper,
    EntityMapper,
    EvidenceMapper,
    ExtractedFieldMapper,
    FindingMapper,
    InvestigationJobMapper,
    InvestigationMapper,
    OrganizationMapper,
    ReviewDecisionMapper,
    SignatureReferenceMapper,
    bbox_to_dict,
    dict_to_bbox,
    dict_to_language_profile,
    language_profile_to_dict,
)


def test_bbox_serialization_round_trip() -> None:
    """Verify NormalizedBoundingBox serialization and deserialization."""
    bbox = NormalizedBoundingBox(ymin=0.1, xmin=0.2, ymax=0.8, xmax=0.9)
    d = bbox_to_dict(bbox)
    assert d == {"ymin": 0.1, "xmin": 0.2, "ymax": 0.8, "xmax": 0.9}

    restored = dict_to_bbox(d)
    assert restored == bbox

    # Also test from 4-element list
    restored_from_list = dict_to_bbox([0.1, 0.2, 0.8, 0.9])
    assert restored_from_list == bbox


def test_language_profile_serialization_round_trip() -> None:
    """Verify LanguageDetectionProfile serialization preserves multi-script regions."""
    region_bbox = NormalizedBoundingBox(ymin=0.5, xmin=0.1, ymax=0.9, xmax=0.8)
    profile = LanguageDetectionProfile(
        primary_language="hin",
        primary_script="Deva",
        confidence=0.96,
        detected_languages=(
            LanguageScriptIdentification("hin", "Deva", 0.96),
            LanguageScriptIdentification("eng", "Latn", 0.88),
        ),
        regions=(
            LanguageScriptRegion(
                language="hin",
                script="Deva",
                confidence=0.97,
                normalized_bbox=region_bbox,
            ),
        ),
        detection_engine="paddleocr-v4",
        model_version="indic-mobile-v1",
    )

    d = language_profile_to_dict(profile)
    assert d is not None
    assert d["primary_language"] == "hin"
    assert len(d["regions"]) == 1

    restored = dict_to_language_profile(d)
    assert restored == profile
    assert restored.regions[0].normalized_bbox == region_bbox


def test_organization_mapper_round_trip() -> None:
    """Verify Organization bidirectional mapping."""
    now = datetime.now(UTC)
    entity = Organization(
        id="org_0123456789abcdef0123456789abcdef",
        name="Tata Steel Industrial Corp",
        industry_sector=IndustrySector.MANUFACTURING,
        created_at=now,
    )
    model = OrganizationMapper.to_model(entity)
    assert model.id == entity.id
    assert model.name == entity.name
    assert model.industry_sector == "MANUFACTURING"

    restored = OrganizationMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.name == entity.name
    assert restored.industry_sector == entity.industry_sector
    assert restored.created_at == entity.created_at


def test_authorized_subject_mapper_round_trip() -> None:
    """Verify AuthorizedSubject bidirectional mapping."""
    now = datetime.now(UTC)
    entity = AuthorizedSubject(
        id="subj_0123456789abcdef0123456789abcdef",
        organization_id="org_0123456789abcdef0123456789abcdef",
        full_name="Dr. Rajesh Sharma",
        designation="Chief Metallurgist",
        id_reference="EMP-9021",
        created_at=now,
    )
    model = AuthorizedSubjectMapper.to_model(entity)
    assert model.id == entity.id
    assert model.organization_id == entity.organization_id

    restored = AuthorizedSubjectMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.full_name == entity.full_name
    assert restored.created_at == entity.created_at


def test_signature_reference_mapper_round_trip() -> None:
    """Verify SignatureReferenceProfile bidirectional mapping."""
    now = datetime.now(UTC)
    expiry = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)
    entity = SignatureReferenceProfile(
        id="sigref_0123456789abcdef0123456789abcdef",
        subject_id="subj_0123456789abcdef0123456789abcdef",
        organization_id="org_0123456789abcdef0123456789abcdef",
        crop_image_path="signatures/crop_01.png",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        source_document_ref="DOC-CERT-2026-001",
        consent_mandate_ref="BOARD-RES-2026-44",
        enrollment_date=now,
        embedding_vector=b"\x00\x01\x02\x03\x04\x05",
        retention_expiry_date=expiry,
        access_role_required="FORENSIC_INVESTIGATOR",
        provenance_json={"witness": "Compliance Officer", "scanner": "Epson DS-70000"},
    )
    model = SignatureReferenceMapper.to_model(entity)
    assert model.id == entity.id
    assert model.embedding_vector == b"\x00\x01\x02\x03\x04\x05"

    restored = SignatureReferenceMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.sha256_hash == entity.sha256_hash
    assert restored.enrollment_date == entity.enrollment_date
    assert restored.retention_expiry_date == entity.retention_expiry_date
    assert restored.provenance_json == entity.provenance_json


def test_investigation_mapper_round_trip() -> None:
    """Verify Investigation bidirectional mapping."""
    now = datetime.now(UTC)
    entity = Investigation(
        id="inv_0123456789abcdef0123456789abcdef",
        title="Procurement Audit Q1",
        reference_code="INV-2026-001",
        status=InvestigationStatus.PROCESSING,
        risk_score=0.45,
        risk_classification=RiskClassification.FLAGGED_INCONSISTENCY,
        organization_id="org_0123456789abcdef0123456789abcdef",
        created_at=now,
        updated_at=now,
    )
    model = InvestigationMapper.to_model(entity)
    assert model.status == "PROCESSING"
    assert model.risk_classification == "FLAGGED_INCONSISTENCY"

    restored = InvestigationMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.status == InvestigationStatus.PROCESSING
    assert restored.risk_classification == RiskClassification.FLAGGED_INCONSISTENCY


def test_investigation_job_mapper_round_trip() -> None:
    """Verify InvestigationJob bidirectional mapping."""
    now = datetime.now(UTC)
    entity = InvestigationJob(
        id="job_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        status=JobStatus.RUNNING,
        current_stage="TEXT_EXTRACTION",
        progress_pct=45,
        created_at=now,
        stage_message="Extracting page 3 of 7",
        can_resume=True,
        retry_count=1,
        started_at=now,
    )
    model = InvestigationJobMapper.to_model(entity)
    assert model.status == "RUNNING"
    assert model.can_resume is True

    restored = InvestigationJobMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.status == JobStatus.RUNNING
    assert restored.progress_pct == 45
    assert restored.stage_message == "Extracting page 3 of 7"


def test_document_mapper_round_trip() -> None:
    """Verify Document bidirectional mapping with multilingual profile."""
    now = datetime.now(UTC)
    profile = LanguageDetectionProfile(
        primary_language="mar",
        primary_script="Deva",
        confidence=0.92,
        detected_languages=(LanguageScriptIdentification("mar", "Deva", 0.92),),
    )
    entity = Document(
        id="doc_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        original_filename="invoice_marathi.pdf",
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/pdf",
        created_at=now,
        document_type=DocumentType.COMMERCIAL_INVOICE,
        primary_language="mar",
        primary_script="Deva",
        language_profile=profile,
        classification_confidence=0.95,
        page_count=3,
        file_size_bytes=1048576,
        storage_path="documents/inv_01.pdf",
        quality_status=QualityStatus.VERIFIED_HIGH,
        structured_content={"total_amount": "125000.00"},
        metadata_json={"producer": "VeriTrace Scanner"},
        status=DocumentStatus.PROCESSED,
    )
    model = DocumentMapper.to_model(entity)
    assert model.document_type == "COMMERCIAL_INVOICE"
    assert model.quality_status == "VERIFIED_HIGH"
    assert model.status == "PROCESSED"

    restored = DocumentMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.document_type == DocumentType.COMMERCIAL_INVOICE
    assert restored.language_profile == profile
    assert restored.structured_content == {"total_amount": "125000.00"}


def test_document_page_mapper_round_trip() -> None:
    """Verify DocumentPage bidirectional mapping with dimensions."""
    dimensions = PageDimensions(width_pixels=2479, height_pixels=3508, dpi=300)
    entity = DocumentPage(
        id="page_0123456789abcdef0123456789abcdef",
        document_id="doc_0123456789abcdef0123456789abcdef",
        page_number=1,
        dimensions=dimensions,
        image_storage_path="pages/page_001.png",
        has_digital_text=True,
        text_layer_type=TextLayerType.HYBRID,
        primary_language="eng",
        primary_script="Latn",
    )
    model = DocumentPageMapper.to_model(entity)
    assert model.width_pixels == 2479
    assert model.height_pixels == 3508
    assert model.text_layer_type == "HYBRID"

    restored = DocumentPageMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.dimensions == dimensions
    assert restored.text_layer_type == TextLayerType.HYBRID


def test_extracted_field_mapper_round_trip() -> None:
    """Verify ExtractedField bidirectional mapping with verbatim Indic glyphs."""
    bbox = NormalizedBoundingBox(ymin=0.2, xmin=0.3, ymax=0.25, xmax=0.6)
    entity = ExtractedField(
        id="fld_0123456789abcdef0123456789abcdef",
        page_id="page_0123456789abcdef0123456789abcdef",
        field_name="heat_number",
        field_value="HN-9082-A",
        raw_text="ऊष्मा क्रमांक: ९०८२-अ",
        confidence=0.98,
        field_type="IDENTIFIER",
        entity_id="ent_0123456789abcdef0123456789abcdef",
        language="mar",
        script="Deva",
        lang_confidence=0.95,
        normalized_bbox=bbox,
        extraction_source=ExtractionSourceType.OCR,
        ocr_engine="paddleocr-v4",
    )
    model = ExtractedFieldMapper.to_model(entity)
    assert model.raw_text == "ऊष्मा क्रमांक: ९०८२-अ"
    assert model.extraction_source == "ocr"

    restored = ExtractedFieldMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.raw_text == entity.raw_text
    assert restored.normalized_bbox == bbox
    assert restored.extraction_source == ExtractionSourceType.OCR


def test_entity_mapper_round_trip() -> None:
    """Verify Entity bidirectional mapping."""
    entity = Entity(
        id="ent_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        entity_type=EntityType.TAX_IDENTIFIER,
        canonical_value="PAN: ABCDE1234F",
    )
    model = EntityMapper.to_model(entity)
    assert model.entity_type == "TAX_IDENTIFIER"

    restored = EntityMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.entity_type == EntityType.TAX_IDENTIFIER
    assert restored.canonical_value == "PAN: ABCDE1234F"


def test_evidence_mapper_round_trip() -> None:
    """Verify Evidence bidirectional mapping."""
    bbox = NormalizedBoundingBox(ymin=0.4, xmin=0.5, ymax=0.6, xmax=0.7)
    entity = Evidence(
        id="evd_0123456789abcdef0123456789abcdef",
        page_id="page_0123456789abcdef0123456789abcdef",
        crop_image_path="evidence/crop_01.png",
        normalized_bbox=bbox,
        pixel_x=1200,
        pixel_y=1400,
        pixel_width=400,
        pixel_height=300,
        heatmap_image_path="evidence/heat_01.png",
        grounding_explanation="Copy-move artifact detected around date stamp",
    )
    model = EvidenceMapper.to_model(entity)
    assert model.pixel_width == 400

    restored = EvidenceMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.normalized_bbox == bbox
    assert restored.heatmap_image_path == "evidence/heat_01.png"


def test_finding_mapper_round_trip() -> None:
    """Verify Finding bidirectional mapping preserving evidence set."""
    now = datetime.now(UTC)
    ev_ids = {"evd_0123456789abcdef0123456789abcdef", "evd_fedcba9876543210fedcba9876543210"}
    entity = Finding(
        id="fnd_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        category=FindingCategory.COPY_MOVE_CLONE,
        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
        severity=FindingSeverity.HIGH,
        title="Duplicated Seal Impression",
        narrative_explanation="Identical noise residuals found across multiple pages",
        confidence=0.88,
        investigator_guidance="Compare against authentic physical specimen stamp",
        review_status=ReviewStatus.PENDING_REVIEW,
        signature_reference_id="sigref_0123456789abcdef0123456789abcdef",
        created_at=now,
        _evidence_ids=ev_ids,
    )
    model = FindingMapper.to_model(entity)
    assert model.epistemic_tier == "DETECTED_INCONSISTENCY"
    assert model.severity == "HIGH"

    restored = FindingMapper.to_entity(model, evidence_ids=ev_ids)
    assert restored.id == entity.id
    assert restored.epistemic_tier == EpistemicTier.DETECTED_INCONSISTENCY
    assert restored.severity == FindingSeverity.HIGH
    assert restored.evidence_ids == frozenset(ev_ids)


def test_cross_document_relation_mapper_round_trip() -> None:
    """Verify CrossDocumentRelation bidirectional mapping."""
    entity = CrossDocumentRelation(
        id="rel_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        source_document_id="doc_0123456789abcdef0123456789abcdef",
        target_document_id="doc_fedcba9876543210fedcba9876543210",
        relation_type=RelationType.CONFLICTS_WITH,
        description="Heat number mismatch between MTC and Delivery Challan",
        finding_id="fnd_0123456789abcdef0123456789abcdef",
        similarity_score=0.15,
    )
    model = CrossDocumentRelationMapper.to_model(entity)
    assert model.relation_type == "CONFLICTS_WITH"

    restored = CrossDocumentRelationMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.relation_type == RelationType.CONFLICTS_WITH
    assert restored.similarity_score == 0.15


def test_review_decision_mapper_round_trip() -> None:
    """Verify ReviewDecision bidirectional mapping."""
    now = datetime.now(UTC)
    entity = ReviewDecision(
        id="rev_0123456789abcdef0123456789abcdef",
        finding_id="fnd_0123456789abcdef0123456789abcdef",
        reviewer_id="analyst_vikram",
        decision=ReviewDecisionType.CONFIRMED,
        rationale="Verified stamp duplication under high magnification",
        timestamp=now,
    )
    model = ReviewDecisionMapper.to_model(entity)
    assert model.decision == "CONFIRMED"

    restored = ReviewDecisionMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.decision == ReviewDecisionType.CONFIRMED
    assert restored.rationale == entity.rationale


def test_dossier_mapper_round_trip() -> None:
    """Verify Dossier bidirectional mapping."""
    now = datetime.now(UTC)
    entity = Dossier(
        id="dos_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        dossier_data={"summary": "Confirmed alterations detected", "score": 0.85},
        pdf_storage_path="dossiers/final_report.pdf",
        pdf_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        generated_at=now,
    )
    model = DossierMapper.to_model(entity)
    assert model.pdf_hash_sha256 == entity.pdf_hash_sha256

    restored = DossierMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.dossier_data == {"summary": "Confirmed alterations detected", "score": 0.85}
    assert restored.pdf_hash_sha256 == entity.pdf_hash_sha256


def test_audit_event_mapper_round_trip() -> None:
    """Verify AuditEvent bidirectional mapping."""
    now = datetime.now(UTC)
    entity = AuditEvent(
        id="aud_0123456789abcdef0123456789abcdef",
        investigation_id="inv_0123456789abcdef0123456789abcdef",
        event_type=AuditEventType.DOC_UPLOADED,
        actor_type=ActorType.HUMAN_ANALYST,
        actor_id="investigator_priya",
        timestamp=now,
        event_payload={"filename": "challan_signed.pdf", "pages": 2},
    )
    model = AuditEventMapper.to_model(entity)
    assert model.event_type == "DOC_UPLOADED"
    assert model.actor_type == "HUMAN_ANALYST"

    restored = AuditEventMapper.to_entity(model)
    assert restored.id == entity.id
    assert restored.event_type == AuditEventType.DOC_UPLOADED
    assert restored.actor_type == ActorType.HUMAN_ANALYST
    assert restored.event_payload == {"filename": "challan_signed.pdf", "pages": 2}
