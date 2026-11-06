"""Persistence layer package exposing database, base, repositories, and Unit of Work."""

from veritrace.infrastructure.persistence.base import Base
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    get_default_database_url,
    init_db,
    session_scope,
)
from veritrace.infrastructure.persistence.repositories import (
    SqlAlchemyUnitOfWork,
    SqliteAuditEventRepository,
    SqliteDocumentRepository,
    SqliteEvidenceRepository,
    SqliteFindingRepository,
    SqliteInvestigationRepository,
)

__all__ = [
    "Base",
    "SqlAlchemyUnitOfWork",
    "SqliteAuditEventRepository",
    "SqliteDocumentRepository",
    "SqliteEvidenceRepository",
    "SqliteFindingRepository",
    "SqliteInvestigationRepository",
    "create_db_engine",
    "create_session_factory",
    "get_default_database_url",
    "init_db",
    "session_scope",
]
