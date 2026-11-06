"""VeriTrace Native Desktop Application Entrypoint.

Initializes application bootstrap, applies High-DPI attributes,
instantiates the PySide6 QApplication, mounts the forensic workstation window,
and enters the Qt event loop.
"""

from __future__ import annotations

import logging
import os
import sys

from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.bootstrap import bootstrap_application
from veritrace.gui.app import VeriTraceApp
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    init_db,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from veritrace.infrastructure.storage.document_storage import (
    OriginalDocumentStorage,
)

logger = logging.getLogger("veritrace.main")


def main() -> int:
    """Initialize and run the VeriTrace PySide6 desktop application."""
    bootstrap_application()
    logger.info("Starting VeriTrace Desktop...")

    engine = create_db_engine()
    init_db(engine)
    session_factory = create_session_factory(engine)

    from datetime import UTC, datetime

    from veritrace.infrastructure.persistence.models.organization import (
        OrganizationModel,
    )

    with session_factory() as session:
        default_org_id = "org_11111111111111111111111111111111"
        if session.get(OrganizationModel, default_org_id) is None:
            session.add(
                OrganizationModel(
                    id=default_org_id,
                    name="Default Manufacturing Organization",
                    industry_sector="MANUFACTURING",
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    storage = OriginalDocumentStorage(allow_workspace_storage=True)
    ingestion_service = DocumentIngestionService(uow_factory, storage)
    inv_service = InvestigationService(uow_factory)
    corr_service = CrossDocumentCorrelationService(uow_factory)

    headless = "--headless" in sys.argv or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    app = VeriTraceApp(
        argv=sys.argv,
        investigation_service=inv_service,
        correlation_service=corr_service,
        ingestion_service=ingestion_service,
        uow_factory=uow_factory,
        headless=headless,
    )
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
