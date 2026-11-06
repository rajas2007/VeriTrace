"""SQLite implementation of DocumentRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.domain.value_objects.identifiers import (
    DocumentId,
    DocumentPageId,
    InvestigationId,
    OrganizationId,
)
from veritrace.infrastructure.persistence.mappers.document_mapper import DocumentMapper
from veritrace.infrastructure.persistence.mappers.document_page_mapper import (
    DocumentPageMapper,
)
from veritrace.infrastructure.persistence.mappers.extracted_field_mapper import (
    ExtractedFieldMapper,
)
from veritrace.infrastructure.persistence.models.document import DocumentModel
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel
from veritrace.infrastructure.persistence.models.extracted_field import (
    ExtractedFieldModel,
)
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class SqliteDocumentRepository:
    """SQLite-backed repository for Document entities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document, organization_id: OrganizationId) -> None:
        """Persist a new Document, verifying its investigation belongs to the organization."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(document.investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(document.investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{document.investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{document.investigation_id}' not found "
                f"in organization '{organization_id}'"
            )

        model = DocumentMapper.to_model(document)
        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> Document | None:
        """Retrieve a document by ID scoped strictly to the authorized organization."""
        stmt = (
            select(DocumentModel)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentModel.id == str(document_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return DocumentMapper.to_entity(row)

    def get_by_hash(
        self,
        file_hash_sha256: str,
        organization_id: OrganizationId,
    ) -> list[Document]:
        """Find documents with a matching SHA-256 hash within the authorized organization."""
        stmt = (
            select(DocumentModel)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentModel.file_hash_sha256 == file_hash_sha256,
                InvestigationModel.organization_id == str(organization_id),
            )
            .order_by(DocumentModel.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [DocumentMapper.to_entity(r) for r in rows]

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Document]:
        """List all documents for an investigation, enforcing tenant ownership."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(DocumentModel)
            .where(DocumentModel.investigation_id == str(investigation_id))
            .order_by(DocumentModel.created_at.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [DocumentMapper.to_entity(r) for r in rows]

    def update(
        self,
        document: Document,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing document, enforcing tenant ownership."""
        stmt = (
            select(DocumentModel)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentModel.id == str(document.id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_doc = self._session.get(DocumentModel, str(document.id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Document '{document.id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{document.id}' not found in organization '{organization_id}'"
            )

        model.original_filename = document.original_filename
        model.file_hash_sha256 = document.file_hash_sha256
        model.mime_type = document.mime_type
        model.document_type = document.document_type.value
        model.file_size_bytes = document.file_size_bytes
        model.storage_path = document.storage_path
        model.quality_status = document.quality_status.value
        model.structured_content = document.structured_content
        model.metadata_json = document.metadata_json
        model.status = document.status.value
        self._session.flush()

    def delete(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete a document, enforcing tenant ownership."""
        stmt = (
            select(DocumentModel)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentModel.id == str(document_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_doc = self._session.get(DocumentModel, str(document_id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Document '{document_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{document_id}' not found in organization '{organization_id}'"
            )
        self._session.delete(model)
        self._session.flush()

    def add_page(
        self,
        page: DocumentPage,
        organization_id: OrganizationId,
    ) -> None:
        """Persist a DocumentPage entity, verifying parent document belongs to organization."""
        doc = (
            self._session.execute(
                select(DocumentModel)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentModel.id == str(page.document_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if doc is None:
            any_doc = self._session.get(DocumentModel, str(page.document_id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document '{page.document_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{page.document_id}' not found in organization '{organization_id}'"
            )

        model = DocumentPageMapper.to_model(page)
        self._session.add(model)
        self._session.flush()

    def get_page(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> DocumentPage | None:
        """Retrieve a document page by ID scoped strictly to the authorized organization."""
        stmt = (
            select(DocumentPageModel)
            .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
            .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
            .where(
                DocumentPageModel.id == str(page_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return DocumentPageMapper.to_entity(row)

    def list_pages(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> list[DocumentPage]:
        """List all pages of a document ordered by page_number, enforcing tenant ownership."""
        doc = (
            self._session.execute(
                select(DocumentModel)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentModel.id == str(document_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if doc is None:
            any_doc = self._session.get(DocumentModel, str(document_id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document '{document_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{document_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(DocumentPageModel)
            .where(DocumentPageModel.document_id == str(document_id))
            .order_by(DocumentPageModel.page_number.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [DocumentPageMapper.to_entity(r) for r in rows]

    def add_extracted_field(
        self,
        field: ExtractedField,
        organization_id: OrganizationId,
    ) -> None:
        """Persist an ExtractedField entity, verifying parent page belongs to organization."""
        page = (
            self._session.execute(
                select(DocumentPageModel)
                .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentPageModel.id == str(field.page_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if page is None:
            any_page = self._session.get(DocumentPageModel, str(field.page_id))
            if any_page is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document page '{field.page_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document page '{field.page_id}' not found in organization '{organization_id}'"
            )

        model = ExtractedFieldMapper.to_model(field)
        self._session.add(model)
        self._session.flush()

    def list_extracted_fields(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> list[ExtractedField]:
        """List all extracted fields for a page, enforcing tenant ownership."""
        page = (
            self._session.execute(
                select(DocumentPageModel)
                .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentPageModel.id == str(page_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if page is None:
            any_page = self._session.get(DocumentPageModel, str(page_id))
            if any_page is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document page '{page_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document page '{page_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(ExtractedFieldModel)
            .where(ExtractedFieldModel.page_id == str(page_id))
            .order_by(ExtractedFieldModel.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [ExtractedFieldMapper.to_entity(r) for r in rows]

    def list_extracted_fields_by_document(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> list[ExtractedField]:
        """List all extracted fields for a document, enforcing tenant ownership."""
        doc = (
            self._session.execute(
                select(DocumentModel)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentModel.id == str(document_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if doc is None:
            any_doc = self._session.get(DocumentModel, str(document_id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document '{document_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{document_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(ExtractedFieldModel)
            .join(DocumentPageModel, ExtractedFieldModel.page_id == DocumentPageModel.id)
            .where(DocumentPageModel.document_id == str(document_id))
            .order_by(
                DocumentPageModel.page_number.asc(),
                ExtractedFieldModel.id.asc(),
            )
        )
        rows = self._session.execute(stmt).scalars().all()
        return [ExtractedFieldMapper.to_entity(r) for r in rows]

    def delete_extracted_fields_by_document(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> int:
        """Delete all extracted fields for a document, ensuring idempotent extraction retries."""
        doc = (
            self._session.execute(
                select(DocumentModel)
                .join(InvestigationModel, DocumentModel.investigation_id == InvestigationModel.id)
                .where(
                    DocumentModel.id == str(document_id),
                    InvestigationModel.organization_id == str(organization_id),
                )
            )
            .scalars()
            .first()
        )
        if doc is None:
            any_doc = self._session.get(DocumentModel, str(document_id))
            if any_doc is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Document '{document_id}' "
                    f"does not belong to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Document '{document_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(ExtractedFieldModel)
            .join(DocumentPageModel, ExtractedFieldModel.page_id == DocumentPageModel.id)
            .where(DocumentPageModel.document_id == str(document_id))
        )
        fields = self._session.execute(stmt).scalars().all()
        count = len(fields)
        for f in fields:
            self._session.delete(f)
        self._session.flush()
        return count
