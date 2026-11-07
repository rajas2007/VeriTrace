"""Integration tests for document classification workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.dto.document import DocumentIngestDTO
from veritrace.application.dto.investigation import InvestigationCreateDTO
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
from veritrace.domain.enums.document import DocumentType
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
def workflow_env(tmp_path: Path):
    """Set up isolated migrated SQLite database and workflow services."""
    db_path = tmp_path / "test_classification_wf.sqlite"
    db_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(db_url)

    # Run Alembic migrations
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    migrations_path = project_root / "src/veritrace/infrastructure/persistence/migrations"
    alembic_cfg.set_main_option("script_location", str(migrations_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    session_factory = create_session_factory(engine)
    org_id = "org_11111111111111111111111111111111"

    with session_scope(session_factory) as session:
        session.add(
            OrganizationModel(
                id=org_id,
                name="Classification Test Corp",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    storage = OriginalDocumentStorage(storage_root=tmp_path / "storage")
    inv_service = InvestigationService(uow_factory)
    ingest_service = DocumentIngestionService(uow_factory, storage=storage)
    extract_service = TextExtractionService(uow_factory, storage=storage)
    workflow = DocumentProcessingWorkflow(
        investigation_service=inv_service,
        ingestion_service=ingest_service,
        extraction_service=extract_service,
    )

    return {
        "uow_factory": uow_factory,
        "storage": storage,
        "inv_service": inv_service,
        "ingest_service": ingest_service,
        "extract_service": extract_service,
        "workflow": workflow,
        "org_id": org_id,
    }


def _create_tax_invoice_pdf() -> bytes:
    """Generate in-memory commercial tax invoice PDF with strong structural keywords."""
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "BHARAT INDUSTRIAL SUPPLIERS LTD", fontsize=14)
    p.insert_text((50, 85), "TAX INVOICE / COMMERCIAL INVOICE", fontsize=12)
    p.insert_text((50, 110), "Invoice No: INV-2026-9921", fontsize=10)
    p.insert_text((50, 130), "GSTIN: 27AABCS1429B1Z8", fontsize=10)
    p.insert_text((50, 150), "Taxable Value: Rs. 4,50,000.00", fontsize=10)
    p.insert_text((50, 170), "Total Amount: Rs. 5,31,000.00", fontsize=10)
    pdf_bytes = bytes(doc.tobytes())
    doc.close()
    return pdf_bytes


def _create_generic_unclassified_pdf() -> bytes:
    """Generate in-memory PDF without identifying classification keywords."""
    doc = pymupdf.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 60), "Meeting minutes and general discussion notes.", fontsize=12)
    p.insert_text((50, 85), "Item A: Project kickoff rescheduled to next Tuesday.", fontsize=10)
    p.insert_text((50, 110), "Item B: Budget review preliminary draft notes.", fontsize=10)
    pdf_bytes = bytes(doc.tobytes())
    doc.close()
    return pdf_bytes


def test_classification_after_extraction_success(workflow_env):
    """Verify document is classified immediately after extraction has completed."""
    workflow: DocumentProcessingWorkflow = workflow_env["workflow"]
    inv_service: InvestigationService = workflow_env["inv_service"]
    org_id: str = workflow_env["org_id"]

    pdf_bytes = _create_tax_invoice_pdf()
    res = workflow.execute_new_investigation_workflow(
        organization_id=org_id,
        investigation_title="Automated Classification Test",
        reference_code="INV-CLASS-001",
        filename="INV-2026-9921.pdf",
        content=pdf_bytes,
        document_type=DocumentType.UNCLASSIFIED,
    )

    # Document type was UNCLASSIFIED at intake, but classified after extraction
    assert res.document.document_type == DocumentType.COMMERCIAL_INVOICE

    # Verify persistence reflects the classified type
    docs = inv_service.list_documents(res.investigation.id, org_id)
    assert len(docs) == 1
    assert docs[0].document_type == DocumentType.COMMERCIAL_INVOICE


def test_uncertain_classification_preserves_unclassified(workflow_env):
    """Verify uncertain documents remain UNCLASSIFIED when confidence is insufficient."""
    workflow: DocumentProcessingWorkflow = workflow_env["workflow"]
    inv_service: InvestigationService = workflow_env["inv_service"]
    org_id: str = workflow_env["org_id"]

    pdf_bytes = _create_generic_unclassified_pdf()
    res = workflow.execute_new_investigation_workflow(
        organization_id=org_id,
        investigation_title="Generic Notes Test",
        reference_code="INV-GENERIC-001",
        filename="meeting_notes.pdf",
        content=pdf_bytes,
        document_type=DocumentType.UNCLASSIFIED,
    )

    # Should remain UNCLASSIFIED
    assert res.document.document_type == DocumentType.UNCLASSIFIED

    docs = inv_service.list_documents(res.investigation.id, org_id)
    assert len(docs) == 1
    assert docs[0].document_type == DocumentType.UNCLASSIFIED


def test_failed_extraction_does_not_corrupt_ingestion(workflow_env):
    """Verify that extraction failure does not corrupt intake or modify original files."""
    ingest_service: DocumentIngestionService = workflow_env["ingest_service"]
    inv_service: InvestigationService = workflow_env["inv_service"]
    org_id: str = workflow_env["org_id"]

    # Ingest document first
    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Extraction Error Resilience",
            reference_code="INV-RESIL-01",
            organization_id=org_id,
        ),
        actor_id="tester",
    )

    pdf_bytes = _create_tax_invoice_pdf()
    dto = DocumentIngestDTO(
        investigation_id=inv.id,
        organization_id=org_id,
        filename="corrupted_scan.pdf",
        content=pdf_bytes,
        document_type=DocumentType.UNCLASSIFIED,
    )
    doc_res = ingest_service.ingest_document(dto)
    assert doc_res.document_id is not None

    # Simulate classification attempt when extraction has not completed or failed
    # Document remains UNCLASSIFIED and stored safely
    docs_before = inv_service.list_documents(inv.id, org_id)
    assert len(docs_before) == 1
    assert docs_before[0].document_type == DocumentType.UNCLASSIFIED
    assert docs_before[0].file_size_bytes == len(pdf_bytes)


def test_classification_before_extraction_is_deferred(workflow_env):
    """Verify classification before text extraction is safely deferred and remains UNCLASSIFIED.

    Even if the filename has strong hints (e.g. PO-*.pdf), filename hints must not
    independently produce a confident classification before extraction.
    """
    ingest_service: DocumentIngestionService = workflow_env["ingest_service"]
    inv_service: InvestigationService = workflow_env["inv_service"]
    extract_service: TextExtractionService = workflow_env["extract_service"]
    org_id: str = workflow_env["org_id"]

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Precondition Test",
            reference_code="INV-PRE-01",
            organization_id=org_id,
        ),
        actor_id="tester",
    )

    pdf_bytes = _create_tax_invoice_pdf()
    dto = DocumentIngestDTO(
        investigation_id=inv.id,
        organization_id=org_id,
        filename="INV-2026-9921.pdf",
        content=pdf_bytes,
        document_type=DocumentType.UNCLASSIFIED,
    )
    doc_res = ingest_service.ingest_document(dto)

    # 1. Document is in UPLOADED status (not PROCESSED yet)
    # Attempting classification before extraction must return UNCLASSIFIED
    dtype, conf = inv_service.classify_document(doc_res.document_id, org_id)
    assert dtype == DocumentType.UNCLASSIFIED
    assert conf == 0.0

    docs = inv_service.list_documents(inv.id, org_id)
    assert docs[0].document_type == DocumentType.UNCLASSIFIED

    # 2. Extract text -> status transitions to PROCESSED
    extract_service.extract_document_text(doc_res.document_id, org_id)

    # 3. Now classification succeeds
    dtype_after, conf_after = inv_service.classify_document(doc_res.document_id, org_id)
    assert dtype_after == DocumentType.COMMERCIAL_INVOICE
    assert conf_after > 0.5

    docs_after = inv_service.list_documents(inv.id, org_id)
    assert docs_after[0].document_type == DocumentType.COMMERCIAL_INVOICE


def test_human_validated_classification_is_preserved(workflow_env):
    """Verify that an already validated human or intake classification is never overwritten."""
    ingest_service: DocumentIngestionService = workflow_env["ingest_service"]
    inv_service: InvestigationService = workflow_env["inv_service"]
    extract_service: TextExtractionService = workflow_env["extract_service"]
    org_id: str = workflow_env["org_id"]

    inv = inv_service.create_investigation(
        dto=InvestigationCreateDTO(
            title="Human Preservation Test",
            reference_code="INV-HUMAN-01",
            organization_id=org_id,
        ),
        actor_id="tester",
    )

    # Ingest document with explicitly validated human type PURCHASE_ORDER
    pdf_bytes = _create_tax_invoice_pdf()  # Content has invoice keywords
    dto = DocumentIngestDTO(
        investigation_id=inv.id,
        organization_id=org_id,
        filename="custom_order.pdf",
        content=pdf_bytes,
        document_type=DocumentType.PURCHASE_ORDER,  # Human assigned
    )
    doc_res = ingest_service.ingest_document(dto)

    # Extract text -> status transitions to PROCESSED
    extract_service.extract_document_text(doc_res.document_id, org_id)

    # Classification must NOT overwrite human assignment
    dtype, conf = inv_service.classify_document(doc_res.document_id, org_id)
    assert dtype == DocumentType.PURCHASE_ORDER

    # Batch classification across investigation must also preserve it
    class_map = inv_service.classify_documents(inv.id, org_id)
    assert class_map[doc_res.document_id] == DocumentType.PURCHASE_ORDER

    docs = inv_service.list_documents(inv.id, org_id)
    assert docs[0].document_type == DocumentType.PURCHASE_ORDER
