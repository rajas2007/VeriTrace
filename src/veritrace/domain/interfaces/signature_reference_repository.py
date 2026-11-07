"""Protocol for SignatureReferenceProfile repository operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile


@runtime_checkable
class SignatureReferenceRepository(Protocol):
    """Repository interface for SignatureReferenceProfiles and AuthorizedSubjects."""

    def add(
        self,
        profile: SignatureReferenceProfile,
        organization_id: str,
    ) -> None:
        """Persist a new SignatureReferenceProfile entity, enforcing tenant boundary."""
        ...

    def get_by_id(
        self,
        profile_id: str,
        organization_id: str,
    ) -> SignatureReferenceProfile | None:
        """Retrieve a signature reference profile by ID, scoped to organization."""
        ...

    def list_by_subject(
        self,
        subject_id: str,
        organization_id: str,
    ) -> list[SignatureReferenceProfile]:
        """List all enrolled signature references for an authorized subject in an organization."""
        ...

    def list_by_organization(
        self,
        organization_id: str,
    ) -> list[SignatureReferenceProfile]:
        """List all enrolled signature references for an entire organization."""
        ...

    def add_subject(
        self,
        subject: AuthorizedSubject,
        organization_id: str,
    ) -> None:
        """Persist a new AuthorizedSubject entity, enforcing tenant boundary."""
        ...

    def get_subject_by_id(
        self,
        subject_id: str,
        organization_id: str,
    ) -> AuthorizedSubject | None:
        """Retrieve an authorized subject by ID, scoped strictly to organization."""
        ...

    def list_subjects(
        self,
        organization_id: str,
    ) -> list[AuthorizedSubject]:
        """List all authorized subjects for an organization."""
        ...
