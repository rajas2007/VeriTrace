"""SQLite implementation of SignatureReferenceRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.exceptions.base import EntityNotFoundError, TenantIsolationError
from veritrace.infrastructure.persistence.mappers.authorized_subject_mapper import (
    AuthorizedSubjectMapper,
)
from veritrace.infrastructure.persistence.mappers.signature_reference_mapper import (
    SignatureReferenceMapper,
)
from veritrace.infrastructure.persistence.models.authorized_subject import (
    AuthorizedSubjectModel,
)
from veritrace.infrastructure.persistence.models.signature_reference import (
    SignatureReferenceProfileModel,
)


class SqliteSignatureReferenceRepository:
    """SQLite-backed repository for SignatureReferenceProfiles and AuthorizedSubjects."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        profile: SignatureReferenceProfile,
        organization_id: str,
    ) -> None:
        """Persist an enrolled signature reference profile, enforcing tenant boundary."""
        if str(profile.organization_id) != str(organization_id):
            raise TenantIsolationError(
                f"Cross-organization violation: Profile organization '{profile.organization_id}' "
                f"does not match caller organization '{organization_id}'"
            )

        # Verify subject exists and belongs to the same organization
        subject = self._session.get(AuthorizedSubjectModel, str(profile.subject_id))
        if subject is None:
            raise EntityNotFoundError(
                f"AuthorizedSubject '{profile.subject_id}' not found in "
                f"organization '{organization_id}'"
            )
        if str(subject.organization_id) != str(organization_id):
            raise TenantIsolationError(
                f"Cross-organization violation: AuthorizedSubject '{profile.subject_id}' "
                f"belongs to organization '{subject.organization_id}', not '{organization_id}'"
            )

        model = SignatureReferenceMapper.to_model(profile)
        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        profile_id: str,
        organization_id: str,
    ) -> SignatureReferenceProfile | None:
        """Retrieve a signature reference profile by ID scoped strictly to organization."""
        model = self._session.execute(
            select(SignatureReferenceProfileModel).where(
                SignatureReferenceProfileModel.id == str(profile_id),
                SignatureReferenceProfileModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if model is not None:
            return SignatureReferenceMapper.to_entity(model)

        # Check if profile belongs to another organization
        other = self._session.get(SignatureReferenceProfileModel, str(profile_id))
        if other is not None and str(other.organization_id) != str(organization_id):
            raise TenantIsolationError(
                f"Cross-organization violation: SignatureReferenceProfile '{profile_id}' "
                f"belongs to organization '{other.organization_id}', not '{organization_id}'"
            )
        return None

    def list_by_subject(
        self,
        subject_id: str,
        organization_id: str,
    ) -> list[SignatureReferenceProfile]:
        """List all enrolled signature references for an authorized subject."""
        models = (
            self._session.execute(
                select(SignatureReferenceProfileModel)
                .where(
                    SignatureReferenceProfileModel.subject_id == str(subject_id),
                    SignatureReferenceProfileModel.organization_id == str(organization_id),
                )
                .order_by(SignatureReferenceProfileModel.enrollment_date.desc())
            )
            .scalars()
            .all()
        )
        return [SignatureReferenceMapper.to_entity(m) for m in models]

    def list_by_organization(
        self,
        organization_id: str,
    ) -> list[SignatureReferenceProfile]:
        """List all enrolled signature references for an organization."""
        models = (
            self._session.execute(
                select(SignatureReferenceProfileModel)
                .where(SignatureReferenceProfileModel.organization_id == str(organization_id))
                .order_by(SignatureReferenceProfileModel.enrollment_date.desc())
            )
            .scalars()
            .all()
        )
        return [SignatureReferenceMapper.to_entity(m) for m in models]

    def add_subject(
        self,
        subject: AuthorizedSubject,
        organization_id: str,
    ) -> None:
        """Persist a new AuthorizedSubject entity, enforcing tenant boundary."""
        if str(subject.organization_id) != str(organization_id):
            raise TenantIsolationError(
                f"Cross-organization violation: Subject organization '{subject.organization_id}' "
                f"does not match caller organization '{organization_id}'"
            )

        model = AuthorizedSubjectMapper.to_model(subject)
        self._session.add(model)
        self._session.flush()

    def get_subject_by_id(
        self,
        subject_id: str,
        organization_id: str,
    ) -> AuthorizedSubject | None:
        """Retrieve an authorized subject by ID scoped strictly to organization."""
        model = self._session.execute(
            select(AuthorizedSubjectModel).where(
                AuthorizedSubjectModel.id == str(subject_id),
                AuthorizedSubjectModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if model is not None:
            return AuthorizedSubjectMapper.to_entity(model)

        other = self._session.get(AuthorizedSubjectModel, str(subject_id))
        if other is not None and str(other.organization_id) != str(organization_id):
            raise TenantIsolationError(
                f"Cross-organization violation: AuthorizedSubject '{subject_id}' "
                f"belongs to organization '{other.organization_id}', not '{organization_id}'"
            )
        return None

    def list_subjects(
        self,
        organization_id: str,
    ) -> list[AuthorizedSubject]:
        """List all authorized subjects for an organization."""
        models = (
            self._session.execute(
                select(AuthorizedSubjectModel)
                .where(AuthorizedSubjectModel.organization_id == str(organization_id))
                .order_by(AuthorizedSubjectModel.full_name.asc())
            )
            .scalars()
            .all()
        )
        return [AuthorizedSubjectMapper.to_entity(m) for m in models]
