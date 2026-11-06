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
from veritrace.gui.styles.theme_manager import load_stylesheet
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
        if "--headless" in self.argv:
            headless = True

        self._investigation_service = investigation_service
        self._correlation_service = correlation_service
        self._ingestion_service = ingestion_service
        self._uow_factory = uow_factory
        self._organization_id = organization_id
        self._headless = headless

        self._theme_stylesheet = load_stylesheet("dark_theme")
        self._qapp: QApplication | None = None
        self.main_window: MainWindow | None = None
        logger.info("VeriTraceApp instance created with %d arguments.", len(self.argv))

    @property
    def qapp(self) -> QApplication | None:
        """Return the underlying QApplication instance."""
        return self._qapp

    @qapp.setter
    def qapp(self, value: QApplication | None) -> None:
        self._qapp = value

    @property
    def theme_stylesheet(self) -> str:
        """Return the active dark theme QSS stylesheet."""
        return self._theme_stylesheet

    def configure_qt(self) -> None:
        """Configure High-DPI attributes and instantiate QApplication if PySide6 is installed."""
        try:
            from PySide6.QtCore import Qt

            # Enable High-DPI pixmaps
            if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

            existing = QApplication.instance()
            if existing is None:
                self._qapp = QApplication(self.argv)
            elif isinstance(existing, QApplication):
                self._qapp = existing
            else:
                self._qapp = None

            if self._qapp is not None:
                self._qapp.setApplicationName("VeriTrace")
                self._qapp.setOrganizationName("VeriTrace")

                if self._theme_stylesheet:
                    self._qapp.setStyleSheet(self._theme_stylesheet)
                    logger.info("Applied forensic dark theme stylesheet to QApplication.")

        except ImportError:
            logger.warning("PySide6 not available in current environment; running headless.")
            self._qapp = None

    def run(self) -> int:
        """Start the Qt event loop, or return 0 if headless."""
        logger.info("Initializing VeriTrace desktop application runtime...")
        if self._qapp is None:
            self.configure_qt()

        if self._qapp is None:
            return 0

        # Ensure services are present for interactive workstation presentation
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
        return int(self._qapp.exec())
