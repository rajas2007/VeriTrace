"""Signature Forensics Workbench component."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.forensics import SignatureComparisonDTO
from veritrace.application.dto.signature_reference import (
    AuthorizedSubjectDTO,
    SignatureReferenceDTO,
)


class CreateAuthorizedSubjectDialog(QDialog):
    """Modal dialog to register an authorized enterprise signatory."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Register Authorized Signatory Subject")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self._txt_name = QLineEdit(self)
        self._txt_name.setPlaceholderText("e.g. Elena Rostova")
        form.addRow("Full Name:", self._txt_name)

        self._txt_desig = QLineEdit(self)
        self._txt_desig.setPlaceholderText("e.g. Chief Financial Officer")
        form.addRow("Designation:", self._txt_desig)

        self._txt_id_ref = QLineEdit(self)
        self._txt_id_ref.setPlaceholderText("e.g. EMP-2024-8841")
        form.addRow("ID / Mandate Ref:", self._txt_id_ref)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self._btn_cancel = QPushButton("Cancel", self)
        self._btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self._btn_cancel)

        self._btn_ok = QPushButton("Register Subject", self)
        self._btn_ok.setObjectName("primaryButton")
        self._btn_ok.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self._btn_ok)

        layout.addLayout(btn_box)

    def _validate_and_accept(self) -> None:
        if not self._txt_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            return
        if not self._txt_desig.text().strip():
            QMessageBox.warning(self, "Validation Error", "Designation is required.")
            return
        if not self._txt_id_ref.text().strip():
            QMessageBox.warning(self, "Validation Error", "ID Reference is required.")
            return
        self.accept()

    def get_data(self) -> tuple[str, str, str]:
        return (
            self._txt_name.text().strip(),
            self._txt_desig.text().strip(),
            self._txt_id_ref.text().strip(),
        )


