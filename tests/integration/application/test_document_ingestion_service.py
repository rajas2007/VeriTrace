"""Integration tests for DocumentIngestionService with real SQLite and filesystem."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pymupdf
import pytest
from alembic import command
from alembic.config import Config
from PIL import Image

from veritrace.application.dto.document import DocumentIngestDTO
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.document import DocumentStatus, DocumentType
from veritrace.domain.exceptions.base import (
    CorruptedDocumentError,
    DuplicateDocumentError,
    UnsupportedFormatError,
)
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
    return tmp_path / "test_doc_ingest.sqlite"


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


def _make_pdf(text: str = "Test Industrial Document Invoice") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), text, fontsize=12)
    buf = doc.tobytes()
    doc.close()
    return bytes(buf)


def _make_image(fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (200, 200), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_multiframe_tiff(frames: int = 3) -> bytes:
    images = [
        Image.new("RGB", (200, 200), color=("red" if i == 0 else "green" if i == 1 else "blue"))
        for i in range(frames)
    ]
    buf = io.BytesIO()
    images[0].save(
        buf,
        format="TIFF",
        save_all=True,
        append_images=images[1:],
    )
    return buf.getvalue()


def test_ingest_valid_pdf_creates_records_and_audit(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify ingesting a valid PDF creates Document, DocumentPage, stored file, and AuditEvent."""
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
                    title="Invoice Audit",
                    reference_code="INV-ING-01",
                    status="DRAFT",
                    created_at=now,
                    updated_at=now,
                )
            )

        service = DocumentIngestionService(
            lambda: SqlAlchemyUnitOfWork(session_factory), storage=storage
        )
        pdf_bytes = _make_pdf("Purchase Order 90021")

        dto = DocumentIngestDTO(
            investigation_id=inv_id,
            organization_id=org_id,
            filename="po_90021.pdf",
            content=pdf_bytes,
            document_type=DocumentType.PURCHASE_ORDER,
        )

        res = service.ingest_document(dto, actor_id="analyst_priya")

        assert res.document_id.startswith("doc_")
        assert res.page_count == 1
        assert res.mime_type == "application/pdf"
        assert res.status == DocumentStatus.UPLOADED
        assert len(res.page_ids) == 1

        # Verify filesystem storage
        assert Path(res.storage_path).is_file()
        assert storage.read_original(res.storage_path) == pdf_bytes

        # Verify DB records via fresh context
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            doc = uow.documents.get_by_id(res.document_id, org_id)
            assert doc is not None
            assert doc.original_filename == "po_90021.pdf"
            pages = uow.documents.list_pages(res.document_id, org_id)
            assert len(pages) == 1
            assert pages[0].has_digital_text is True

            events = uow.audit_events.list_by_investigation(inv_id, org_id)
            upload_events = [e for e in events if e.event_type == AuditEventType.DOC_UPLOADED]
            assert len(upload_events) == 1
            assert upload_events[0].actor_id == "analyst_priya"
    finally:
        engine.dispose()


