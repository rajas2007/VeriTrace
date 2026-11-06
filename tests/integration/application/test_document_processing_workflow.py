"""Integration test demonstrating the complete Phase 5 Definition of Done workflow.

Workflow:
1. Create an organization.
2. Create an investigation under that organization.
3. Import an industrial PDF.
4. Validate and hash the original.
5. Store the original safely.
6. Create document and page records.
7. Extract digital text from the PDF.
8. Persist extraction results (ExtractedFields).
9. Retrieve the investigation and its documents.
10. Retrieve extraction results.
11. Verify corresponding audit events.
12. Verify that a different organization cannot access the data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.application.services.text_extraction_service import (
    TextExtractionService,
)
from veritrace.application.workflows.document_processing import (
    DocumentProcessingWorkflow,
)
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.document import DocumentType, TextLayerType
from veritrace.domain.exceptions.base import TenantIsolationError
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.organization import (
    OrganizationModel,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from veritrace.infrastructure.storage.document_storage import (
    OriginalDocumentStorage,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture providing isolated SQLite database path."""
    return tmp_path / "test_workflow_e2e.sqlite"


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    """Fixture providing isolated storage directory."""
    return tmp_path / "storage"


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    """Fixture providing Alembic Config pointing to temp DB."""
    cfg = Config("alembic.ini")
    url = f"sqlite:///{db_path.as_posix()}"
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _generate_industrial_tax_invoice_pdf() -> bytes:
    """Generate a realistic industrial tax invoice PDF in memory with PyMuPDF."""
    doc = pymupdf.open()

    # Page 1: Header, Supplier, Buyer, and Line Items
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "BHARAT HEAVY INDUSTRIAL CORPORATION", fontsize=16)
    p1.insert_text((50, 85), "COMMERCIAL TAX INVOICE", fontsize=12)
    p1.insert_text((50, 110), "Invoice No: BHIC/2026/INV-9042", fontsize=10)
    p1.insert_text((50, 130), "Date: 04-November-2026", fontsize=10)
    p1.insert_text((50, 150), "Supplier GSTIN: 27AAACB2142D1Z8", fontsize=10)
    p1.insert_text((50, 170), "Purchaser: LAKSHMI INFRASTRUCTURE LTD", fontsize=10)
    p1.insert_text((50, 210), "Item 1: Structural Steel Joists Grade IS 2062 E250", fontsize=10)
    p1.insert_text((50, 230), "Quantity: 24.5 MT -- Unit Rate: Rs. 62,500.00", fontsize=10)
    p1.insert_text((50, 250), "Taxable Subtotal: Rs. 15,31,250.00", fontsize=10)

    # Page 2: Tax Calculation, Signatory and Terms
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "TAX COMPUTATION & CERTIFICATION SUMMARY", fontsize=14)
    p2.insert_text((50, 90), "CGST @ 9%: Rs. 1,37,812.50", fontsize=10)
    p2.insert_text((50, 110), "SGST @ 9%: Rs. 1,37,812.50", fontsize=10)
    p2.insert_text((50, 140), "Total Invoice Value: Rs. 18,06,875.00", fontsize=12)
    p2.insert_text((50, 180), "Authorized Signatory: Rajiv Ramanathan (GM Finance)", fontsize=10)
    p2.insert_text((50, 210), "Quality Assurance Seal: QC-PASSED-2026", fontsize=10)

    content = doc.tobytes()
    doc.close()
    return bytes(content)


