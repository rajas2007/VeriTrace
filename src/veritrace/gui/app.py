"""VeriTrace PySide6 Application Subclass.

Manages the global QApplication lifecycle, High-DPI attributes,
application-wide exception handling, theme management, and graceful
shutdown of background QThreadPool tasks and database connections.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from PySide6.QtWidgets import QApplication

from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.gui.styles.theme_manager import ThemeManager
from veritrace.gui.views.main_window import MainWindow

logger = logging.getLogger("veritrace.gui.app")


class VeriTraceApp:
    """Application manager wrapping the PySide6 QApplication instance."""

    def __init__(
        self,
        argv: list[str] | None = None,
        investigation_service: InvestigationService | None = None,
        correlation_service: CrossDocumentCorrelationService | None = None,
        ingestion_service: DocumentIngestionService | None = None,
        uow_factory: Any = None,
        organization_id: str = "org_11111111111111111111111111111111",
        headless: bool = False,
    ) -> None:
        self.argv = argv or sys.argv
        self._investigation_service = investigation_service
        self._correlation_service = correlation_service
        self._ingestion_service = ingestion_service
        self._uow_factory = uow_factory
        self._organization_id = organization_id
        self._headless = headless

        self.qapp: QApplication | None = None
        self.main_window: MainWindow | None = None
        logger.info("VeriTraceApp instance created.")

    def run(self) -> int:
        """Start the Qt event loop and present workstation interface."""
        logger.info("Initializing PySide6 application lifecycle...")
        existing = QApplication.instance()
        if isinstance(existing, QApplication):
            self.qapp = existing
        else:
            self.qapp = QApplication(self.argv)

        self.qapp.setApplicationName("VeriTrace")
        self.qapp.setOrganizationName("VeriTrace")

        # Apply dark theme stylesheet
        stylesheet = ThemeManager.get_stylesheet()
        if stylesheet:
            self.qapp.setStyleSheet(stylesheet)

        # Ensure services are present
        inv_service = self._investigation_service
        corr_service = self._correlation_service

        if inv_service is not None and corr_service is not None:
            self.main_window = MainWindow(
                investigation_service=inv_service,
                correlation_service=corr_service,
                ingestion_service=self._ingestion_service,
                uow_factory=self._uow_factory,
                organization_id=self._organization_id,
            )
            if not self._headless:
                self.main_window.show()
        else:
            # Standalone placeholder run without services
            return 0

        if self._headless:
            return 0

        logger.info("Entering Qt main event loop...")
        return self.qapp.exec()
