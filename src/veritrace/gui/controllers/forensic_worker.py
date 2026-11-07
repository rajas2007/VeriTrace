"""Background QThread worker executing visual forensic analysis without blocking UI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile

logger = logging.getLogger("veritrace.gui.forensic_worker")


class ForensicWorker(QThread):
    """Worker executing signature detection, stroke morphology, and copy-move analysis."""

    progress_signal = Signal(int, str)  # (percent: 0-100, stage_description)
    finished_signal = Signal(int)  # count of new findings created
    error_signal = Signal(str)

    def __init__(
        self,
        investigation_service: InvestigationService,
        investigation_id: str,
        organization_id: str,
        reference_profiles: list[SignatureReferenceProfile] | None = None,
        crops_dir: Path | str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._service = investigation_service
        self._investigation_id = investigation_id
        self._organization_id = organization_id
        self._reference_profiles = reference_profiles
        self._crops_dir = crops_dir

    def run(self) -> None:
        """Execute forensic pipeline asynchronously."""
        try:
            self.progress_signal.emit(15, "Verifying page image quality and raster resolutions...")
            self.progress_signal.emit(35, "Scanning canvases for handwritten signatures...")
            self.progress_signal.emit(65, "Measuring stroke morphology and boundary artifacts...")
            self.progress_signal.emit(85, "Executing multi-scale ORB copy-move feature matching...")

            findings = self._service.run_forensic_analysis(
                investigation_id=self._investigation_id,
                organization_id=self._organization_id,
                reference_profiles=self._reference_profiles,
                crops_dir=self._crops_dir,
            )

            self.progress_signal.emit(100, "Visual forensics scan complete.")
            self.finished_signal.emit(len(findings))
        except Exception as err:
            logger.exception("Visual forensic analysis failed: %s", err)
            self.error_signal.emit(str(err))
