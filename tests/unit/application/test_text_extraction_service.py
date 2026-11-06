"""Unit tests for TextExtractionService audit events and lifecycle semantics."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pymupdf
import pytest
from alembic import command
from alembic.config import Config

from veritrace.application.services.text_extraction_service import (
    TextExtractionService,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.document import DocumentType, TextLayerType
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    session_scope,
)
from veritrace.infrastructure.persistence.models.investigation import (
    InvestigationModel,
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
    return tmp_path / "test_extraction_service.sqlite"


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


def _make_pdf(text: str = "Tax Invoice #90214") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), text, fontsize=12)
    buf = doc.tobytes()
    doc.close()
    return bytes(buf)


def test_extract_digital_pdf_records_text_extracted_audit_event(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify digital PDF extraction records TEXT_EXTRACTED audit event, not OCR_EXTRACTED."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    now = datetime.now(UTC)

    try:
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

        pdf_bytes = _make_pdf("Delivery Challan DC-4412")
        doc_id = generate_id("doc_")
        stored_path = storage.store_original(
            organization_id=org_id,
            investigation_id=inv_id,
            document_id=doc_id,
            filename="dc_4412.pdf",
            content=pdf_bytes,
        )

        doc_entity = Document.create(
            document_id=doc_id,
            investigation_id=inv_id,
            original_filename="dc_4412.pdf",
            file_hash_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.DELIVERY_CHALLAN,
            page_count=1,
            file_size_bytes=len(pdf_bytes),
            storage_path=stored_path,
        )
        page_entity = DocumentPage(
            id=generate_id("page_"),
            document_id=doc_entity.id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=595, height_pixels=842, dpi=300),
            image_storage_path=stored_path,
            has_digital_text=True,
            text_layer_type=TextLayerType.VECTOR_NATIVE,
        )

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        with uow_factory() as uow:
            uow.documents.add(doc_entity, org_id)
            uow.documents.add_page(page_entity, org_id)

        service = TextExtractionService(uow_factory, storage=storage)
        result = service.extract_document_text(
            document_id=doc_entity.id,
            organization_id=org_id,
            actor_id="analyst_vikram",
        )

        assert result.document_id == doc_entity.id
        assert result.pages_with_digital_text == 1

        # Verify audit trail contains TEXT_EXTRACTED and does not contain OCR_EXTRACTED
        with uow_factory() as uow:
            audit_events = uow.audit_events.list_by_investigation(inv_id, org_id)
            event_types = [e.event_type for e in audit_events]
            assert AuditEventType.TEXT_EXTRACTED in event_types
            assert AuditEventType.OCR_EXTRACTED not in event_types

            text_events = [e for e in audit_events if e.event_type == AuditEventType.TEXT_EXTRACTED]
            assert len(text_events) == 1
            payload = text_events[0].event_payload
            assert payload["document_id"] == doc_entity.id
            assert payload["is_retry"] is False
            assert payload["prior_fields_cleared"] == 0
            assert payload["extraction_method"] == "PyMuPDF_DIGITAL_TEXT"
            assert payload["fields_persisted"] > 0
    finally:
        engine.dispose()


def test_extract_digital_pdf_retry_records_text_extracted_audit_event_with_retry_flag(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify repeated extraction emits second TEXT_EXTRACTED event with is_retry=True."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    now = datetime.now(UTC)

    try:
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

        pdf_bytes = _make_pdf("Bill of Lading BOL-990")
        doc_id = generate_id("doc_")
        stored_path = storage.store_original(
            organization_id=org_id,
            investigation_id=inv_id,
            document_id=doc_id,
            filename="bol_990.pdf",
            content=pdf_bytes,
        )

        doc_entity = Document.create(
            document_id=doc_id,
            investigation_id=inv_id,
            original_filename="bol_990.pdf",
            file_hash_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.COMMERCIAL_RECORD,
            page_count=1,
            file_size_bytes=len(pdf_bytes),
            storage_path=stored_path,
        )
        page_entity = DocumentPage(
            id=generate_id("page_"),
            document_id=doc_entity.id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=595, height_pixels=842, dpi=300),
            image_storage_path=stored_path,
            has_digital_text=True,
            text_layer_type=TextLayerType.VECTOR_NATIVE,
        )

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        with uow_factory() as uow:
            uow.documents.add(doc_entity, org_id)
            uow.documents.add_page(page_entity, org_id)

        service = TextExtractionService(uow_factory, storage=storage)

        # First extraction
        service.extract_document_text(
            document_id=doc_entity.id,
            organization_id=org_id,
            actor_id="analyst_1",
        )

        with uow_factory() as uow:
            initial_fields = uow.documents.list_extracted_fields_by_document(doc_entity.id, org_id)
            initial_count = len(initial_fields)
            assert initial_count > 0

        # Second extraction (retry)
        service.extract_document_text(
            document_id=doc_entity.id,
            organization_id=org_id,
            actor_id="analyst_retry",
        )

        with uow_factory() as uow:
            audit_events = uow.audit_events.list_by_investigation(inv_id, org_id)
            text_events = [e for e in audit_events if e.event_type == AuditEventType.TEXT_EXTRACTED]
            assert len(text_events) == 2
            assert not any(e.event_type == AuditEventType.OCR_EXTRACTED for e in audit_events)

            # Check retry payload
            retry_event = text_events[1]
            assert retry_event.event_payload["is_retry"] is True
            assert retry_event.event_payload["prior_fields_cleared"] == initial_count
            assert retry_event.actor_id == "analyst_retry"
    finally:
        engine.dispose()


def test_extract_raster_image_does_not_emit_text_or_ocr_audit_event(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify raster image intake returns NOOP and emits no extraction audit events."""
    command.upgrade(alembic_config, "head")
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    session_factory = create_session_factory(engine)
    storage = OriginalDocumentStorage(storage_root=storage_dir, allow_workspace_storage=True)

    org_id = "org_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    inv_id = "inv_aaaaaaaaaaaaaaaaaaaaaaaaaaaa0001"
    now = datetime.now(UTC)

    try:
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

        fake_bytes = b"\x89PNG\r\n\x1a\nfake_image_bytes"
        doc_id = generate_id("doc_")
        stored_path = storage.store_original(
            organization_id=org_id,
            investigation_id=inv_id,
            document_id=doc_id,
            filename="receipt.png",
            content=fake_bytes,
        )

        doc_entity = Document.create(
            document_id=doc_id,
            investigation_id=inv_id,
            original_filename="receipt.png",
            file_hash_sha256=hashlib.sha256(fake_bytes).hexdigest(),
            mime_type="image/png",
            document_type=DocumentType.COMMERCIAL_RECORD,
            page_count=1,
            file_size_bytes=len(fake_bytes),
            storage_path=stored_path,
        )
        page_entity = DocumentPage(
            id=generate_id("page_"),
            document_id=doc_entity.id,
            page_number=1,
            dimensions=PageDimensions(width_pixels=200, height_pixels=200, dpi=300),
            image_storage_path=stored_path,
            has_digital_text=False,
            text_layer_type=TextLayerType.SCANNED_RASTER,
        )

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        with uow_factory() as uow:
            uow.documents.add(doc_entity, org_id)
            uow.documents.add_page(page_entity, org_id)

        service = TextExtractionService(uow_factory, storage=storage)
        result = service.extract_document_text(
            document_id=doc_entity.id,
            organization_id=org_id,
        )

        assert result.extraction_method == "IMAGE_RASTER_NOOP"
        assert result.pages_with_digital_text == 0
        assert len(result.pages) == 1
        assert result.pages[0].has_digital_text is False
        assert result.pages[0].text_layer_type == TextLayerType.SCANNED_RASTER
        assert result.pages[0].extracted_fields_count == 0

        # Verify neither TEXT_EXTRACTED nor OCR_EXTRACTED audit events were created
        with uow_factory() as uow:
            audit_events = uow.audit_events.list_by_investigation(inv_id, org_id)
            event_types = [e.event_type for e in audit_events]
            assert AuditEventType.TEXT_EXTRACTED not in event_types
            assert AuditEventType.OCR_EXTRACTED not in event_types
    finally:
        engine.dispose()
