"""Investigation and Document management sidebar widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.document import DocumentIngestionResultDTO
from veritrace.application.dto.investigation import InvestigationResponseDTO
from veritrace.gui.styles.theme_manager import ThemeManager


class InvestigationSidebar(QWidget):
    """Sidebar for case selection, metadata inspection, and document navigation."""

    investigation_selected = Signal(str)  # investigation_id
    document_selected = Signal(str)  # document_id
    new_investigation_requested = Signal()
    add_document_requested = Signal()
    load_demo_requested = Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._investigations: list[InvestigationResponseDTO] = []
        self._documents: list[DocumentIngestionResultDTO] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Header & Case Switcher
        header_layout = QHBoxLayout()
        header_title = QLabel("🗂️ INVESTIGATION CASE", self)
        header_title.setStyleSheet(
            "font-weight: 800; color: #38bdf8; font-size: 11px; letter-spacing: 0.6px;"
        )
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        self._btn_new = QPushButton("+ New Case", self)
        self._btn_new.setStyleSheet("padding: 4px 10px; font-size: 11px; font-weight: 700;")
        self._btn_new.setToolTip("Create a new investigation case")
        self._btn_new.clicked.connect(self.new_investigation_requested.emit)
        header_layout.addWidget(self._btn_new)
        layout.addLayout(header_layout)

        self._case_combo = QComboBox(self)
        self._case_combo.currentIndexChanged.connect(self._on_case_changed)
        layout.addWidget(self._case_combo)

        # 2. Case Details Card
        self._card_frame = QFrame(self)
        self._card_frame.setObjectName("card")
        card_layout = QVBoxLayout(self._card_frame)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

        self._lbl_ref = QLabel("Ref: --", self._card_frame)
        self._lbl_ref.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 12px;")
        card_layout.addWidget(self._lbl_ref)

        self._lbl_status = QLabel("Status: --", self._card_frame)
        self._lbl_status.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        card_layout.addWidget(self._lbl_status)

        self._lbl_risk = QLabel("Risk: --", self._card_frame)
        self._lbl_risk.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        card_layout.addWidget(self._lbl_risk)

        layout.addWidget(self._card_frame)

        # 3. Documents Section
        doc_header = QHBoxLayout()
        doc_title = QLabel("📑 CASE EVIDENCE DOSSIER", self)
        doc_title.setStyleSheet(
            "font-weight: 800; color: #38bdf8; font-size: 11px; letter-spacing: 0.6px;"
        )
        doc_header.addWidget(doc_title)
        doc_header.addStretch()

        self._btn_add_doc = QPushButton("+ Import", self)
        self._btn_add_doc.setStyleSheet("padding: 4px 10px; font-size: 11px; font-weight: 700;")
        self._btn_add_doc.clicked.connect(self.add_document_requested.emit)
        doc_header.addWidget(self._btn_add_doc)
        layout.addLayout(doc_header)

        self._doc_tree = QTreeWidget(self)
        self._doc_tree.setHeaderLabels(["Document", "Type", "Pages"])
        self._doc_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._doc_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._doc_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._doc_tree.itemClicked.connect(self._on_doc_item_clicked)
        layout.addWidget(self._doc_tree, 1)

        # 4. Demo Data Action
        self._btn_demo = QPushButton("🔄 Load Industrial Alloy Demo (4 Docs)", self)
        self._btn_demo.setObjectName("primaryButton")
        self._btn_demo.setStyleSheet("padding: 9px 14px; font-size: 12px; font-weight: 700;")
        self._btn_demo.clicked.connect(self.load_demo_requested.emit)
        layout.addWidget(self._btn_demo)

    def set_investigations(
        self, investigations: list[InvestigationResponseDTO], selected_id: str | None = None
    ) -> None:
        """Populate case dropdown and select active case."""
        self._investigations = investigations
        self._case_combo.blockSignals(True)
        self._case_combo.clear()
        selected_idx = 0
        for idx, inv in enumerate(investigations):
            self._case_combo.addItem(f"{inv.reference_code}: {inv.title}", inv.id)
            if selected_id and inv.id == selected_id:
                selected_idx = idx
        self._case_combo.blockSignals(False)

        if investigations:
            self._case_combo.setCurrentIndex(selected_idx)
            self._update_case_card(investigations[selected_idx])

    def _on_case_changed(self, index: int) -> None:
        if 0 <= index < len(self._investigations):
            inv = self._investigations[index]
            self._update_case_card(inv)
            self.investigation_selected.emit(inv.id)

    def _update_case_card(self, inv: InvestigationResponseDTO) -> None:
        self._lbl_ref.setText(f"Ref: {inv.reference_code}")
        self._lbl_status.setText(f"Status: <b>{inv.status.value}</b>")
        risk_color = ThemeManager.get_severity_color(
            "CRITICAL" if inv.risk_score >= 0.75 else "MEDIUM" if inv.risk_score >= 0.4 else "LOW"
        )
        self._lbl_risk.setText(
            f"Risk Score: <span style='color: {risk_color}; font-weight: 800; font-size: 12px;'>"
            f"{inv.risk_score:.2f} ({inv.risk_classification.value})</span>"
        )

    def set_documents(self, documents: list[DocumentIngestionResultDTO]) -> None:
        """Populate documents tree widget."""
        self._documents = documents
        self._doc_tree.clear()
        for doc in documents:
            item = QTreeWidgetItem(self._doc_tree)
            doc_type_val = doc.document_type.value
            icon_prefix = "📄"
            if "PURCHASE" in doc_type_val:
                icon_prefix = "📋"
            elif "DELIVERY" in doc_type_val or "CHALLAN" in doc_type_val:
                icon_prefix = "🚚"
            elif "TEST_CERTIFICATE" in doc_type_val:
                icon_prefix = "🔬"
            elif "INVOICE" in doc_type_val:
                icon_prefix = "🧾"

            item.setText(0, f"{icon_prefix} {doc.original_filename}")
            item.setText(1, doc_type_val.replace("_", " "))
            item.setText(2, str(doc.page_count))
            item.setData(0, Qt.ItemDataRole.UserRole, doc.document_id)

    def _on_doc_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        doc_id = item.data(0, Qt.ItemDataRole.UserRole)
        if doc_id:
            self.document_selected.emit(str(doc_id))
