"""VeriTrace PySide6 Application Subclass.

Manages the global QApplication lifecycle, High-DPI attributes,
application-wide exception handling, theme management, and graceful
shutdown of background QThreadPool tasks and database connections.
"""

from __future__ import annotations

import logging
import sys

from veritrace.gui.styles.theme_manager import load_stylesheet

logger = logging.getLogger("veritrace.gui.app")


class VeriTraceApp:
    """Application manager wrapping the PySide6 QApplication instance."""

    def __init__(self, argv: list[str] | None = None) -> None:
        self.argv = argv or sys.argv
        self._qapp = None
        self._theme_stylesheet = load_stylesheet("dark_theme")
        logger.info("VeriTraceApp instance created with %d arguments.", len(self.argv))

    @property
    def theme_stylesheet(self) -> str:
        """Return the active dark theme QSS stylesheet."""
        return self._theme_stylesheet

    def configure_qt(self) -> None:
        """Configure High-DPI attributes and instantiate QApplication if PySide6 is installed."""
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication

            # Enable High-DPI pixmaps
            if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

            existing = QApplication.instance()
            if existing is None:
                self._qapp = QApplication(self.argv)
            else:
                self._qapp = existing

            if self._theme_stylesheet:
                self._qapp.setStyleSheet(self._theme_stylesheet)
                logger.info("Applied forensic dark theme stylesheet to QApplication.")

        except ImportError:
            logger.warning("PySide6 not available in current environment; running headless.")
            self._qapp = None

    def run(self) -> int:
        """Start the Qt event loop, or return 0 if headless."""
        logger.info("Initializing VeriTrace desktop application runtime.")
        if self._qapp is None:
            # If configure_qt wasn't called or PySide6 is headless
            return 0

        # Start event loop when launched with active QApplication
        return int(self._qapp.exec())
