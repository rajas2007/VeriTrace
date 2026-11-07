"""Application workflow orchestrating end-to-end document processing.

Coordinates: Create Investigation -> Ingest Document -> Store Original ->
Extract Digital Text -> Persist Results -> Record Audit Events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from veritrace.application.dto.document import (
    DocumentIngestDTO,
    DocumentIngestionResultDTO,
)
from veritrace.application.dto.extraction import DocumentExtractionResultDTO
from veritrace.application.dto.investigation import (
    InvestigationCreateDTO,
    InvestigationResponseDTO,
)
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.application.services.text_extraction_service import (
    TextExtractionService,
)
from veritrace.domain.enums.document import DocumentType

logger = logging.getLogger("veritrace.application.workflows.document_processing")


@dataclass(slots=True)
class WorkflowExecutionResult:
    """Consolidated result of an end-to-end document processing workflow."""

    investigation: InvestigationResponseDTO
    document: DocumentIngestionResultDTO
    extraction: DocumentExtractionResultDTO


class DocumentProcessingWorkflow:
    """Orchestrates intake, storage, extraction, and audit trails for forensic documents."""

    def __init__(
        self,
        investigation_service: InvestigationService,
        ingestion_service: DocumentIngestionService,
        extraction_service: TextExtractionService,
    ) -> None:
        self._investigation_service = investigation_service
        self._ingestion_service = ingestion_service
        self._extraction_service = extraction_service

    def execute_new_investigation_workflow(
        self,
        organization_id: str,
        investigation_title: str,
        reference_code: str,
        filename: str,
        content: bytes | None = None,
        file_path: Path | str | None = None,
        document_type: DocumentType = DocumentType.UNCLASSIFIED,
        actor_id: str = "analyst_01",
    ) -> WorkflowExecutionResult:
        """Create new investigation, ingest document, extract digital text, and record audit."""
        # 1. Create Investigation
        inv_create = InvestigationCreateDTO(
            title=investigation_title,
            reference_code=reference_code,
            organization_id=organization_id,
        )
        inv = self._investigation_service.create_investigation(inv_create, actor_id=actor_id)

        # 2. Ingest Document
        doc_ingest = DocumentIngestDTO(
            investigation_id=inv.id,
            organization_id=organization_id,
            filename=filename,
            content=content,
            file_path=file_path,
            document_type=document_type,
        )
        doc = self._ingestion_service.ingest_document(doc_ingest, actor_id=actor_id)

        # 3. Extract Digital Text & Persist Tokens
        ext = self._extraction_service.extract_document_text(
            document_id=doc.document_id,
            organization_id=organization_id,
            actor_id=actor_id,
        )

        # 4. Classify document after extraction has completed
        try:
            if document_type == DocumentType.UNCLASSIFIED:
                classified_type, _ = self._investigation_service.classify_document(
                    document_id=doc.document_id,
                    organization_id=organization_id,
                )
                doc = doc.model_copy(update={"document_type": classified_type})
        except Exception as err:
            logger.warning(
                "Post-extraction classification failed for document '%s': %s",
                doc.document_id,
                err,
            )

        return WorkflowExecutionResult(
            investigation=inv,
            document=doc,
            extraction=ext,
        )

    def execute_existing_investigation_workflow(
        self,
        investigation_id: str,
        organization_id: str,
        filename: str,
        content: bytes | None = None,
        file_path: Path | str | None = None,
        document_type: DocumentType = DocumentType.UNCLASSIFIED,
        actor_id: str = "analyst_01",
    ) -> WorkflowExecutionResult:
        """Ingest document into existing investigation and extract digital text."""
        inv = self._investigation_service.get_investigation(investigation_id, organization_id)
        if inv is None:
            from veritrace.domain.exceptions.base import EntityNotFoundError

            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )

        doc_ingest = DocumentIngestDTO(
            investigation_id=investigation_id,
            organization_id=organization_id,
            filename=filename,
            content=content,
            file_path=file_path,
            document_type=document_type,
        )
        doc = self._ingestion_service.ingest_document(doc_ingest, actor_id=actor_id)

        ext = self._extraction_service.extract_document_text(
            document_id=doc.document_id,
            organization_id=organization_id,
            actor_id=actor_id,
        )

        # 4. Classify document after extraction has completed
        try:
            if document_type == DocumentType.UNCLASSIFIED:
                classified_type, _ = self._investigation_service.classify_document(
                    document_id=doc.document_id,
                    organization_id=organization_id,
                )
                doc = doc.model_copy(update={"document_type": classified_type})
        except Exception as err:
            logger.warning(
                "Post-extraction classification failed for document '%s': %s",
                doc.document_id,
                err,
            )

        return WorkflowExecutionResult(
            investigation=inv,
            document=doc,
            extraction=ext,
        )
