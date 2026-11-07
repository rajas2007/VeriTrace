"""Custom status bar with progress telemetry and execution tracking."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QStatusBar,
    QWidget,
)


class VeriTraceStatusBar(QStatusBar):
    """Forensic status bar displaying stage telemetry and task progress."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        self._container = QWidget(self)
        layout = QHBoxLayout(self._container)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(14)

        self._stage_badge = QLabel("IDLE", self)
        self._stage_badge.setStyleSheet(
            "background-color: #0f1420; color: #10b981; border: 1px solid #10b981; "
            "padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 10px; "
            "letter-spacing: 0.5px;"
        )
        layout.addWidget(self._stage_badge)

        self._status_label = QLabel("Ready", self)
        self._status_label.setStyleSheet("color: #f1f5f9; font-weight: 600; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedWidth(220)
        self._progress_bar.setFixedHeight(12)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._telemetry_label = QLabel("", self)
        self._telemetry_label.setStyleSheet(
            "color: #64748b; font-size: 11px; font-family: 'Segoe UI', monospace;"
        )
        layout.addWidget(self._telemetry_label)

        self.addPermanentWidget(self._container, 1)

    def set_status(self, message: str, stage: str = "READY") -> None:
        """Update status message and stage indicator."""
        self._status_label.setText(message)
        self._stage_badge.setText(stage.upper())
        if stage.upper() in ("READY", "IDLE"):
            self._stage_badge.setStyleSheet(
                "background-color: #064e3b; color: #34d399; border: 1px solid #10b981; "
                "padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 10px; "
                "letter-spacing: 0.5px;"
            )
        elif stage.upper() in ("ANALYZING", "PROCESSING"):
            self._stage_badge.setStyleSheet(
                "background-color: #1e3a8a; color: #38bdf8; border: 1px solid #38bdf8; "
                "padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 10px; "
                "letter-spacing: 0.5px;"
            )
        elif stage.upper() == "ERROR":
            self._stage_badge.setStyleSheet(
                "background-color: #7f1d1d; color: #f87171; border: 1px solid #ef4444; "
                "padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 10px; "
                "letter-spacing: 0.5px;"
            )

    def start_progress(self, message: str = "Processing...") -> None:
        """Show progress bar and update stage to PROCESSING."""
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self.set_status(message, stage="ANALYZING")

    def update_progress(self, percent: int, message: str) -> None:
        """Update progress value and status message."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def finish_progress(self, message: str = "Operation completed") -> None:
        """Hide progress bar and set stage to READY."""
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(False)
        self.set_status(message, stage="READY")

    def set_telemetry(self, text: str) -> None:
        """Set telemetry or case metadata string."""
        self._telemetry_label.setText(text)
