"""Application service for digital text extraction and result persistence."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from veritrace.application.dto.extraction import (
    DocumentExtractionResultDTO,
    PageExtractionResultDTO,
)
from veritrace.capabilities.extraction.pdf_text_extractor import (
    DocumentDigitalExtraction,
    PdfDigitalTextExtractor,
)
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import (
    DocumentStatus,
    TextLayerType,
)
from veritrace.domain.exceptions.base import (
    DocumentExtractionError,
    EntityNotFoundError,
)
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.infrastructure.storage.document_storage import OriginalDocumentStorage


class TextExtractionService:
    """Coordinates digital text extraction from documents, persistence, and audit logging."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork] | UnitOfWork,
        storage: OriginalDocumentStorage,
        extractor: PdfDigitalTextExtractor | None = None,
    ) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory
        self._storage = storage
        self._extractor = extractor or PdfDigitalTextExtractor()

    def _get_uow(self) -> UnitOfWork:
        return self._uow_factory()

    def extract_document_text(
        self,
        document_id: str,
        organization_id: str,
        actor_id: str = "system_pipeline",
    ) -> DocumentExtractionResultDTO:
        """Extract digital text from a document page-by-page and persist structured tokens."""
        # 1. Fetch document and verify tenant boundary
        with self._get_uow() as uow:
            doc = uow.documents.get_by_id(document_id, organization_id)
            if doc is None:
                raise EntityNotFoundError(
                    f"Document '{document_id}' not found in organization '{organization_id}'"
                )

            inv_id = doc.investigation_id
            storage_path = doc.storage_path
            mime_type = doc.mime_type
            pages = uow.documents.list_pages(document_id, organization_id)

        # 2. Handle non-PDF image files
        if mime_type != "application/pdf":
            page_dtos: list[PageExtractionResultDTO] = []
            for p in pages:
                page_dtos.append(
                    PageExtractionResultDTO(
                        page_id=p.id,
                        page_number=p.page_number,
                        has_digital_text=False,
                        text_layer_type=TextLayerType.SCANNED_RASTER,
                        extracted_text="",
                        word_count=0,
                        width_pixels=p.width_pixels,
                        height_pixels=p.height_pixels,
                        dpi=p.dpi,
                        extracted_fields_count=0,
                        warnings=[f"Image format '{mime_type}' has no digital vector text."],
                    )
                )
            return DocumentExtractionResultDTO(
                document_id=document_id,
                investigation_id=inv_id,
                total_pages=len(pages),
                pages_with_digital_text=0,
                extraction_method="IMAGE_RASTER_NOOP",
                timestamp=datetime.now(UTC),
                pages=page_dtos,
                warnings=[f"File '{doc.original_filename}' is a raster image; no vector text."],
            )

        # 3. Read raw PDF binary from immutable storage enforcing tenant containment
        pdf_bytes = self._storage.read_original_for_tenant(organization_id, storage_path)

        # 4. Extract digital text using PyMuPDF capability
        extraction: DocumentDigitalExtraction
        try:
            extraction = self._extractor.extract(pdf_bytes)
        except Exception as exc:
            raise DocumentExtractionError(
                f"Digital text extraction failed for document '{document_id}': {exc}"
            ) from exc

        # 5. Persist extracted fields and update document status atomically
        page_by_num = {p.page_number: p for p in pages}
        page_dtos = []

        with self._get_uow() as uow:
            # Idempotent cleanup: delete existing extracted fields to avoid duplicates on retries
            deleted_prior = uow.documents.delete_extracted_fields_by_document(
                document_id, organization_id
            )
            is_retry = deleted_prior > 0 or doc.status == DocumentStatus.PROCESSED

            for page_extract in extraction.pages:
                page_entity = page_by_num.get(page_extract.page_number)
                if page_entity is None:
                    continue

                page_fields_count = 0
                for block in page_extract.blocks:
                    fid = generate_id("fld_")
                    field_entity = ExtractedField.create(
                        field_id=fid,
                        page_id=page_entity.id,
                        field_name=block.field_name,
                        field_value=block.field_value,
                        raw_text=block.raw_text,
                        confidence=block.confidence,
                        normalized_bbox=block.normalized_bbox,
                        extraction_source=block.extraction_source,
                        ocr_engine=block.ocr_engine,
                        ocr_model_version=block.ocr_model_version,
                    )
                    uow.documents.add_extracted_field(field_entity, organization_id)
                    page_fields_count += 1

                page_dtos.append(
                    PageExtractionResultDTO(
                        page_id=page_entity.id,
                        page_number=page_extract.page_number,
                        has_digital_text=page_extract.has_digital_text,
                        text_layer_type=page_extract.text_layer_type,
                        extracted_text=page_extract.extracted_text,
                        word_count=page_extract.word_count,
                        width_pixels=page_extract.dimensions.width_pixels,
                        height_pixels=page_extract.dimensions.height_pixels,
                        dpi=page_extract.dimensions.dpi,
                        extracted_fields_count=page_fields_count,
                        warnings=page_extract.warnings,
                    )
                )

            # Update document status to PROCESSED
            doc.status = DocumentStatus.PROCESSED
            uow.documents.update(doc, organization_id)

            # Record TEXT_EXTRACTED AuditEvent
            actor_type = (
                ActorType.HUMAN_ANALYST
                if "analyst" in actor_id.lower()
                else ActorType.SYSTEM_PIPELINE
            )
            audit_event = AuditEvent.create(
                investigation_id=inv_id,
                event_type=AuditEventType.TEXT_EXTRACTED,
                actor_type=actor_type,
                actor_id=actor_id,
                event_payload={
                    "document_id": document_id,
                    "extraction_method": extraction.extraction_method,
                    "total_pages": extraction.total_pages,
                    "pages_with_digital_text": extraction.pages_with_digital_text,
                    "fields_persisted": sum(p.extracted_fields_count for p in page_dtos),
                    "is_retry": is_retry,
                    "prior_fields_cleared": deleted_prior,
                },
            )
            uow.audit_events.add(audit_event, organization_id)

        return DocumentExtractionResultDTO(
            document_id=document_id,
            investigation_id=inv_id,
            total_pages=extraction.total_pages,
            pages_with_digital_text=extraction.pages_with_digital_text,
            extraction_method=extraction.extraction_method,
            timestamp=extraction.timestamp,
            pages=page_dtos,
            warnings=extraction.warnings,
        )