class EnrollSignatureReferenceDialog(QDialog):
    """Modal dialog to enroll a specimen signature crop under chain of custody."""

    def __init__(
        self,
        subjects: list[AuthorizedSubjectDTO],
        parent: QWidget | None = None,
        preselected_subject_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Enroll Specimen Signature Reference")
        self.setMinimumWidth(500)

        self._subjects = subjects
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._combo_subjects = QComboBox(self)
        for s in subjects:
            self._combo_subjects.addItem(f"{s.full_name} ({s.designation})", s.id)
        if preselected_subject_id:
            idx = self._combo_subjects.findData(preselected_subject_id)
            if idx >= 0:
                self._combo_subjects.setCurrentIndex(idx)
        form.addRow("Authorized Subject:", self._combo_subjects)

        # File selection
        file_row = QHBoxLayout()
        self._txt_path = QLineEdit(self)
        self._txt_path.setPlaceholderText("Path to high-resolution specimen crop image...")
        self._btn_browse = QPushButton("Browse...", self)
        self._btn_browse.clicked.connect(self._on_browse)
        file_row.addWidget(self._txt_path, 1)
        file_row.addWidget(self._btn_browse)
        form.addRow("Specimen Crop Image:", file_row)

        # Image preview
        self._lbl_preview = QLabel("No Specimen Selected", self)
        self._lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_preview.setMinimumHeight(100)
        self._lbl_preview.setStyleSheet(
            "background: #090d16; border: 1px dashed #30363d; border-radius: 4px; padding: 4px;"
        )
        form.addRow("Visual Preview:", self._lbl_preview)

        self._txt_source_ref = QLineEdit(self)
        self._txt_source_ref.setPlaceholderText("e.g. Board Resolution 2024-A, Signature Card #1")
        form.addRow("Source Document Ref:", self._txt_source_ref)

        self._txt_consent_ref = QLineEdit(self)
        self._txt_consent_ref.setPlaceholderText("e.g. SIGNER-MANDATE-2024-001")
        form.addRow("Consent Mandate Ref:", self._txt_consent_ref)

        self._combo_role = QComboBox(self)
        self._combo_role.addItems(["FORENSIC_INVESTIGATOR", "ANALYST", "ADMIN"])
        form.addRow("Required Access Role:", self._combo_role)

        layout.addLayout(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self._btn_cancel = QPushButton("Cancel", self)
        self._btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self._btn_cancel)

        self._btn_enroll = QPushButton("Enroll Reference", self)
        self._btn_enroll.setObjectName("primaryButton")
        self._btn_enroll.clicked.connect(self._validate_and_accept)
        btn_box.addWidget(self._btn_enroll)

        layout.addLayout(btn_box)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Specimen Signature Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)",
        )
        if path:
            self._txt_path.setText(path)
            self._update_preview(path)

    def _update_preview(self, path_str: str) -> None:
        p = Path(path_str)
        if p.exists() and p.is_file():
            pix = QPixmap(str(p))
            if not pix.isNull():
                self._lbl_preview.setPixmap(
                    pix.scaled(
                        260,
                        100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self._lbl_preview.setText("Invalid Image")

    def _validate_and_accept(self) -> None:
        if self._combo_subjects.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select an authorized subject.")
            return
        img_path = self._txt_path.text().strip()
        if not img_path or not Path(img_path).is_file():
            QMessageBox.warning(
                self, "Validation Error", "A valid specimen image file is required."
            )
            return
        if not self._txt_source_ref.text().strip():
            QMessageBox.warning(self, "Validation Error", "Source document reference is required.")
            return
        if not self._txt_consent_ref.text().strip():
            QMessageBox.warning(self, "Validation Error", "Consent mandate reference is required.")
            return
        self.accept()

    def get_data(self) -> dict[str, str]:
        return {
            "subject_id": str(self._combo_subjects.currentData()),
            "crop_image_path": self._txt_path.text().strip(),
            "source_document_ref": self._txt_source_ref.text().strip(),
            "consent_mandate_ref": self._txt_consent_ref.text().strip(),
            "access_role_required": self._combo_role.currentText(),
        }


class SignatureWorkbenchWidget(QWidget):
    """Forensic workbench for signature detection, Hu moment analysis,
    and optical verification heuristics.
    """

    run_verification_requested = Signal()
    create_subject_requested = Signal(str, str, str)
    enroll_reference_requested = Signal(dict)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)

        self._subjects: list[AuthorizedSubjectDTO] = []
        self._references: list[SignatureReferenceDTO] = []
        self._comparisons: list[SignatureComparisonDTO] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(8)

        title_layout = QVBoxLayout()
        title_lbl = QLabel("✍️ Signature Forensics & Hu Moment Verification", self)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "VeriTrace 6-Level Epistemic Scale, Invariant Hu Moments, and Optical Stroke Analysis",
            self,
        )
        sub_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_layout.addWidget(sub_lbl)
        header_bar.addLayout(title_layout, 1)

        self._btn_verify = QPushButton("Run Signature Verification", self)
        self._btn_verify.setObjectName("primaryButton")
        self._btn_verify.clicked.connect(self.run_verification_requested.emit)
        header_bar.addWidget(self._btn_verify)

        main_layout.addLayout(header_bar)

        # Controls Bar: Signatory & Specimen Reference Selection
        controls_bar = QHBoxLayout()
        controls_bar.setSpacing(8)

        lbl_subj = QLabel("Signatory:", self)
        lbl_subj.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        controls_bar.addWidget(lbl_subj)

        self._combo_subjects = QComboBox(self)
        self._combo_subjects.addItem("All Signatories", None)
        self._combo_subjects.currentIndexChanged.connect(self._on_subject_changed)
        controls_bar.addWidget(self._combo_subjects)

        self._btn_new_subject = QPushButton("+ Signatory", self)
        self._btn_new_subject.clicked.connect(self._on_open_new_subject)
        controls_bar.addWidget(self._btn_new_subject)

        lbl_ref = QLabel("Reference Specimen:", self)
        lbl_ref.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        controls_bar.addWidget(lbl_ref)

        self._combo_references = QComboBox(self)
        self._combo_references.addItem("Auto (Pairwise / First Detected)", None)
        self._combo_references.currentIndexChanged.connect(self._on_reference_changed)
        controls_bar.addWidget(self._combo_references, 1)

        self._btn_enroll_ref = QPushButton("+ Enroll Specimen...", self)
        self._btn_enroll_ref.clicked.connect(self._on_open_enroll_dialog)
        controls_bar.addWidget(self._btn_enroll_ref)

        main_layout.addLayout(controls_bar)

        # Splitter: Left Table / Right Side-by-Side Comparison
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Table of signature comparisons
        left_box = QWidget(splitter)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        lbl_table_hdr = QLabel("DETECTED QUESTIONED SIGNATURES", left_box)
        lbl_table_hdr.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        left_layout.addWidget(lbl_table_hdr)

        self._table = QTableWidget(left_box)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Questioned Doc", "Reference Doc", "Hu Distance", "Verdict"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        left_layout.addWidget(self._table, 1)
        splitter.addWidget(left_box)

        # Right Inspection Box
        right_box = QWidget(splitter)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Crops card
        crops_card = QFrame(right_box)
        crops_card.setObjectName("card")
        crops_layout = QVBoxLayout(crops_card)
        crops_layout.setContentsMargins(10, 10, 10, 10)
        crops_layout.setSpacing(8)

        lbl_preview_hdr = QLabel("OPTICAL STROKE COMPARISON", crops_card)
        lbl_preview_hdr.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        crops_layout.addWidget(lbl_preview_hdr)

        crops_row = QHBoxLayout()
        crops_row.setSpacing(12)

        # Questioned preview
        q_layout = QVBoxLayout()
        self._lbl_q_title = QLabel("Questioned Signature", crops_card)
        self._lbl_q_title.setStyleSheet("font-weight: 600; color: #f0f6fc; font-size: 11px;")
        q_layout.addWidget(self._lbl_q_title)
        self._lbl_q_img = QLabel("No Image", crops_card)
        self._lbl_q_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_q_img.setMinimumSize(180, 110)
        self._lbl_q_img.setStyleSheet(
            "background: #090d16; border: 1px dashed #30363d; border-radius: 4px;"
        )
        q_layout.addWidget(self._lbl_q_img)
        crops_row.addLayout(q_layout)

        # Reference preview
        r_layout = QVBoxLayout()
        self._lbl_r_title = QLabel("Reference Enrolled", crops_card)
        self._lbl_r_title.setStyleSheet("font-weight: 600; color: #f0f6fc; font-size: 11px;")
        r_layout.addWidget(self._lbl_r_title)
        self._lbl_r_img = QLabel("No Image", crops_card)
        self._lbl_r_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_r_img.setMinimumSize(180, 110)
        self._lbl_r_img.setStyleSheet(
            "background: #090d16; border: 1px dashed #30363d; border-radius: 4px;"
        )
        r_layout.addWidget(self._lbl_r_img)
        crops_row.addLayout(r_layout)

        crops_layout.addLayout(crops_row)
        right_layout.addWidget(crops_card)

        # Metrics Card
        metrics_card = QFrame(right_box)
        metrics_card.setObjectName("card")
        metrics_layout = QVBoxLayout(metrics_card)
        metrics_layout.setContentsMargins(10, 10, 10, 10)
        metrics_layout.setSpacing(6)

        lbl_metric_hdr = QLabel("VERITRACE OPTICAL VERIFICATION METRICS", metrics_card)
        lbl_metric_hdr.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        metrics_layout.addWidget(lbl_metric_hdr)

        self._lbl_verdict_badge = QLabel("SELECT A COMPARISON ROW", metrics_card)
        self._lbl_verdict_badge.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #58a6ff; padding: 4px 8px; "
            "background: #161b22; border: 1px solid #30363d; border-radius: 4px;"
        )
        metrics_layout.addWidget(self._lbl_verdict_badge)

        self._lbl_hu_distance = QLabel("Hu Invariant Moments Distance: —", metrics_card)
        self._lbl_hu_distance.setStyleSheet("color: #f0f6fc; font-size: 12px;")
        metrics_layout.addWidget(self._lbl_hu_distance)

        self._bar_distance = QProgressBar(metrics_card)
        self._bar_distance.setRange(0, 100)
        self._bar_distance.setValue(0)
        self._bar_distance.setFixedHeight(8)
        self._bar_distance.setTextVisible(False)
        metrics_layout.addWidget(self._bar_distance)

        self._lbl_stroke_density = QLabel("Stroke Density Ratio: —", metrics_card)
        self._lbl_stroke_density.setStyleSheet("color: #8b949e; font-size: 11px;")
        metrics_layout.addWidget(self._lbl_stroke_density)

        self._txt_explanation = QTextEdit(metrics_card)
        self._txt_explanation.setReadOnly(True)
        self._txt_explanation.setMaximumHeight(80)
        metrics_layout.addWidget(self._txt_explanation)

        right_layout.addWidget(metrics_card)
        right_layout.addStretch()

        splitter.addWidget(right_box)
        splitter.setSizes([450, 550])

        main_layout.addWidget(splitter, 1)

    def set_subjects(self, subjects: list[AuthorizedSubjectDTO]) -> None:
        """Update available authorized signatories in dropdown."""
        self._subjects = subjects
        self._combo_subjects.blockSignals(True)
        current_data = self._combo_subjects.currentData()
        self._combo_subjects.clear()
        self._combo_subjects.addItem("All Signatories", None)
        for s in subjects:
            self._combo_subjects.addItem(f"{s.full_name} ({s.designation})", s.id)
        idx = self._combo_subjects.findData(current_data)
        if idx >= 0:
            self._combo_subjects.setCurrentIndex(idx)
        else:
            self._combo_subjects.setCurrentIndex(0)
        self._combo_subjects.blockSignals(False)
        self._update_references_combo()

    def set_references(self, references: list[SignatureReferenceDTO]) -> None:
        """Update available enrolled specimen references."""
        self._references = references
        self._update_references_combo()

    def _update_references_combo(self) -> None:
        self._combo_references.blockSignals(True)
        current_ref_id = self._combo_references.currentData()
        self._combo_references.clear()
        self._combo_references.addItem("Auto (Pairwise / First Detected)", None)

        subj_filter = self._combo_subjects.currentData()
        filtered = (
            [r for r in self._references if r.subject_id == subj_filter]
            if subj_filter
            else self._references
        )

        for r in filtered:
            subj_name = next(
                (s.full_name for s in self._subjects if s.id == r.subject_id), "Signer"
            )
            label = f"{subj_name}: {r.source_document_ref} [{r.sha256_hash[:8]}]"
            self._combo_references.addItem(label, r.id)

        idx = self._combo_references.findData(current_ref_id)
        if idx >= 0:
            self._combo_references.setCurrentIndex(idx)
        else:
            self._combo_references.setCurrentIndex(0)
        self._combo_references.blockSignals(False)

    def get_selected_reference_id(self) -> str | None:
        """Return currently selected reference profile ID, or None for auto."""
        val = self._combo_references.currentData()
        return str(val) if val else None

    def get_selected_subject_id(self) -> str | None:
        """Return currently selected subject ID, or None for all."""
        val = self._combo_subjects.currentData()
        return str(val) if val else None

    def _on_subject_changed(self, _index: int) -> None:
        self._update_references_combo()

    def _on_reference_changed(self, _index: int) -> None:
        ref_id = self.get_selected_reference_id()
        if not ref_id:
            return
        ref = next((r for r in self._references if r.id == ref_id), None)
        if ref and Path(ref.crop_image_path).exists():
            self._lbl_r_title.setText(f"Reference: {ref.source_document_ref}")
            pix_r = QPixmap(ref.crop_image_path)
            if not pix_r.isNull():
                self._lbl_r_img.setPixmap(
                    pix_r.scaled(
                        200,
                        110,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    def _on_open_new_subject(self) -> None:
        dlg = CreateAuthorizedSubjectDialog(self)
        if dlg.exec():
            name, desig, id_ref = dlg.get_data()
            self.create_subject_requested.emit(name, desig, id_ref)

    def _on_open_enroll_dialog(self) -> None:
        if not self._subjects:
            QMessageBox.information(
                self,
                "No Subjects Registered",
                "Please register an authorized signatory subject "
                "before enrolling reference specimens.",
            )
            return
        selected_subj_id = self.get_selected_subject_id()
        dlg = EnrollSignatureReferenceDialog(
            subjects=self._subjects,
            parent=self,
            preselected_subject_id=selected_subj_id,
        )
        if dlg.exec():
            data = dlg.get_data()
            self.enroll_reference_requested.emit(data)

    def set_comparisons(self, comparisons: list[SignatureComparisonDTO]) -> None:
        """Populate table with signature verification comparisons."""
        self._comparisons = comparisons
        self._table.setRowCount(len(comparisons))

        for row, c in enumerate(comparisons):
            self._table.setItem(row, 0, QTableWidgetItem(c.questioned_doc_name))
            self._table.setItem(row, 1, QTableWidgetItem(c.reference_doc_name))
            self._table.setItem(row, 2, QTableWidgetItem(f"{c.hu_distance:.3f}"))
            self._table.setItem(row, 3, QTableWidgetItem(c.assessment_level.replace("_", " ")))

        if comparisons:
            self._table.selectRow(0)

    def _on_row_selected(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self._comparisons):
            return

        c = self._comparisons[row]
        self._lbl_q_title.setText(f"Questioned: {c.questioned_doc_name}")
        self._lbl_r_title.setText(f"Reference: {c.reference_doc_name}")

        # Load Questioned Crop
        if Path(c.questioned_crop_path).exists():
            pix_q = QPixmap(c.questioned_crop_path)
            if not pix_q.isNull():
                self._lbl_q_img.setPixmap(
                    pix_q.scaled(
                        200,
                        110,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._lbl_q_img.setText("Invalid Crop")
        else:
            self._lbl_q_img.setText("File Not Found")

        # Load Reference Crop
        if Path(c.reference_crop_path).exists():
            pix_r = QPixmap(c.reference_crop_path)
            if not pix_r.isNull():
                self._lbl_r_img.setPixmap(
                    pix_r.scaled(
                        200,
                        110,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self._lbl_r_img.setText("Invalid Crop")
        else:
            self._lbl_r_img.setText("File Not Found")

        # Verdict Badge & Colors
        verdict = c.assessment_level.replace("_", " ")
        if "IDENTIFICATION" in c.assessment_level:
            color = "#3fb950"
            bg = "#1f4028"
        elif "INCONCLUSIVE" in c.assessment_level or "INSUFFICIENT" in c.assessment_level:
            color = "#e3b341"
            bg = "#3d3014"
        else:
            color = "#f85149"
            bg = "#491d1e"

        self._lbl_verdict_badge.setText(f"VERDICT: {verdict}")
        self._lbl_verdict_badge.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {color}; padding: 5px 10px; "
            f"background: {bg}; border: 1px solid {color}; border-radius: 4px;"
        )

        self._lbl_hu_distance.setText(f"Hu Invariant Moments Distance: <b>{c.hu_distance:.4f}</b>")
        pct = min(100, int(c.hu_distance * 100))
        self._bar_distance.setValue(pct)
        self._lbl_stroke_density.setText(
            f"Stroke Density Ratio: <b>{c.stroke_density_ratio:.2f}</b>"
        )
        self._txt_explanation.setPlainText(c.explanation)