def test_full_document_processing_workflow_e2e(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Execute complete end-to-end Definition of Done workflow."""
    # 0. Infrastructure setup
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_primary = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    org_adversary = "org_bbbbbbbbbbbbbbbbbbbbbbbbbbbb0002"
    now = datetime.now(UTC)

    try:
        # STEP 1: Create Organization
        with session_scope(session_factory) as session:
            session.add(
                OrganizationModel(
                    id=org_primary,
                    name="Bharat Heavy Industries Ltd",
                    industry_sector="MANUFACTURING",
                    created_at=now,
                )
            )
            session.add(
                OrganizationModel(
                    id=org_adversary,
                    name="External Auditor Corp",
                    industry_sector="BFSI",
                    created_at=now,
                )
            )

        # Wire application services
        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        inv_service = InvestigationService(uow_factory)
        ingest_service = DocumentIngestionService(uow_factory, storage=storage)
        extract_service = TextExtractionService(uow_factory, storage=storage)
        workflow = DocumentProcessingWorkflow(
            investigation_service=inv_service,
            ingestion_service=ingest_service,
            extraction_service=extract_service,
        )

        # STEPS 2 to 8: Execute End-to-End Workflow
        pdf_bytes = _generate_industrial_tax_invoice_pdf()
        wf_result = workflow.execute_new_investigation_workflow(
            organization_id=org_primary,
            investigation_title="Vendor Billing & Procurement Verification",
            reference_code="CASE-2026-BHIC-01",
            filename="bhic_tax_invoice_9042.pdf",
            content=pdf_bytes,
            document_type=DocumentType.COMMERCIAL_INVOICE,
            actor_id="analyst_rajesh",
        )

        # STEP 4: Verify Validation and SHA-256 Hash
        assert wf_result.document.file_hash_sha256 is not None
        assert len(wf_result.document.file_hash_sha256) == 64

        # STEP 5: Verify Original File Stored Safely
        stored_path = Path(wf_result.document.storage_path)
        assert stored_path.is_file()
        assert stored_path.name == "bhic_tax_invoice_9042.pdf"
        assert storage.read_original(stored_path) == pdf_bytes

        # STEP 6: Verify Document and Page Records Created
        assert wf_result.document.page_count == 2
        assert len(wf_result.document.page_ids) == 2

        # STEP 7 & 8: Verify Digital Text Extraction and Persisted Fields
        extraction = wf_result.extraction
        assert extraction.total_pages == 2
        assert extraction.pages_with_digital_text == 2
        assert extraction.extraction_method == "PyMuPDF_DIGITAL_TEXT"
        assert len(extraction.pages) == 2

        p1_result = extraction.pages[0]
        assert p1_result.has_digital_text is True
        assert p1_result.text_layer_type == TextLayerType.VECTOR_NATIVE
        assert "BHARAT HEAVY INDUSTRIAL CORPORATION" in p1_result.extracted_text
        assert "Invoice No: BHIC/2026/INV-9042" in p1_result.extracted_text
        assert p1_result.extracted_fields_count > 0

        p2_result = extraction.pages[1]
        assert p2_result.has_digital_text is True
        assert "TAX COMPUTATION & CERTIFICATION SUMMARY" in p2_result.extracted_text
        assert "Rajiv Ramanathan" in p2_result.extracted_text
        assert p2_result.extracted_fields_count > 0

        # STEP 9: Retrieve Investigation and Documents through Persistence
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            retrieved_inv = uow.investigations.get_by_id(wf_result.investigation.id, org_primary)
            assert retrieved_inv is not None
            assert retrieved_inv.title == "Vendor Billing & Procurement Verification"

            docs = uow.documents.list_by_investigation(wf_result.investigation.id, org_primary)
            assert len(docs) == 1
            assert docs[0].id == wf_result.document.document_id

            pages = uow.documents.list_pages(docs[0].id, org_primary)
            assert len(pages) == 2
            assert pages[0].page_number == 1
            assert pages[1].page_number == 2

            # STEP 10: Retrieve Extracted Results from Database
            fields_p1 = uow.documents.list_extracted_fields(pages[0].id, org_primary)
            assert len(fields_p1) > 0
            assert any("BHARAT HEAVY" in f.raw_text for f in fields_p1)

            all_doc_fields = uow.documents.list_extracted_fields_by_document(
                docs[0].id, org_primary
            )
            assert len(all_doc_fields) == len(fields_p1) + len(
                uow.documents.list_extracted_fields(pages[1].id, org_primary)
            )

            # STEP 11: Verify Corresponding Audit Events in Sequence
            audit_events = uow.audit_events.list_by_investigation(
                wf_result.investigation.id, org_primary
            )
            event_types = [e.event_type for e in audit_events]
            assert AuditEventType.CASE_CREATED in event_types
            assert AuditEventType.DOC_UPLOADED in event_types
            assert AuditEventType.TEXT_EXTRACTED in event_types
            assert AuditEventType.OCR_EXTRACTED not in event_types

            # Ensure chronological order
            timestamps = [e.timestamp for e in audit_events]
            assert timestamps == sorted(timestamps)

            # STEP 12: Verify Cross-Organization Isolation
            adversary_inv = uow.investigations.get_by_id(wf_result.investigation.id, org_adversary)
            assert adversary_inv is None

            adversary_docs = uow.documents.get_by_id(wf_result.document.document_id, org_adversary)
            assert adversary_docs is None

            # Cross-organization access to other tenant's IDs strictly raises TenantIsolationError
            with pytest.raises(TenantIsolationError):
                uow.documents.list_by_investigation(wf_result.investigation.id, org_adversary)

            with pytest.raises(TenantIsolationError):
                uow.documents.list_pages(docs[0].id, org_adversary)

            with pytest.raises(TenantIsolationError):
                uow.documents.list_extracted_fields(pages[0].id, org_adversary)

            with pytest.raises(TenantIsolationError):
                uow.audit_events.list_by_investigation(wf_result.investigation.id, org_adversary)
    finally:
        engine.dispose()


def test_extraction_retry_and_repeated_extraction_is_idempotent(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify that repeating extraction on an already extracted document is idempotent.

    - Prior extracted fields are cleaned up rather than duplicated.
    - Resulting extracted field count matches exactly.
    - Audit log captures the retry event with is_retry=True and prior_fields_cleared > 0.
    """
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_primary = "org_11111111111111111111111111111111"
    now = datetime.now(UTC)

    try:
        with session_scope(session_factory) as session:
            session.add(
                OrganizationModel(
                    id=org_primary,
                    name="Global Steel Ltd",
                    industry_sector="METALS",
                    created_at=now,
                )
            )

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        workflow = DocumentProcessingWorkflow(
            investigation_service=InvestigationService(uow_factory),
            ingestion_service=DocumentIngestionService(uow_factory, storage=storage),
            extraction_service=TextExtractionService(uow_factory, storage=storage),
        )

        pdf_bytes = _generate_industrial_tax_invoice_pdf()
        wf_result = workflow.execute_new_investigation_workflow(
            organization_id=org_primary,
            investigation_title="Idempotency Test",
            reference_code="INV-IDEMP",
            filename="commercial_invoice.pdf",
            content=pdf_bytes,
            actor_id="test_runner",
        )

        doc_id = wf_result.document.document_id
        with uow_factory() as uow:
            initial_fields = uow.documents.list_extracted_fields_by_document(doc_id, org_primary)
            initial_count = len(initial_fields)
            assert initial_count > 0

        # Run extraction a second time (e.g. pipeline retry or re-processing)
        extraction_service = TextExtractionService(uow_factory, storage=storage)
        retry_result = extraction_service.extract_document_text(
            document_id=doc_id,
            organization_id=org_primary,
            actor_id="retry_runner",
        )
        assert retry_result.document_id == doc_id

        # Verify idempotency: fields count is exactly preserved, not doubled
        with uow_factory() as uow:
            after_retry_fields = uow.documents.list_extracted_fields_by_document(
                doc_id, org_primary
            )
            assert len(after_retry_fields) == initial_count

            # Verify audit trail records the retry
            audit_events = uow.audit_events.list_by_investigation(
                wf_result.investigation.id, org_primary
            )
            text_extract_events = [
                e for e in audit_events if e.event_type == AuditEventType.TEXT_EXTRACTED
            ]
            assert len(text_extract_events) == 2
            # Verify OCR_EXTRACTED is not emitted for digital text extraction
            assert not any(e.event_type == AuditEventType.OCR_EXTRACTED for e in audit_events)
            # Second event has is_retry == True
            retry_event = text_extract_events[1]
            assert retry_event.event_payload.get("is_retry") is True
            assert retry_event.event_payload.get("prior_fields_cleared") == initial_count
    finally:
        engine.dispose()
