"""Background QThread worker for cross-document correlation."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QThread, Signal

from veritrace.application.dto.correlation import (
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)

logger = logging.getLogger("veritrace.gui.correlation_worker")


class CorrelationWorker(QThread):
    """Executes cross-document correlation asynchronously to keep GUI responsive."""

    started_signal = Signal()
    progress_signal = Signal(int, str)
    finished_signal = Signal(object)  # Emits CorrelationSummaryDTO
    error_signal = Signal(str)

    def __init__(
        self,
        correlation_service: CrossDocumentCorrelationService,
        request: CorrelationRequestDTO,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._correlation_service = correlation_service
        self._request = request

    def run(self) -> None:
        """Run correlation engine in worker thread."""
        try:
            self.started_signal.emit()
            self.progress_signal.emit(10, "Initializing correlation engine...")
            logger.info(
                "Background correlation worker started for %s", self._request.investigation_id
            )

            self.progress_signal.emit(30, "Aligning cross-document entities and line items...")
            self.progress_signal.emit(60, "Evaluating cross-document forensic rules...")

            summary: CorrelationSummaryDTO = self._correlation_service.correlate_investigation(
                self._request
            )

            self.progress_signal.emit(90, "Recording relations and audit events...")
            self.progress_signal.emit(100, "Analysis complete")
            logger.info(
                "Background correlation completed: %d discrepancies found",
                summary.discrepancies_count,
            )
            self.finished_signal.emit(summary)
        except Exception as exc:
            logger.exception("Background correlation failed: %s", exc)
            self.error_signal.emit(str(exc))
