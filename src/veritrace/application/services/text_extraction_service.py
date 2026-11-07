"""Application service for digital text extraction and result persistence."""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from veritrace.application.dto.extraction import (
    DocumentExtractionResultDTO,
    PageExtractionResultDTO,
)
from veritrace.capabilities.extraction.docling_adapter import DoclingLayoutAdapter
from veritrace.capabilities.extraction.ocr_engine import OcrEngineProtocol
from veritrace.capabilities.extraction.pdf_text_extractor import (
    DocumentDigitalExtraction,
    PdfDigitalTextExtractor,
)
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import (
    DocumentStatus,
    ExtractionSourceType,
    TextLayerType,
)
from veritrace.domain.exceptions.base import (
    DocumentExtractionError,
    EntityNotFoundError,
)
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.infrastructure.storage.document_storage import OriginalDocumentStorage

logger = logging.getLogger("veritrace.application.services.text_extraction_service")


class TextExtractionService:
    """Coordinates digital text extraction from documents, persistence, and audit logging."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork] | UnitOfWork,
        storage: OriginalDocumentStorage,
        extractor: PdfDigitalTextExtractor | None = None,
        ocr_engine: OcrEngineProtocol | None = None,
        layout_adapter: DoclingLayoutAdapter | None = None,
    ) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory
        self._storage = storage
        self._extractor = extractor or PdfDigitalTextExtractor()
        self._ocr_engine = ocr_engine
        self._layout_adapter = layout_adapter

    def _get_uow(self) -> UnitOfWork:
        return self._uow_factory()

    def set_ocr_engine(self, ocr_engine: OcrEngineProtocol | None) -> None:
        """Configure optional pluggable OCR engine backend."""
        self._ocr_engine = ocr_engine

    def set_layout_adapter(self, layout_adapter: DoclingLayoutAdapter | None) -> None:
        """Configure optional structured layout and table parsing adapter."""
        self._layout_adapter = layout_adapter

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
            # If an operational OCR engine is configured, extract raster tokens
            if self._ocr_engine is not None and self._ocr_engine.is_available():
                img_bytes = self._storage.read_original_for_tenant(organization_id, storage_path)
                ocr_result = self._ocr_engine.extract_page_ocr(img_bytes, page_number=1)

                page_entity = pages[0] if pages else None
                page_dtos: list[PageExtractionResultDTO] = []
                fields_persisted = 0

                with self._get_uow() as uow:
                    deleted_prior = uow.documents.delete_extracted_fields_by_document(
                        document_id, organization_id
                    )
                    is_retry = deleted_prior > 0 or doc.status == DocumentStatus.PROCESSED

                    if page_entity:
                        for tok in ocr_result.tokens:
                            field_entity = ExtractedField.create(
                                field_id=generate_id("fld_"),
                                page_id=page_entity.id,
                                field_name=f"ocr_token_{tok.token_id}",
                                field_value=tok.text,
                                raw_text=tok.text,
                                confidence=tok.confidence,
                                normalized_bbox=tok.normalized_bbox,
                                extraction_source=ExtractionSourceType.OCR,
                                ocr_engine=ocr_result.ocr_engine,
                                ocr_model_version=ocr_result.ocr_model_version,
                            )
                            uow.documents.add_extracted_field(field_entity, organization_id)
                            fields_persisted += 1

                        page_dtos.append(
                            PageExtractionResultDTO(
                                page_id=page_entity.id,
                                page_number=1,
                                has_digital_text=False,
                                text_layer_type=TextLayerType.SCANNED_RASTER,
                                extracted_text=ocr_result.full_text,
                                word_count=len(ocr_result.tokens),
                                width_pixels=ocr_result.dimensions.width_pixels,
                                height_pixels=ocr_result.dimensions.height_pixels,
                                dpi=ocr_result.dimensions.dpi,
                                extracted_fields_count=fields_persisted,
                                warnings=ocr_result.warnings,
                            )
                        )

                    doc.status = DocumentStatus.PROCESSED
                    uow.documents.update(doc, organization_id)

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
                            "extraction_method": f"OCR_{ocr_result.ocr_engine}",
                            "total_pages": len(pages),
                            "pages_with_digital_text": 0,
                            "fields_persisted": fields_persisted,
                            "is_retry": is_retry,
                            "prior_fields_cleared": deleted_prior,
                        },
                    )
                    uow.audit_events.add(audit_event, organization_id)

                return DocumentExtractionResultDTO(
                    document_id=document_id,
                    investigation_id=inv_id,
                    total_pages=len(pages),
                    pages_with_digital_text=0,
                    extraction_method=f"OCR_{ocr_result.ocr_engine}",
                    timestamp=datetime.now(UTC),
                    pages=page_dtos,
                    warnings=ocr_result.warnings,
                )

            # Standard NOOP fallback when no OCR engine is available
            page_dtos = []
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

        # Optional: Parse structured tables using Docling layout adapter if configured and available
        layout_tables: list[Any] = []
        if self._layout_adapter is not None and self._layout_adapter.is_available():
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                    tf.write(pdf_bytes)
                    temp_pdf_path = Path(tf.name)
                try:
                    layout_res = self._layout_adapter.parse_document(temp_pdf_path)
                    layout_tables = layout_res.tables
                finally:
                    if temp_pdf_path.exists():
                        temp_pdf_path.unlink()
            except Exception as exc:
                logger.warning(
                    "Docling structured layout parsing failed (%s); continuing with digital text.",
                    exc,
                )

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

                # If structured tables were extracted by Docling for this page, persist their fields
                for tbl in layout_tables:
                    try:
                        table_fields = tbl.to_extracted_fields(page_id=page_entity.id)
                        for tfld in table_fields:
                            uow.documents.add_extracted_field(tfld, organization_id)
                            page_fields_count += 1
                    except Exception as err:
                        logger.warning("Failed to persist structured table fields: %s", err)

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
