"""Application service for secure, multi-tenant document ingestion."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image

from veritrace.application.dto.document import (
    DocumentIngestDTO,
    DocumentIngestionResultDTO,
)
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import (
    DocumentStatus,
    TextLayerType,
)
from veritrace.domain.exceptions.base import (
    CorruptedDocumentError,
    DocumentIngestionError,
    DuplicateDocumentError,
    EntityNotFoundError,
    UnsupportedFormatError,
)
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    PAGE_PREFIX,
    generate_id,
)
from veritrace.infrastructure.storage.document_storage import OriginalDocumentStorage

# Magic bytes signature definitions
PDF_MAGIC = b"%PDF-"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
TIFF_LE_MAGIC = b"II*\x00"
TIFF_BE_MAGIC = b"MM\x00*"

DEFAULT_MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def detect_mime_type(content: bytes, filename: str) -> str:
    """Identify MIME type from cryptographic file magic bytes."""
    if content.startswith(PDF_MAGIC):
        return "application/pdf"
    if content.startswith(PNG_MAGIC):
        return "image/png"
    if content.startswith(JPEG_MAGIC):
        return "image/jpeg"
    if content.startswith((TIFF_LE_MAGIC, TIFF_BE_MAGIC)):
        return "image/tiff"

    ext = Path(filename).suffix.lower()
    raise UnsupportedFormatError(
        f"Unsupported file format for '{filename}' with extension '{ext}'. "
        "Supported formats: PDF (.pdf), PNG (.png), JPEG (.jpg, .jpeg), TIFF (.tif, .tiff)"
    )


class DocumentIngestionService:
    """Manages intake, validation, storage, and initial registration of forensic documents."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork] | UnitOfWork,
        storage: OriginalDocumentStorage,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory
        self._storage = storage
        self._max_size = max_file_size_bytes

    def _get_uow(self) -> UnitOfWork:
        return self._uow_factory()

    def ingest_document(
        self,
        dto: DocumentIngestDTO,
        actor_id: str = "analyst_01",
    ) -> DocumentIngestionResultDTO:
        """Execute full intake pipeline with atomicity, validation, and compensation."""
        # 1. Resolve content
        content: bytes
        if dto.content is not None:
            content = dto.content
        elif dto.file_path is not None:
            path = Path(dto.file_path)
            if not path.is_file():
                raise DocumentIngestionError(f"Source file does not exist: {path}")
            content = path.read_bytes()
        else:
            raise DocumentIngestionError(
                "Document ingest payload must provide either content or file_path"
            )

        # 2. File size and readability validation
        file_size = len(content)
        if file_size == 0:
            raise CorruptedDocumentError(f"Document '{dto.filename}' is empty (0 bytes)")
        if file_size > self._max_size:
            raise DocumentIngestionError(
                f"File size ({file_size} bytes) exceeds limit ({self._max_size} bytes)"
            )

        # 3. Magic bytes and MIME detection
        mime_type = detect_mime_type(content, dto.filename)

        # 4. Deep format validation and readability inspection
        if mime_type == "application/pdf":
            try:
                pdf_doc = pymupdf.open(stream=content, filetype="pdf")
                page_count = len(pdf_doc)
                if page_count == 0:
                    pdf_doc.close()
                    raise CorruptedDocumentError(f"PDF document '{dto.filename}' has 0 pages")
                pdf_doc.close()
            except Exception as exc:
                raise CorruptedDocumentError(
                    f"Corrupted or unreadable PDF document '{dto.filename}': {exc}"
                ) from exc
        else:
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception as exc:
                raise CorruptedDocumentError(
                    f"Corrupted or unreadable image document '{dto.filename}': {exc}"
                ) from exc

        # 5. Compute SHA-256 hash
        file_hash = hashlib.sha256(content).hexdigest()

        # 6. Verify Investigation tenant ownership and check duplicate hash
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(dto.investigation_id, dto.organization_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"Investigation '{dto.investigation_id}' not found in '{dto.organization_id}'"
                )

            duplicates = uow.documents.get_by_hash(file_hash, dto.organization_id)
            if duplicates:
                existing = duplicates[0]
                raise DuplicateDocumentError(
                    f"Duplicate document with SHA-256 '{file_hash}' already exists in organization "
                    f"'{dto.organization_id}' (document ID: '{existing.id}')",
                    existing_document_id=existing.id,
                )

        # 7. Generate Document ID and store original file
        doc_id = generate_id(DOC_PREFIX)
        storage_path: str
        try:
            storage_path = self._storage.store_original(
                organization_id=dto.organization_id,
                investigation_id=dto.investigation_id,
                document_id=doc_id,
                filename=dto.filename,
                content=content,
            )
        except Exception as exc:
            raise DocumentIngestionError(f"Storage failed during intake: {exc}") from exc

        # 8. Create Document and DocumentPage entities with compensation guard
        page_entities: list[DocumentPage] = []
        try:
            metadata_json: dict[str, Any] = {}
            if mime_type == "application/pdf":
                pdf_doc = pymupdf.open(stream=content, filetype="pdf")
                total_pages = len(pdf_doc)
                metadata_json = dict(pdf_doc.metadata) if pdf_doc.metadata else {}

                for idx in range(total_pages):
                    page_num = idx + 1
                    pdf_page = pdf_doc[idx]
                    rect = pdf_page.rect

                    width_px = max(1, int(rect.width * 300 / 72))
                    height_px = max(1, int(rect.height * 300 / 72))
                    dims = PageDimensions(width_pixels=width_px, height_pixels=height_px, dpi=300)

                    # Store preview image
                    pix = pdf_page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    img_storage_path = self._storage.store_page_image(
                        organization_id=dto.organization_id,
                        investigation_id=dto.investigation_id,
                        document_id=doc_id,
                        page_number=page_num,
                        image_bytes=img_bytes,
                    )

                    has_text = bool(pdf_page.get_text("text").strip())
                    text_layer = (
                        TextLayerType.VECTOR_NATIVE if has_text else TextLayerType.SCANNED_RASTER
                    )

                    page_id = generate_id(PAGE_PREFIX)
                    dp = DocumentPage.create(
                        document_id=doc_id,
                        page_number=page_num,
                        dimensions=dims,
                        image_storage_path=img_storage_path,
                        page_id=page_id,
                        has_digital_text=has_text,
                        text_layer_type=text_layer,
                    )
                    page_entities.append(dp)
                pdf_doc.close()
            else:
                img = Image.open(io.BytesIO(content))
                n_frames = getattr(img, "n_frames", 1)
                metadata_json = {
                    "format": img.format,
                    "mode": img.mode,
                    "n_frames": n_frames,
                }

                for frame_idx in range(n_frames):
                    page_num = frame_idx + 1
                    img.seek(frame_idx)
                    width_px, height_px = img.size
                    dims = PageDimensions(width_pixels=width_px, height_pixels=height_px, dpi=300)

                    # Render preview PNG for this frame
                    frame_rgb = img.convert("RGB")
                    frame_buf = io.BytesIO()
                    frame_rgb.save(frame_buf, format="PNG")
                    preview_bytes = frame_buf.getvalue()

                    img_storage_path = self._storage.store_page_image(
                        organization_id=dto.organization_id,
                        investigation_id=dto.investigation_id,
                        document_id=doc_id,
                        page_number=page_num,
                        image_bytes=preview_bytes,
                    )

                    page_id = generate_id(PAGE_PREFIX)
                    dp = DocumentPage.create(
                        document_id=doc_id,
                        page_number=page_num,
                        dimensions=dims,
                        image_storage_path=img_storage_path,
                        page_id=page_id,
                        has_digital_text=False,
                        text_layer_type=TextLayerType.SCANNED_RASTER,
                    )
                    page_entities.append(dp)

                total_pages = n_frames

            # 9. Create root Document entity
            document_entity = Document.create(
                investigation_id=dto.investigation_id,
                original_filename=dto.filename,
                file_hash_sha256=file_hash,
                mime_type=mime_type,
                document_type=dto.document_type,
                document_id=doc_id,
                page_count=total_pages,
                file_size_bytes=file_size,
                storage_path=storage_path,
                metadata_json=metadata_json,
            )

            # 10. Persist atomically through UnitOfWork
            with self._get_uow() as uow:
                uow.documents.add(document_entity, dto.organization_id)
                for page in page_entities:
                    uow.documents.add_page(page, dto.organization_id)

                actor_type = (
                    ActorType.HUMAN_ANALYST
                    if "analyst" in actor_id.lower()
                    else ActorType.SYSTEM_PIPELINE
                )
                audit_event = AuditEvent.create(
                    investigation_id=dto.investigation_id,
                    event_type=AuditEventType.DOC_UPLOADED,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    event_payload={
                        "document_id": doc_id,
                        "original_filename": dto.filename,
                        "file_hash_sha256": file_hash,
                        "mime_type": mime_type,
                        "file_size_bytes": file_size,
                        "page_count": total_pages,
                        "storage_path": storage_path,
                    },
                )
                uow.audit_events.add(audit_event, dto.organization_id)

            return DocumentIngestionResultDTO(
                document_id=doc_id,
                investigation_id=dto.investigation_id,
                organization_id=dto.organization_id,
                original_filename=dto.filename,
                file_hash_sha256=file_hash,
                mime_type=mime_type,
                document_type=dto.document_type,
                page_count=total_pages,
                file_size_bytes=file_size,
                storage_path=storage_path,
                status=DocumentStatus.UPLOADED,
                created_at=document_entity.created_at,
                page_ids=[p.id for p in page_entities],
            )
        except Exception:
            self._storage.cleanup_document(
                organization_id=dto.organization_id,
                investigation_id=dto.investigation_id,
                document_id=doc_id,
            )
            raise
