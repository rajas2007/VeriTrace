"""Protocol for Document repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.value_objects.identifiers import (
    DocumentId,
    DocumentPageId,
    InvestigationId,
    OrganizationId,
)


@runtime_checkable
class DocumentRepository(Protocol):
    """Repository interface for managing submitted Document entities and child pages/fields."""

    def add(self, document: Document, organization_id: OrganizationId) -> None:
        """Persist a new Document, verifying its investigation belongs to the organization."""
        ...

    def get_by_id(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> Document | None:
        """Retrieve a document by ID scoped strictly to the authorized organization."""
        ...

    def get_by_hash(
        self,
        file_hash_sha256: str,
        organization_id: OrganizationId,
    ) -> list[Document]:
        """Find documents with a matching SHA-256 hash within the authorized organization."""
        ...

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Document]:
        """List all documents for an investigation, enforcing tenant ownership."""
        ...

    def update(
        self,
        document: Document,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing document, enforcing tenant ownership."""
        ...

    def delete(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete a document, enforcing tenant ownership."""
        ...

    def add_page(
        self,
        page: DocumentPage,
        organization_id: OrganizationId,
    ) -> None:
        """Persist a DocumentPage entity, verifying parent document belongs to organization."""
        ...

    def get_page(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> DocumentPage | None:
        """Retrieve a document page by ID scoped strictly to the authorized organization."""
        ...

    def list_pages(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> list[DocumentPage]:
        """List all pages of a document ordered by page_number, enforcing tenant ownership."""
        ...

    def add_extracted_field(
        self,
        field: ExtractedField,
        organization_id: OrganizationId,
    ) -> None:
        """Persist an ExtractedField entity, verifying parent page belongs to organization."""
        ...

    def list_extracted_fields(
        self,
        page_id: DocumentPageId,
        organization_id: OrganizationId,
    ) -> list[ExtractedField]:
        """List all extracted fields for a page, enforcing tenant ownership."""
        ...

    def list_extracted_fields_by_document(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> list[ExtractedField]:
        """List all extracted fields for a document, enforcing tenant ownership."""
        ...

    def delete_extracted_fields_by_document(
        self,
        document_id: DocumentId,
        organization_id: OrganizationId,
    ) -> int:
        """Delete all extracted fields for a document, ensuring idempotent retries."""
        ...