def test_ingest_valid_png_jpeg_tiff_images(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify ingesting PNG, JPEG, and TIFF images creates single-page records."""
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
                    title="Image Audit",
                    reference_code="INV-IMG-01",
                    status="DRAFT",
                    created_at=now,
                    updated_at=now,
                )
            )

        service = DocumentIngestionService(
            lambda: SqlAlchemyUnitOfWork(session_factory), storage=storage
        )

        for fmt, ext, mime in [
            ("PNG", "png", "image/png"),
            ("JPEG", "jpg", "image/jpeg"),
            ("TIFF", "tiff", "image/tiff"),
        ]:
            img_bytes = _make_image(fmt)
            dto = DocumentIngestDTO(
                investigation_id=inv_id,
                organization_id=org_id,
                filename=f"scan.{ext}",
                content=img_bytes,
            )
            res = service.ingest_document(dto)
            assert res.mime_type == mime
            assert res.page_count == 1
            assert Path(res.storage_path).is_file()
    finally:
        engine.dispose()


def test_ingest_corrupted_and_unsupported_files(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify corrupted, empty, or unsupported format files are rejected."""
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

        service = DocumentIngestionService(
            lambda: SqlAlchemyUnitOfWork(session_factory), storage=storage
        )

        # 1. Empty file
        with pytest.raises(CorruptedDocumentError, match="is empty"):
            service.ingest_document(
                DocumentIngestDTO(
                    investigation_id=inv_id,
                    organization_id=org_id,
                    filename="empty.pdf",
                    content=b"",
                )
            )

        # 2. Unsupported format (.exe, .zip)
        with pytest.raises(UnsupportedFormatError, match="Unsupported file format"):
            service.ingest_document(
                DocumentIngestDTO(
                    investigation_id=inv_id,
                    organization_id=org_id,
                    filename="app.exe",
                    content=b"MZ\x90\x00not_a_doc",
                )
            )

        # 3. Corrupted PDF header
        with pytest.raises(CorruptedDocumentError):
            service.ingest_document(
                DocumentIngestDTO(
                    investigation_id=inv_id,
                    organization_id=org_id,
                    filename="broken.pdf",
                    content=b"%PDF-1.4\nCorrupted binary without EOF",
                )
            )
    finally:
        engine.dispose()


def test_ingest_duplicate_hash_rejected(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify duplicate document hash within the organization raises DuplicateDocumentError."""
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

        service = DocumentIngestionService(
            lambda: SqlAlchemyUnitOfWork(session_factory), storage=storage
        )
        pdf_bytes = _make_pdf("Invoice #5512")

        # Ingest first copy
        res1 = service.ingest_document(
            DocumentIngestDTO(
                investigation_id=inv_id,
                organization_id=org_id,
                filename="original.pdf",
                content=pdf_bytes,
            )
        )
        assert res1.document_id is not None

        # Attempt to ingest duplicate copy
        with pytest.raises(DuplicateDocumentError) as exc_info:
            service.ingest_document(
                DocumentIngestDTO(
                    investigation_id=inv_id,
                    organization_id=org_id,
                    filename="duplicate.pdf",
                    content=pdf_bytes,
                )
            )
        assert exc_info.value.existing_document_id == res1.document_id
    finally:
        engine.dispose()


def test_storage_cleanup_compensation_on_database_failure(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify that if database commit fails, the stored file is deleted by compensation."""
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

        # Mock UOW to simulate database crash on document addition
        mock_uow = MagicMock()
        mock_uow.__enter__.return_value = mock_uow
        mock_uow.investigations.get_by_id.return_value = MagicMock()
        mock_uow.documents.get_by_hash.return_value = []
        mock_uow.documents.add.side_effect = RuntimeError("Simulated DB connection failure")

        service = DocumentIngestionService(lambda: mock_uow, storage=storage)
        pdf_bytes = _make_pdf("Compensation Test")

        with pytest.raises(RuntimeError, match="Simulated DB connection failure"):
            service.ingest_document(
                DocumentIngestDTO(
                    investigation_id=inv_id,
                    organization_id=org_id,
                    filename="compensate.pdf",
                    content=pdf_bytes,
                )
            )

        # Verify no orphaned files remain in storage directory
        doc_storage_files = list(storage_dir.rglob("compensate.pdf"))
        assert len(doc_storage_files) == 0
    finally:
        engine.dispose()


def test_ingest_multiframe_tiff_creates_multiple_pages_and_previews(
    db_path: Path, storage_dir: Path, alembic_config: Config
) -> None:
    """Verify ingesting a multi-frame TIFF creates DocumentPage and preview for each frame."""
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

        service = DocumentIngestionService(
            lambda: SqlAlchemyUnitOfWork(session_factory), storage=storage
        )
        tiff_bytes = _make_multiframe_tiff(frames=3)

        result = service.ingest_document(
            DocumentIngestDTO(
                investigation_id=inv_id,
                organization_id=org_id,
                filename="scanned_batch.tiff",
                content=tiff_bytes,
            )
        )

        assert result.page_count == 3
        assert result.status == DocumentStatus.UPLOADED.value

        # Verify pages in database and previews in storage
        uow = SqlAlchemyUnitOfWork(session_factory)
        with uow:
            doc = uow.documents.get_by_id(result.document_id, org_id)
            assert doc is not None
            assert doc.page_count == 3
            pages = uow.documents.list_pages(result.document_id, org_id)
            assert len(pages) == 3
            for i, page in enumerate(pages, start=1):
                assert page.page_number == i
                assert page.image_storage_path is not None
                preview_file = Path(page.image_storage_path)
                assert preview_file.is_file()
                assert preview_file.stat().st_size > 0
    finally:
        engine.dispose()
