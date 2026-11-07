"""Unit and integration tests for TextExtractionService with pluggable OCR and Docling backends."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pymupdf
import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.services.text_extraction_service import TextExtractionService
from veritrace.capabilities.extraction.docling_adapter import (
    DoclingDocumentResult,
    DoclingLayoutAdapter,
)
from veritrace.capabilities.extraction.ocr_engine import (
    OcrEngineProtocol,
    OcrPageResult,
)
from veritrace.capabilities.extraction.table_extractor import (
    ExtractedTable,
    TableCell,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.document import (
    DocumentStatus,
    DocumentType,
    ExtractionSourceType,
)
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox, PageDimensions
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel
from veritrace.infrastructure.persistence.models.organization import OrganizationModel
from veritrace.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from veritrace.infrastructure.storage.document_storage import OriginalDocumentStorage


@pytest.fixture
def test_env(tmp_path: Path):
    db_path = tmp_path / "test_extraction_integrations.sqlite"
    storage_dir = tmp_path / "storage"

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")

    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    now = datetime.now(UTC)

    with session_scope(session_factory) as session:
        session.add(
            OrganizationModel(
                id=org_id, name="Energy Corp", industry_sector="MANUFACTURING", created_at=now
            )
        )
        session.add(
            InvestigationModel(
                id=inv_id,
                organization_id=org_id,
                title="Audit",
                reference_code="INV-01",
                status="DRAFT",
                created_at=now,
                updated_at=now,
            )
        )

    def uow_factory():
        return SqlAlchemyUnitOfWork(session_factory)

    return {
        "uow_factory": uow_factory,
        "storage": storage,
        "org_id": org_id,
        "inv_id": inv_id,
    }


def test_text_extraction_with_pluggable_ocr_engine(test_env):
    """Verify raster document extraction routes to OCR engine and persists fields."""
    uow_factory = test_env["uow_factory"]
    storage = test_env["storage"]
    org_id = test_env["org_id"]
    inv_id = test_env["inv_id"]

    # 1. Setup mock OCR engine
    mock_ocr = MagicMock(spec=OcrEngineProtocol)
    mock_ocr.is_available.return_value = True

    dummy_tokens = [
        ExtractedToken(
            token_id=generate_id("tok_"),
            text="TOTAL",
            raw_text="TOTAL",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.15, xmax=0.3),
            confidence=0.98,
            page_number=1,
            source_type=ExtractionSourceType.OCR,
        ),
        ExtractedToken(
            token_id=generate_id("tok_"),
            text="450000.00",
            raw_text="450000.00",
            normalized_bbox=NormalizedBoundingBox(ymin=0.1, xmin=0.35, ymax=0.15, xmax=0.6),
            confidence=0.96,
            page_number=1,
            source_type=ExtractionSourceType.OCR,
        ),
    ]
    mock_ocr.extract_page_ocr.return_value = OcrPageResult(
        page_number=1,
        dimensions=PageDimensions(width_pixels=600, height_pixels=800, dpi=300),
        full_text="TOTAL 450000.00",
        tokens=dummy_tokens,
        mean_confidence=0.97,
        ocr_engine="MockPaddleOCR",
        ocr_model_version="v4",
    )

    service = TextExtractionService(
        uow_factory=uow_factory,
        storage=storage,
        ocr_engine=mock_ocr,
    )

    # 2. Store dummy image and record document
    img_bytes = b"fake_png_header_and_data_bytes"
    doc_id = generate_id("doc_")
    stored_path = storage.store_original(
        organization_id=org_id,
        investigation_id=inv_id,
        document_id=doc_id,
        filename="invoice_scan.png",
        content=img_bytes,
    )

    doc_entity = Document.create(
        document_id=doc_id,
        investigation_id=inv_id,
        original_filename="invoice_scan.png",
        file_hash_sha256=hashlib.sha256(img_bytes).hexdigest(),
        mime_type="image/png",
        document_type=DocumentType.COMMERCIAL_INVOICE,
        file_size_bytes=len(img_bytes),
        storage_path=stored_path,
        page_count=1,
    )
    page_entity = DocumentPage.create(
        page_id=generate_id("page_"),
        document_id=doc_id,
        page_number=1,
        dimensions=PageDimensions(width_pixels=600, height_pixels=800, dpi=300),
        image_storage_path="pages/scan_p1.png",
    )

    with uow_factory() as uow:
        uow.documents.add(doc_entity, org_id)
        uow.documents.add_page(page_entity, org_id)

    # 3. Execute extraction
    result = service.extract_document_text(doc_id, org_id)

    assert result.extraction_method == "OCR_MockPaddleOCR"
    assert len(result.pages) == 1
    assert result.pages[0].extracted_fields_count == 2
    assert "TOTAL 450000.00" in result.pages[0].extracted_text

    # 4. Verify fields persisted in relational store
    with uow_factory() as uow:
        persisted_fields = uow.documents.list_extracted_fields_by_document(doc_id, org_id)
        assert len(persisted_fields) == 2
        assert any(
            f.field_value == "TOTAL" and f.ocr_engine == "MockPaddleOCR" for f in persisted_fields
        )
        assert any(f.field_value == "450000.00" for f in persisted_fields)

        doc = uow.documents.get_by_id(doc_id, org_id)
        assert doc.status == DocumentStatus.PROCESSED


def test_text_extraction_with_docling_layout_adapter(test_env):
    """Verify PDF extraction integrates Docling tables and persists structured fields."""
    uow_factory = test_env["uow_factory"]
    storage = test_env["storage"]
    org_id = test_env["org_id"]
    inv_id = test_env["inv_id"]

    # 1. Setup mock Docling layout adapter
    mock_docling = MagicMock(spec=DoclingLayoutAdapter)
    mock_docling.is_available.return_value = True

    sample_table = ExtractedTable(
        table_index=0,
        page_number=1,
        normalized_bbox=NormalizedBoundingBox(ymin=0.2, xmin=0.1, ymax=0.8, xmax=0.9),
        headers=["Item", "Qty", "Price"],
        rows=[["Steel Tubes", "10", "45000.00"]],
        cells=[
            TableCell(
                row_index=0,
                col_index=0,
                text="Steel Tubes",
                normalized_bbox=NormalizedBoundingBox(ymin=0.25, xmin=0.1, ymax=0.3, xmax=0.4),
            ),
            TableCell(
                row_index=0,
                col_index=1,
                text="10",
                normalized_bbox=NormalizedBoundingBox(ymin=0.25, xmin=0.42, ymax=0.3, xmax=0.5),
            ),
            TableCell(
                row_index=0,
                col_index=2,
                text="45000.00",
                normalized_bbox=NormalizedBoundingBox(ymin=0.25, xmin=0.52, ymax=0.3, xmax=0.8),
            ),
        ],
    )
    mock_docling.parse_document.return_value = DoclingDocumentResult(
        filename="po_101.pdf",
        page_count=1,
        elements=[],
        tables=[sample_table],
        reading_order_text="Steel Tubes 10 45000.00",
        is_fallback=False,
    )

    service = TextExtractionService(
        uow_factory=uow_factory,
        storage=storage,
        layout_adapter=mock_docling,
    )

    # 2. Create minimal digital PDF
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Purchase Order PO-101", fontsize=12)
    pdf_bytes = bytes(doc.tobytes())
    doc.close()

    doc_id = generate_id("doc_")
    stored_path = storage.store_original(
        organization_id=org_id,
        investigation_id=inv_id,
        document_id=doc_id,
        filename="po_101.pdf",
        content=pdf_bytes,
    )

    doc_entity = Document.create(
        document_id=doc_id,
        investigation_id=inv_id,
        original_filename="po_101.pdf",
        file_hash_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        mime_type="application/pdf",
        document_type=DocumentType.PURCHASE_ORDER,
        file_size_bytes=len(pdf_bytes),
        storage_path=stored_path,
        page_count=1,
    )
    page_entity = DocumentPage.create(
        page_id=generate_id("page_"),
        document_id=doc_id,
        page_number=1,
        dimensions=PageDimensions(width_pixels=595, height_pixels=842, dpi=72),
        image_storage_path="pages/po_p1.png",
    )

    with uow_factory() as uow:
        uow.documents.add(doc_entity, org_id)
        uow.documents.add_page(page_entity, org_id)

    # 3. Execute extraction
    result = service.extract_document_text(doc_id, org_id)
    assert result.pages[0].extracted_fields_count > 0

    # 4. Verify table fields persisted
    with uow_factory() as uow:
        fields = uow.documents.list_extracted_fields_by_document(doc_id, org_id)
        # Should contain digital vector block fields AND docling table fields
        assert any("table" in f.field_name and f.field_value == "Steel Tubes" for f in fields)
        assert any("table" in f.field_name and f.field_value == "45000.00" for f in fields)
