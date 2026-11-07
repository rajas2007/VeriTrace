"""Background QThread worker for compiling investigation dossiers without blocking UI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from veritrace.application.services.investigation_service import (
    InvestigationService,
)

logger = logging.getLogger("veritrace.gui.dossier_worker")


class DossierWorker(QThread):
    """Background worker executing PS-2 dossier compilation."""

    progress_signal = Signal(int, str)  # (percent: 0-100, stage_description)
    finished_signal = Signal(str, str)  # (pdf_path, json_path)
    error_signal = Signal(str)

    def __init__(
        self,
        investigation_service: InvestigationService,
        investigation_id: str,
        organization_id: str,
        output_dir: Path | str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._service = investigation_service
        self._investigation_id = investigation_id
        self._organization_id = organization_id
        self._output_dir = output_dir

    def run(self) -> None:
        """Execute dossier compilation workflow."""
        try:
            self.progress_signal.emit(15, "Gathering case evidence and extracted fields...")
            self.progress_signal.emit(35, "Evaluating contextual arithmetic and timeline rules...")
            self.progress_signal.emit(55, "Synthesizing auditor-grade executive narrative...")
            self.progress_signal.emit(75, "Compiling PS-2 JSON payload and ReportLab PDF...")

            _, _, pdf_path, json_path = self._service.compile_investigation_dossier(
                investigation_id=self._investigation_id,
                organization_id=self._organization_id,
                output_dir=self._output_dir,
            )

            self.progress_signal.emit(100, "Investigation dossier successfully compiled.")
            self.finished_signal.emit(str(pdf_path), str(json_path))
        except Exception as err:
            logger.exception("Dossier compilation failed: %s", err)
            self.error_signal.emit(str(err))
