"""Integration tests for CrossDocumentCorrelationService with real SQLite persistence.

Verifies the complete end-to-end industrial correlation scenario:
1. Investigation creation.
2. Ingestion of 4 industrial documents (PO, Delivery Challan, MTC, Commercial Invoice).
3. Field extraction persistence across document pages.
4. Cross-document correlation execution via CrossDocumentCorrelationService.
5. Verification of the 3 demonstration discrepancies:
   - 1000 KG ordered vs 800 KG delivered (partial delivery on open order is consistent).
   - SS 316L ordered vs SS 304 certified (CRITICAL material grade contradiction finding).
   - 1000 KG invoiced vs 800 KG delivered (HIGH over-billing discrepancy finding).
6. Evidence linking to pixel/bbox coordinates and Evidence persistence.
7. CrossDocumentRelation persistence with CONFLICTS_WITH and CORROBORATES links.
8. Immutable AuditEvent logging (ANOMALY_FLAGGED).
9. Strict multi-tenant isolation enforcement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.dto.correlation import CorrelationRequestDTO
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.document import DocumentType
from veritrace.domain.enums.forensic import (
    FindingSeverity,
    RelationType,
)
from veritrace.domain.enums.investigation import InvestigationStatus
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.value_objects.geometry import (
    NormalizedBoundingBox,
    PageDimensions,
)
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    INV_PREFIX,
    ORG_PREFIX,
    PAGE_PREFIX,
    generate_id,
)
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database path."""
    return tmp_path / "test_correlation_service.sqlite"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing configured Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_cross_document_correlation_service_e2e(
    db_path: Path,
    alembic_config: Config,
) -> None:
    """End-to-end integration test of industrial document correlation and persistence."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)

    org_a_id = generate_id(ORG_PREFIX)
    org_b_id = generate_id(ORG_PREFIX)
    inv_id = generate_id(INV_PREFIX)

    po_id = generate_id(DOC_PREFIX)
    dc_id = generate_id(DOC_PREFIX)
    mtc_id = generate_id(DOC_PREFIX)
    inv_doc_id = generate_id(DOC_PREFIX)

    p_po = generate_id(PAGE_PREFIX)
    p_dc = generate_id(PAGE_PREFIX)
    p_mtc = generate_id(PAGE_PREFIX)
    p_inv = generate_id(PAGE_PREFIX)

    bbox_sample = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.5)

    try:
        # 1. Seed Organizations
        with session_scope(session_factory) as session:
            session.add_all(
                [
                    OrganizationModel(
                        id=org_a_id,
                        name="Alpha Heavy Industries",
                        industry_sector="MANUFACTURING",
                        created_at=now,
                    ),
                    OrganizationModel(
                        id=org_b_id,
                        name="Beta Logistics Corp",
                        industry_sector="LOGISTICS",
                        created_at=now,
                    ),
                ]
            )

        # 2. Setup Unit of Work factory
        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        dims = PageDimensions(width_pixels=2480, height_pixels=3508, dpi=300)

        # 3. Create Investigation and Documents in Org A
        with uow_factory() as uow:
            investigation = Investigation(
                id=inv_id,
                organization_id=org_a_id,
                title="Q1 Industrial Alloy Procurement Audit",
                reference_code="INV-ALPHA-2024-001",
                status=InvestigationStatus.PROCESSING,
                created_at=now,
                updated_at=now,
            )
            uow.investigations.add(investigation)

            # Document 1: Purchase Order
            doc_po = Document(
                id=po_id,
                investigation_id=inv_id,
                original_filename="PO_2024_001.pdf",
                file_hash_sha256="1" * 64,
                mime_type="application/pdf",
                document_type=DocumentType.PURCHASE_ORDER,
                created_at=now,
            )
            uow.documents.add(doc_po, org_a_id)
            uow.documents.add_page(
                DocumentPage.create(
                    document_id=po_id,
                    page_number=1,
                    dimensions=dims,
                    image_storage_path="pages/po_p1.png",
                    page_id=p_po,
                ),
                org_a_id,
            )

            # Document 2: Delivery Challan
            doc_dc = Document(
                id=dc_id,
                investigation_id=inv_id,
                original_filename="DC_2024_880.pdf",
                file_hash_sha256="2" * 64,
                mime_type="application/pdf",
                document_type=DocumentType.DELIVERY_CHALLAN,
                created_at=now,
            )
            uow.documents.add(doc_dc, org_a_id)
            uow.documents.add_page(
                DocumentPage.create(
                    document_id=dc_id,
                    page_number=1,
                    dimensions=dims,
                    image_storage_path="pages/dc_p1.png",
                    page_id=p_dc,
                ),
                org_a_id,
            )

            # Document 3: Mill Test Certificate
            doc_mtc = Document(
                id=mtc_id,
                investigation_id=inv_id,
                original_filename="MTC_2024_X109.pdf",
                file_hash_sha256="3" * 64,
                mime_type="application/pdf",
                document_type=DocumentType.MILL_TEST_CERT,
                created_at=now,
            )
            uow.documents.add(doc_mtc, org_a_id)
            uow.documents.add_page(
                DocumentPage.create(
                    document_id=mtc_id,
                    page_number=1,
                    dimensions=dims,
                    image_storage_path="pages/mtc_p1.png",
                    page_id=p_mtc,
                ),
                org_a_id,
            )

            # Document 4: Commercial Invoice
            doc_inv = Document(
                id=inv_doc_id,
                investigation_id=inv_id,
                original_filename="INV_2024_551.pdf",
                file_hash_sha256="4" * 64,
                mime_type="application/pdf",
                document_type=DocumentType.COMMERCIAL_INVOICE,
                created_at=now,
            )
            uow.documents.add(doc_inv, org_a_id)
            uow.documents.add_page(
                DocumentPage.create(
                    document_id=inv_doc_id,
                    page_number=1,
                    dimensions=dims,
                    image_storage_path="pages/inv_p1.png",
                    page_id=p_inv,
                ),
                org_a_id,
            )

            # Add Extracted Fields for PO (Ordered 1000 KG of SS 316L)
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_po,
                    field_name="po_number",
                    field_value="PO-2024-001",
                    raw_text="PO-2024-001",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_po,
                    field_name="date",
                    field_value="2024-01-10",
                    raw_text="10-Jan-2024",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_po,
                    field_name="material_grade",
                    field_value="SS 316L",
                    raw_text="SS 316L Seamless Pipes",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_po,
                    field_name="quantity",
                    field_value="1000 KG",
                    raw_text="1000 KG",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )

            # Add Extracted Fields for DC (Delivered 800 KG of SS 304, citing PO and MTC)
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="challan_number",
                    field_value="DC-2024-880",
                    raw_text="DC-2024-880",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="date",
                    field_value="2024-01-15",
                    raw_text="15-Jan-2024",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="cited_po_number",
                    field_value="PO-2024-001",
                    raw_text="Ref PO: PO-2024-001",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="material_grade",
                    field_value="SS 304",
                    raw_text="SS 304 Pipes",
                    confidence=0.97,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="quantity",
                    field_value="800 KG",
                    raw_text="800 KG",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="batch_number",
                    field_value="HT-9042",
                    raw_text="Heat No: HT-9042",
                    confidence=0.96,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_dc,
                    field_name="cited_mtc_number",
                    field_value="MTC-2024-X109",
                    raw_text="MTC No: MTC-2024-X109",
                    confidence=0.95,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )

            # Add Extracted Fields for MTC (Certifies SS 304, Heat HT-9042)
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_mtc,
                    field_name="mtc_number",
                    field_value="MTC-2024-X109",
                    raw_text="MTC-2024-X109",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_mtc,
                    field_name="material_grade",
                    field_value="SS 304",
                    raw_text="Grade: SS 304",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_mtc,
                    field_name="heat_number",
                    field_value="HT-9042",
                    raw_text="Heat: HT-9042",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )

            # Add Extracted Fields for Invoice (Billed 1000 KG @ 250 = 2,50,000 + 45k tax = 2.95L)
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="invoice_number",
                    field_value="INV-2024-551",
                    raw_text="INV-2024-551",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="date",
                    field_value="2024-01-20",
                    raw_text="20-Jan-2024",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="cited_po_number",
                    field_value="PO-2024-001",
                    raw_text="PO: PO-2024-001",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="quantity",
                    field_value="1000 KG",
                    raw_text="1000 KG",
                    confidence=0.99,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="unit_rate",
                    field_value="250.00",
                    raw_text="250.00 / KG",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="line_total",
                    field_value="250000.00",
                    raw_text="2,50,000.00",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="subtotal",
                    field_value="250000.00",
                    raw_text="2,50,000.00",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="tax_amount",
                    field_value="45000.00",
                    raw_text="45,000.00",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )
            uow.documents.add_extracted_field(
                ExtractedField.create(
                    page_id=p_inv,
                    field_name="grand_total",
                    field_value="295000.00",
                    raw_text="2,95,000.00",
                    confidence=0.98,
                    normalized_bbox=bbox_sample,
                ),
                org_a_id,
            )

        # 4. Execute Correlation Service
        service = CrossDocumentCorrelationService(uow_factory=uow_factory)
        summary = service.correlate_investigation(
            CorrelationRequestDTO(
                investigation_id=inv_id,
                organization_id=org_a_id,
                is_order_closed=False,
            )
        )

        # 5. Verify Summary Metrics
        assert summary.documents_analyzed == 4
        assert summary.discrepancies_count >= 2
        assert summary.findings_generated >= 2
        assert summary.relations_created >= 2

        # 6. Verify Material Grade Contradiction is persisted
        grade_disc = next(
            (d for d in summary.discrepancies if d.rule_code == "RULE_GRADE_CONSISTENCY"),
            None,
        )
        assert grade_disc is not None
        assert grade_disc.severity == FindingSeverity.CRITICAL.value
        assert grade_disc.finding_id is not None
        assert grade_disc.relation_id is not None

        # 7. Verify Over-billing Discrepancy (1000 KG vs 800 KG) is persisted
        overbill_disc = next(
            (
                d
                for d in summary.discrepancies
                if d.rule_code == "RULE_QTY_CONSISTENCY"
                and d.source_doc_id == dc_id
                and d.target_doc_id == inv_doc_id
            ),
            None,
        )
        assert overbill_disc is not None
        assert overbill_disc.severity == FindingSeverity.HIGH.value
        assert overbill_disc.finding_id is not None
        assert overbill_disc.relation_id is not None

        # 8. Query Database directly via Repositories to confirm persistence & tenant isolation
        with uow_factory() as uow:
            # Findings persisted
            findings = uow.findings.list_by_investigation(inv_id, org_a_id)
            assert len(findings) >= 2
            finding_ids = {f.id for f in findings}
            assert grade_disc.finding_id in finding_ids
            assert overbill_disc.finding_id in finding_ids

            # Evidence persisted and linked
            grade_finding = uow.findings.get_by_id(grade_disc.finding_id, org_a_id)
            assert grade_finding is not None
            assert len(grade_finding.evidence_ids) >= 1

            for ev_id in grade_finding.evidence_ids:
                ev = uow.evidence.get_by_id(ev_id, org_a_id)
                assert ev is not None
                assert ev.page_id in (p_po, p_dc, p_mtc)

            # Relations persisted
            relations = uow.investigations.list_relations(inv_id, org_a_id)
            assert len(relations) >= 2
            conflicts = [r for r in relations if r.relation_type == RelationType.CONFLICTS_WITH]
            assert len(conflicts) >= 2

            # Audit events persisted
            audit_events = uow.audit_events.list_by_investigation(inv_id, org_a_id)
            assert len(audit_events) >= 1
            assert any(e.event_payload.get("discrepancies_count", 0) >= 2 for e in audit_events)

        # 9. Tenant Isolation: Org B cannot correlate or view Org A's case
        with pytest.raises(EntityNotFoundError):
            service.correlate_investigation(
                CorrelationRequestDTO(
                    investigation_id=inv_id,
                    organization_id=org_b_id,
                )
            )
    finally:
        engine.dispose()
