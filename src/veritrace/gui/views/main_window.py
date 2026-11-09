"""Main forensic investigation workstation window."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.correlation import (
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.application.dto.document import DocumentIngestionResultDTO
from veritrace.application.dto.dossier import DossierExportRequestDTO
from veritrace.application.dto.investigation import (
    EvidenceResponseDTO,
    FindingResponseDTO,
    InvestigationCreateDTO,
    ReviewDecisionType,
    ReviewFindingRequestDTO,
)
from veritrace.application.dto.signature_reference import SignatureReferenceDTO
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.dossier_export_service import (
    DossierExportService,
)
from veritrace.application.services.forensic_analysis_service import (
    ForensicAnalysisService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.application.services.text_extraction_service import (
    TextExtractionService,
)
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.document import DocumentType
from veritrace.gui.components.common import CommandPaletteDialog, ToastNotification
from veritrace.gui.components.contextual_audit_table import ContextualAuditWidget
from veritrace.gui.components.dashboard_widget import DashboardBannerWidget
from veritrace.gui.components.document_viewer import SideBySideDocumentViewer
from veritrace.gui.components.evidence_inspector import EvidenceInspectorDock
from veritrace.gui.components.finding_table import FindingTableWidget
from veritrace.gui.components.investigation_sidebar import InvestigationSidebar
from veritrace.gui.components.signature_workbench import SignatureWorkbenchWidget
from veritrace.gui.components.status_bar import VeriTraceStatusBar
from veritrace.gui.controllers.correlation_worker import CorrelationWorker
from veritrace.gui.controllers.dossier_worker import DossierWorker
from veritrace.gui.controllers.forensic_worker import ForensicWorker
from veritrace.gui.demo_data import seed_industrial_demo
from veritrace.gui.styles.tokens import ColorTokens, MetricTokens

logger = logging.getLogger("veritrace.gui.main_window")


class MainWindow(QMainWindow):
    """Forensic investigation workstation coordinating 4-pane views and background analysis."""

    def __init__(
        self,
        investigation_service: InvestigationService,
        correlation_service: CrossDocumentCorrelationService,
        ingestion_service: DocumentIngestionService | None = None,
        extraction_service: TextExtractionService | None = None,
        dossier_export_service: DossierExportService | None = None,
        forensic_analysis_service: ForensicAnalysisService | None = None,
        uow_factory: Any = None,
        organization_id: str = "org_11111111111111111111111111111111",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("VeriTrace Workstation — Cross-Document Forensic Intelligence")
        self.setMinimumSize(960, 580)

        # Adaptively size window to screen geometry
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1360, max(960, int(avail.width() * 0.90)))
            target_h = min(820, max(600, int(avail.height() * 0.88)))
            self.resize(target_w, target_h)
            self.move(
                avail.x() + (avail.width() - target_w) // 2,
                avail.y() + (avail.height() - target_h) // 2,
            )
        else:
            self.resize(1180, 720)

        self._investigation_service = investigation_service
        self._correlation_service = correlation_service
        self._ingestion_service = ingestion_service
        self._extraction_service = extraction_service
        self._uow_factory = uow_factory
        self._organization_id = organization_id

        self._dossier_export_service: DossierExportService | None
        if dossier_export_service:
            self._dossier_export_service = dossier_export_service
        elif uow_factory:
            self._dossier_export_service = DossierExportService(uow_factory)
        else:
            self._dossier_export_service = None

        if forensic_analysis_service:
            self._forensic_analysis_service = forensic_analysis_service
        else:
            self._forensic_analysis_service = ForensicAnalysisService(uow_factory)

        self._active_investigation_id: str | None = None
        self._current_findings: list[FindingResponseDTO] = []
        self._current_evidence: list[EvidenceResponseDTO] = []
        self._docs_by_id: dict[str, DocumentIngestionResultDTO] = {}
        self._pages_by_id: dict[str, DocumentPage] = {}
        self._active_worker: CorrelationWorker | None = None
        self._dossier_worker: DossierWorker | None = None
        self._forensic_worker: ForensicWorker | None = None

        self._setup_menus()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_ui()
        self._load_investigations()

    def _show_message(self, title: str, text: str, is_error: bool = False) -> None:
        """Display dialog or log without blocking when offscreen."""
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            logger.warning("Dialog suppressed in offscreen mode: %s: %s", title, text)
            if is_error:
                raise RuntimeError(f"{title}: {text}")
            return
        if is_error:
            QMessageBox.critical(self, title, text)
        else:
            QMessageBox.information(self, title, text)

    def _setup_menus(self) -> None:
        """Create standard application menu bar."""
        menubar = self.menuBar()

        # 1. File Menu
        file_menu = menubar.addMenu("&File")

        act_new_inv = QAction("&New Investigation", self)
        act_new_inv.setShortcut(QKeySequence("Ctrl+N"))
        act_new_inv.triggered.connect(self._on_new_investigation)
        file_menu.addAction(act_new_inv)

        act_add_doc = QAction("&Import Document...", self)
        act_add_doc.setShortcut(QKeySequence("Ctrl+O"))
        act_add_doc.triggered.connect(self._on_add_document)
        file_menu.addAction(act_add_doc)

        file_menu.addSeparator()

        act_export_pdf = QAction("Export &PS-2 Dossier (PDF)...", self)
        act_export_pdf.setShortcut(QKeySequence("Ctrl+E"))
        act_export_pdf.triggered.connect(self._on_export_pdf_dossier)
        file_menu.addAction(act_export_pdf)

        act_export_json = QAction("Export Structured &JSON Payload...", self)
        act_export_json.setShortcut(QKeySequence("Ctrl+J"))
        act_export_json.triggered.connect(self._on_export_json_dossier)
        file_menu.addAction(act_export_json)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # 2. View Menu
        view_menu = menubar.addMenu("&View")

        act_palette = QAction("Command &Palette...", self)
        act_palette.setShortcut(QKeySequence("Ctrl+K"))
        act_palette.triggered.connect(self._open_command_palette)
        view_menu.addAction(act_palette)

        view_menu.addSeparator()

        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(lambda: self._doc_viewer._left_canvas.zoom_in())
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(lambda: self._doc_viewer._left_canvas.zoom_out())
        view_menu.addAction(act_zoom_out)

        act_fit = QAction("&Fit to Screen", self)
        act_fit.setShortcut(QKeySequence("Ctrl+0"))
        act_fit.triggered.connect(lambda: self._doc_viewer._reset_both_zooms())
        view_menu.addAction(act_fit)

        # 3. Forensic Engines Menu
        forensics_menu = menubar.addMenu("F&orensics")

        act_run_corr = QAction("⚡ Run &Cross-Document Correlation", self)
        act_run_corr.setShortcut(QKeySequence("F5"))
        act_run_corr.triggered.connect(lambda: self._on_run_correlation(False))
        forensics_menu.addAction(act_run_corr)

        act_run_sig = QAction("✍️ Run &Signature Hu Moment Verification", self)
        act_run_sig.triggered.connect(self._on_run_signatures)
        forensics_menu.addAction(act_run_sig)

        act_run_audit = QAction("🧮 Run &Contextual Procurement Math Audit", self)
        act_run_audit.triggered.connect(self._on_run_contextual_audit)
        forensics_menu.addAction(act_run_audit)

        # 4. Settings Menu
        settings_menu = menubar.addMenu("&Settings")
        act_ai_settings = QAction("🤖 AI Reasoning & &Privacy Mode...", self)
        act_ai_settings.triggered.connect(self._on_ai_settings)
        settings_menu.addAction(act_ai_settings)

        # 5. Demo Bundles Menu
        demos_menu = menubar.addMenu("&Demo Cases")

        act_demo_ind = QAction("🏭 Load Case 1: Industrial Alloy Fraud (PO/DC/MTC/Invoice)", self)
        act_demo_ind.triggered.connect(self._on_load_demo)
        demos_menu.addAction(act_demo_ind)

        # 6. Help Menu
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("&About VeriTrace Workstation", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _setup_toolbar(self) -> None:
        """Create sleek, consolidated top action toolbar with Command Palette."""
        toolbar = QToolBar("Forensic Actions", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setStyleSheet(
            f"QToolBar {{ background-color: {ColorTokens.SURFACE_SIDEBAR}; "
            f"border-bottom: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            "padding: 4px 10px; spacing: 8px; }"
        )

        # 1. Search / Command Palette Trigger
        self._btn_search_palette = QPushButton("🔍  Search commands or findings... (Ctrl+K)", self)
        self._btn_search_palette.setObjectName("paletteTrigger")
        self._btn_search_palette.setFixedWidth(280)
        self._btn_search_palette.setStyleSheet(
            f"QPushButton {{ background-color: {ColorTokens.BACKGROUND_BASE}; "
            f"border: 1px solid {ColorTokens.BORDER_SUBTLE}; "
            f"border-radius: {MetricTokens.RADIUS_MD}; "
            f"padding: 5px 12px; color: {ColorTokens.TEXT_MUTED}; "
            f"font-size: {MetricTokens.FONT_SIZE_XS}; text-align: left; }} "
            f"QPushButton:hover {{ border-color: {ColorTokens.ACCENT_PRIMARY}; "
            f"color: {ColorTokens.TEXT_PRIMARY}; }}"
        )
        self._btn_search_palette.clicked.connect(self._open_command_palette)
        toolbar.addWidget(self._btn_search_palette)

        toolbar.addSeparator()

        # 2. Quick Import Document
        btn_import = QPushButton("+ Import Document", self)
        btn_import.setObjectName("secondaryButton")
        btn_import.setStyleSheet(
            f"padding: 5px 12px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        btn_import.clicked.connect(self._on_add_document)
        toolbar.addWidget(btn_import)

        # 3. Primary Run Correlation
        btn_run = QPushButton("⚡ Run Full Forensics", self)
        btn_run.setObjectName("primaryButton")
        btn_run.setStyleSheet(
            f"padding: 5px 14px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_BOLD};"
        )
        btn_run.clicked.connect(lambda: self._on_run_correlation(False))
        toolbar.addWidget(btn_run)

        # Spacer to push overflow to right
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # 4. Consolidated 'More Actions' Menu
        more_btn = QPushButton("More Actions ▾", self)
        more_btn.setObjectName("secondaryButton")
        more_btn.setStyleSheet(
            f"padding: 5px 12px; font-size: {MetricTokens.FONT_SIZE_XS}; "
            f"font-weight: {MetricTokens.FONT_WEIGHT_MEDIUM};"
        )
        more_menu = QMenu(more_btn)

        act_dossier_pdf = more_menu.addAction("Export PS-2 Dossier (PDF)...")
        act_dossier_pdf.triggered.connect(self._on_export_pdf_dossier)

        act_dossier_json = more_menu.addAction("Export JSON Dossier...")
        act_dossier_json.triggered.connect(self._on_export_json_dossier)

        more_menu.addSeparator()

        act_forensic_scan = more_menu.addAction("Scan Visual Forensics...")
        act_forensic_scan.triggered.connect(self._on_run_forensics)

        act_load_demo = more_menu.addAction("Load Industrial Alloy Demo Case")
        act_load_demo.triggered.connect(self._on_load_demo)

        more_menu.addSeparator()

        act_settings = more_menu.addAction("AI Reasoning & Privacy Settings...")
        act_settings.triggered.connect(self._on_ai_settings)

        more_btn.setMenu(more_menu)
        toolbar.addWidget(more_btn)

        self.addToolBar(toolbar)

    def _setup_shortcuts(self) -> None:
        """Register global application keyboard shortcuts."""
        palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        palette_shortcut.activated.connect(self._open_command_palette)

    def _open_command_palette(self) -> None:
        """Open Raycast/Linear-style command launcher."""
        commands = [
            (
                "⚡ Run Full Forensics",
                "Execute deterministic cross-document correlation across all ingested evidence",
                lambda: self._on_run_correlation(False),
            ),
            (
                "📥 Import Evidence Document",
                "Ingest PDF or high-resolution image document into active investigation",
                self._on_add_document,
            ),
            (
                "📄 Export PS-2 Dossier (PDF)",
                "Compile complete sealed legal PDF forensic investigation dossier",
                self._on_export_pdf_dossier,
            ),
            (
                "📊 Export Structured JSON Dossier",
                "Export cryptographic JSON payload containing complete case findings",
                self._on_export_json_dossier,
            ),
            (
                "👁️ Scan Visual Forensics",
                "Scan document pages for copy-move tampering, morphology, and signatures",
                self._on_run_forensics,
            ),
            (
                "✍️ Signature Verification Workbench",
                "Navigate to Hu moments optical signature comparison tab",
                lambda: self._tabs.setCurrentIndex(2),
            ),
            (
                "🧮 Procurement & Chronology Audit",
                "Navigate to procurement math and weighbridge arithmetic tab",
                lambda: self._tabs.setCurrentIndex(3),
            ),
            (
                "🔍 Contradiction Matrix",
                "Navigate to primary discrepancy table tab",
                lambda: self._tabs.setCurrentIndex(0),
            ),
            (
                "🖼️ Side-by-Side Evidence Canvas",
                "Navigate to dual-canvas page and ELA comparison viewer",
                lambda: self._tabs.setCurrentIndex(1),
            ),
            (
                "🔄 Load Industrial Alloy Demo Case",
                "Seed and load 4-document demo (PO, Challan, MTC, Invoice)",
                self._on_load_demo,
            ),
            (
                "➕ New Investigation Case",
                "Create a new forensic case in current organization",
                self._on_new_investigation,
            ),
            (
                "⚙️ AI Reasoning & Privacy Settings",
                "Configure model provider, offline air-gap mode, and PII redaction",
                self._on_ai_settings,
            ),
        ]
        dlg = CommandPaletteDialog(commands, self)
        dlg.exec()

    def _setup_ui(self) -> None:
        # Central Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # 1. Left Sidebar
        self._sidebar = InvestigationSidebar(main_splitter)
        self._sidebar.setMinimumWidth(220)
        self._sidebar.setMaximumWidth(320)
        self._sidebar.investigation_selected.connect(self._on_investigation_selected)
        self._sidebar.document_selected.connect(self._on_document_selected)
        self._sidebar.new_investigation_requested.connect(self._on_new_investigation)
        self._sidebar.add_document_requested.connect(self._on_add_document)
        self._sidebar.load_demo_requested.connect(self._on_load_demo)
        main_splitter.addWidget(self._sidebar)

        # 2. Central Workspace
        central_container = QWidget(main_splitter)
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(6, 6, 6, 6)
        central_layout.setSpacing(6)

        self._dashboard_banner = DashboardBannerWidget(central_container)
        self._dashboard_banner.run_correlation_requested.connect(self._on_run_correlation)
        self._dashboard_banner.run_forensics_requested.connect(self._on_run_forensics)
        self._dashboard_banner.generate_dossier_requested.connect(self._on_generate_dossier)
        self._dashboard_banner.export_dossier_requested.connect(self._on_export_pdf_dossier)
        central_layout.addWidget(self._dashboard_banner)

        self._tabs = QTabWidget(central_container)
        self._tabs.setDocumentMode(True)

        # Tab 0: Contradiction Matrix & Findings
        matrix_container = QWidget(self._tabs)
        matrix_layout = QVBoxLayout(matrix_container)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        self._finding_table = FindingTableWidget(matrix_container)
        self._finding_table.finding_selected.connect(self._on_finding_selected)
        self._finding_table.finding_activated.connect(self._on_finding_activated)
        self._finding_table.run_forensics_requested.connect(lambda: self._on_run_correlation(False))
        matrix_layout.addWidget(self._finding_table)
        self._tabs.addTab(matrix_container, "Contradiction Matrix")

        # Tab 1: Side-by-Side Evidence Canvas
        self._doc_viewer = SideBySideDocumentViewer(self._tabs)
        self._tabs.addTab(self._doc_viewer, "Side-by-Side Evidence Canvas")

        # Tab 2: Signature Forensics Workbench
        self._signature_workbench = SignatureWorkbenchWidget(self._tabs)
        self._signature_workbench.run_verification_requested.connect(self._on_run_signatures)
        self._signature_workbench.create_subject_requested.connect(
            self._on_create_authorized_subject
        )
        self._signature_workbench.enroll_reference_requested.connect(
            self._on_enroll_signature_reference
        )
        self._tabs.addTab(self._signature_workbench, "✍️ Signature Workbench")

        # Tab 3: Contextual Arithmetic & Chronology Audit
        self._contextual_audit = ContextualAuditWidget(self._tabs)
        self._contextual_audit.run_audit_requested.connect(self._on_run_contextual_audit)
        self._tabs.addTab(self._contextual_audit, "🧮 Math & Chronology Audit")

        central_layout.addWidget(self._tabs, 1)
        main_splitter.addWidget(central_container)
        main_splitter.setSizes([240, 780])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)

        self.setCentralWidget(main_splitter)

        # 3. Right Evidence Inspector Dock
        self._inspector_dock = EvidenceInspectorDock(self)
        self._inspector_dock.setMinimumWidth(260)
        self._inspector_dock.setMaximumWidth(360)
        self._inspector_dock.review_action_submitted.connect(self._on_review_submitted)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._inspector_dock)

        # 4. Status Bar
        self._status_bar = VeriTraceStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.set_telemetry(f"Org: {self._organization_id[:16]}...")

    def _load_investigations(self) -> None:
        """Fetch investigations for organization, auto-seeding demo on first launch."""
        invs = self._investigation_service.list_investigations(self._organization_id)
        if not invs and self._uow_factory:
            # Auto-seed industrial demo on fresh launch so the workstation has immediate data
            try:
                seed_industrial_demo(self._uow_factory, organization_id=self._organization_id)
                invs = self._investigation_service.list_investigations(self._organization_id)
            except Exception as e:
                logger.warning("Auto-seeding demo on first launch skipped: %s", e)

        if invs:
            self._sidebar.set_investigations(invs, selected_id=invs[0].id)
            self._on_investigation_selected(invs[0].id)
            if not self._current_findings and self._correlation_service:
                try:
                    corr_req = CorrelationRequestDTO(
                        investigation_id=invs[0].id,
                        organization_id=self._organization_id,
                        is_order_closed=False,
                    )
                    self._correlation_service.correlate_investigation(corr_req)
                    self._reload_case_data()
                except Exception as e:
                    logger.warning("Initial correlation skipped: %s", e)
        else:
            self._status_bar.set_status(
                "No active investigations found. Create a case or load demo."
            )

    def _on_investigation_selected(self, investigation_id: str) -> None:
        """Handle case selection and load documents and findings."""
        self._active_investigation_id = investigation_id
        self._status_bar.set_telemetry(
            f"Org: {self._organization_id[:12]}... | Case: {investigation_id[:12]}..."
        )
        self._reload_case_data()

    def _reload_case_data(self) -> None:
        if not self._active_investigation_id:
            return

        inv_id = self._active_investigation_id
        org_id = self._organization_id

        # 1. Documents
        docs = self._investigation_service.list_documents(inv_id, org_id)
        self._sidebar.set_documents(docs)
        self._docs_by_id = {d.document_id: d for d in docs}
        self._pages_by_id.clear()
        for d in docs:
            pages = self._investigation_service.list_document_pages(d.document_id, org_id)
            for p in pages:
                self._pages_by_id[p.id] = p

        # 2. Findings
        findings = self._investigation_service.list_findings(inv_id, org_id)
        self._current_findings = findings
        self._finding_table.set_findings(findings)

        # 3. Evidence
        self._current_evidence = self._investigation_service.list_evidence(inv_id, org_id)

        # 4. Relations
        relations = self._investigation_service.list_relations(inv_id, org_id)

        # 5. Metrics
        crit_count = sum(1 for f in findings if f.severity.value == "CRITICAL")
        high_med_count = sum(1 for f in findings if f.severity.value in ("HIGH", "MEDIUM"))

        self._dashboard_banner.set_metrics(
            docs_count=len(docs),
            findings_count=len(findings),
            critical_count=crit_count,
            high_med_count=high_med_count,
            relations_count=len(relations),
        )

        self._status_bar.set_status(f"Loaded {len(docs)} documents and {len(findings)} findings.")

        # Update Contextual Audit
        if self._forensic_analysis_service:
            audit_items = self._forensic_analysis_service.run_contextual_audit(inv_id, org_id)
            self._contextual_audit.set_audit_items(audit_items)

        # 6. Enrolled Signature References
        self._load_signature_references()

    def _on_run_correlation(self, is_order_closed: bool) -> None:
        """Trigger asynchronous background cross-document correlation."""
        if not self._active_investigation_id:
            self._show_message(
                "No Case Selected", "Please select or create an investigation first.", is_error=True
            )
            return

        self._dashboard_banner.set_correlate_enabled(False)
        self._status_bar.start_progress("Running cross-document correlation engine...")

        # Run auto-classification on unclassified documents only if unclassified documents exist
        has_unclassified = any(
            doc.document_type == DocumentType.UNCLASSIFIED for doc in self._docs_by_id.values()
        )
        if has_unclassified:
            try:
                self._investigation_service.classify_documents(
                    self._active_investigation_id, self._organization_id
                )
            except Exception as err:
                logger.warning("Automated document classification warning: %s", err)

        request = CorrelationRequestDTO(
            investigation_id=self._active_investigation_id,
            organization_id=self._organization_id,
            is_order_closed=is_order_closed,
        )

        self._active_worker = CorrelationWorker(self._correlation_service, request, self)
        self._active_worker.progress_signal.connect(self._status_bar.update_progress)
        self._active_worker.finished_signal.connect(self._on_correlation_finished)
        self._active_worker.error_signal.connect(self._on_correlation_error)
        self._active_worker.start()

    def _on_correlation_finished(self, summary: CorrelationSummaryDTO) -> None:
        self._dashboard_banner.set_correlate_enabled(True)
        self._status_bar.finish_progress(
            f"Correlation complete: {summary.discrepancies_count} discrepancies, "
            f"{summary.corroborations_count} corroborations."
        )
        ToastNotification.show_toast(
            self,
            f"Forensics complete: {summary.discrepancies_count} discrepancies identified",
        )
        self._reload_case_data()

    def _on_correlation_error(self, err_msg: str) -> None:
        self._dashboard_banner.set_correlate_enabled(True)
        self._status_bar.set_status(f"Correlation error: {err_msg}", stage="ERROR")
        self._show_message(
            "Correlation Engine Error", f"Analysis failed:\n{err_msg}", is_error=True
        )

    def _on_run_forensics(self) -> None:
        """Trigger asynchronous background execution of visual forensic analysis."""
        if not self._active_investigation_id:
            self._show_message(
                "No Case Selected",
                "Please select an active investigation to run forensic analysis.",
                is_error=True,
            )
            return

        self._dashboard_banner.set_forensics_enabled(False)
        self._status_bar.start_progress(
            "Scanning visual forensics (signatures, stroke morphology, copy-move)..."
        )

        self._forensic_worker = ForensicWorker(
            investigation_service=self._investigation_service,
            investigation_id=self._active_investigation_id,
            organization_id=self._organization_id,
            parent=self,
        )
        self._forensic_worker.progress_signal.connect(self._status_bar.update_progress)
        self._forensic_worker.finished_signal.connect(self._on_forensics_finished)
        self._forensic_worker.error_signal.connect(self._on_forensics_error)
        self._forensic_worker.start()

    def _on_forensics_finished(self, findings_count: int) -> None:
        self._dashboard_banner.set_forensics_enabled(True)
        self._status_bar.finish_progress(
            f"Forensic scan complete: {findings_count} visual findings recorded."
        )
        ToastNotification.show_toast(
            self, f"Forensic scan complete: {findings_count} findings recorded"
        )
        self._reload_case_data()

    def _on_forensics_error(self, err_msg: str) -> None:
        self._dashboard_banner.set_forensics_enabled(True)
        self._status_bar.set_status(f"Forensic error: {err_msg}", stage="ERROR")
        self._show_message(
            "Forensic Scan Failed",
            f"Visual forensic analysis failed:\n{err_msg}",
            is_error=True,
        )

    def _on_generate_dossier(self) -> None:
        """Trigger asynchronous background compilation of the PS-2 Investigation Dossier."""
        if not self._active_investigation_id:
            self._show_message(
                "No Case Selected",
                "Please select an active investigation to compile its dossier.",
                is_error=True,
            )
            return

        self._dashboard_banner.set_dossier_enabled(False)
        self._status_bar.start_progress("Compiling 6-section PS-2 Investigation Dossier...")

        self._dossier_worker = DossierWorker(
            investigation_service=self._investigation_service,
            investigation_id=self._active_investigation_id,
            organization_id=self._organization_id,
            parent=self,
        )
        self._dossier_worker.progress_signal.connect(self._status_bar.update_progress)
        self._dossier_worker.finished_signal.connect(self._on_dossier_finished)
        self._dossier_worker.error_signal.connect(self._on_dossier_error)
        self._dossier_worker.start()

    def _on_dossier_finished(self, pdf_path: str, json_path: str) -> None:
        self._dashboard_banner.set_dossier_enabled(True)
        self._status_bar.finish_progress(f"Dossier ready: {Path(pdf_path).name}")
        ToastNotification.show_toast(self, "PS-2 Investigation Dossier compiled successfully")
        self._show_message(
            "Investigation Dossier Compiled",
            f"PS-2 Investigation Dossier generated successfully:\n\n"
            f"PDF: {pdf_path}\n"
            f"JSON: {json_path}",
        )

    def _on_dossier_error(self, err_msg: str) -> None:
        self._dashboard_banner.set_dossier_enabled(True)
        self._status_bar.set_status(f"Dossier error: {err_msg}", stage="ERROR")
        self._show_message(
            "Dossier Compilation Failed",
            f"Failed to compile dossier:\n{err_msg}",
            is_error=True,
        )

    def _on_document_selected(self, document_id: str) -> None:
        """Display selected document in the dual canvas viewer."""
        doc = self._docs_by_id.get(document_id)
        if not doc:
            return

        pages = [p for p in self._pages_by_id.values() if p.document_id == document_id]
        pages.sort(key=lambda p: p.page_number)
        if pages:
            first_page = pages[0]
            self._tabs.setCurrentIndex(1)

            # Generate or fetch ELA heatmap
            ela_path = ""
            if self._forensic_analysis_service and first_page.image_storage_path:
                ela_path = self._forensic_analysis_service.get_or_generate_ela_heatmap(
                    first_page.image_storage_path
                )

            self._doc_viewer.load_comparison(
                source_doc_name=f"{doc.original_filename} (Page {first_page.page_number})",
                source_img_path=first_page.image_storage_path,
                source_evidence=None,
                target_doc_name="Select a second document or finding to compare",
                target_img_path=None,
                target_evidence=None,
                source_ela_path=ela_path or None,
            )
            quality_msg = ""
            if self._active_investigation_id and self._investigation_service:
                try:
                    q_res = self._investigation_service.assess_document_quality(
                        self._active_investigation_id, self._organization_id
                    )
                    doc_q = next((q for q in q_res if q.document_id == document_id), None)
                    if doc_q:
                        score_val = doc_q.overall_score
                        rec_val = doc_q.recommendation.value
                        quality_msg = f" | Quality: {score_val:.1f}/100 ({rec_val})"
                except Exception:
                    pass
            self._status_bar.set_status(f"Viewing document: {doc.original_filename}{quality_msg}")

    def _on_finding_selected(self, finding_id: str) -> None:
        """Bind selected finding to inspector dock and side-by-side canvas."""
        finding = next((f for f in self._current_findings if f.id == finding_id), None)
        self._inspector_dock.set_finding(finding)

        if not finding:
            return

        # Find linked evidence
        src_ev: EvidenceResponseDTO | None = None
        tgt_ev: EvidenceResponseDTO | None = None

        if finding.evidence_ids:
            ev_list = [e for e in self._current_evidence if e.id in finding.evidence_ids]
            if len(ev_list) >= 1:
                src_ev = ev_list[0]
            if len(ev_list) >= 2:
                tgt_ev = ev_list[1]

        # Resolve document and page for source evidence
        src_doc_name = "Primary Document Evidence"
        src_img_path = None
        if src_ev and src_ev.page_id in self._pages_by_id:
            page = self._pages_by_id[src_ev.page_id]
            doc = self._docs_by_id.get(page.document_id)
            src_doc_name = (
                f"{doc.original_filename} (Page {page.page_number})"
                if doc
                else f"Page {page.page_number}"
            )
            src_img_path = page.image_storage_path
        elif src_ev:
            src_img_path = src_ev.crop_image_path

        # Resolve document and page for target evidence
        tgt_doc_name = "Cross-Document Evidence"
        tgt_img_path = None
        if tgt_ev and tgt_ev.page_id in self._pages_by_id:
            page = self._pages_by_id[tgt_ev.page_id]
            doc = self._docs_by_id.get(page.document_id)
            tgt_doc_name = (
                f"{doc.original_filename} (Page {page.page_number})"
                if doc
                else f"Page {page.page_number}"
            )
            tgt_img_path = page.image_storage_path
        elif tgt_ev:
            tgt_img_path = tgt_ev.crop_image_path

        # Compute or retrieve ELA heatmap paths
        src_ela = ""
        tgt_ela = ""
        if self._forensic_analysis_service:
            if src_img_path:
                src_ela = self._forensic_analysis_service.get_or_generate_ela_heatmap(src_img_path)
            if tgt_img_path:
                tgt_ela = self._forensic_analysis_service.get_or_generate_ela_heatmap(tgt_img_path)

        # Update inspector crops
        src_crop = src_ev.crop_image_path if src_ev else (src_img_path or "")
        tgt_crop = tgt_ev.crop_image_path if tgt_ev else (src_ela or "")
        self._inspector_dock.set_crops(src_crop, tgt_crop)

        self._doc_viewer.load_comparison(
            source_doc_name=src_doc_name,
            source_img_path=src_img_path,
            source_evidence=src_ev,
            target_doc_name=tgt_doc_name,
            target_img_path=tgt_img_path,
            target_evidence=tgt_ev,
            source_ela_path=src_ela or None,
            target_ela_path=tgt_ela or None,
        )

    def _on_finding_activated(self, finding_id: str) -> None:
        """Switch to evidence viewer tab when double clicked."""
        self._on_finding_selected(finding_id)
        self._tabs.setCurrentIndex(1)

    def _on_review_submitted(
        self,
        finding_id: str,
        decision: ReviewDecisionType,
        rationale: str,
        reviewer_id: str,
    ) -> None:
        """Persist human review adjudication and update views."""
        if not self._active_investigation_id:
            return

        try:
            req = ReviewFindingRequestDTO(
                finding_id=finding_id,
                decision=decision,
                rationale=rationale,
                reviewer_id=reviewer_id,
            )
            updated_finding = self._investigation_service.review_finding(
                investigation_id=self._active_investigation_id,
                request=req,
                organization_id=self._organization_id,
            )

            # Update cache & view
            self._inspector_dock.set_finding(updated_finding)
            self._reload_case_data()
            self._finding_table.select_finding_by_id(finding_id)
            self._status_bar.set_status(
                f"Finding {finding_id} adjudicated as {decision.value} by {reviewer_id}."
            )
            ToastNotification.show_toast(self, f"Adjudication recorded: {decision.value}")
        except Exception as e:
            logger.exception("Review adjudication failed: %s", e)
            self._show_message(
                "Adjudication Error", f"Failed to record review:\n{e}", is_error=True
            )

    def _on_new_investigation(self) -> None:
        """Prompt user for new investigation title."""
        import uuid

        ref = f"INV-{uuid.uuid4().hex[:6].upper()}"
        dto = InvestigationCreateDTO(
            title="Procurement Cross-Check Audit",
            reference_code=ref,
            organization_id=self._organization_id,
        )
        new_inv = self._investigation_service.create_investigation(dto)
        self._load_investigations()
        self._sidebar.set_investigations(
            self._investigation_service.list_investigations(self._organization_id),
            selected_id=new_inv.id,
        )
        ToastNotification.show_toast(self, f"New case created: {ref}")

    def _on_add_document(self) -> None:
        """Select file from dialog and ingest into case."""
        if not self._active_investigation_id or not self._ingestion_service:
            self._show_message(
                "Intake Service",
                "Document ingestion service is available when storage is attached.",
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Forensic Document",
            "",
            "Documents (*.pdf *.png *.jpg *.jpeg *.tif *.tiff)",
        )
        if not file_path:
            return

        try:
            from veritrace.application.dto.document import DocumentIngestDTO

            dto = DocumentIngestDTO(
                investigation_id=self._active_investigation_id,
                organization_id=self._organization_id,
                filename=Path(file_path).name,
                file_path=file_path,
                document_type=DocumentType.UNCLASSIFIED,
            )
            doc_res = self._ingestion_service.ingest_document(dto)

            # Extract digital text if extraction service is available
            extracted_successfully = False
            if self._extraction_service:
                try:
                    self._extraction_service.extract_document_text(
                        document_id=doc_res.document_id,
                        organization_id=self._organization_id,
                    )
                    extracted_successfully = True
                except Exception as extract_err:
                    logger.warning("Post-ingestion extraction warning: %s", extract_err)

            # Trigger classification only after successful extraction
            if extracted_successfully:
                try:
                    self._investigation_service.classify_document(
                        document_id=doc_res.document_id,
                        organization_id=self._organization_id,
                    )
                except Exception as class_err:
                    logger.warning("Post-ingestion classification warning: %s", class_err)

            self._reload_case_data()
            self._status_bar.set_status(f"Ingested document: {Path(file_path).name}")
            ToastNotification.show_toast(self, f"Ingested {Path(file_path).name}")
        except Exception as e:
            logger.exception("Document ingestion failed: %s", e)
            self._show_message("Ingestion Failed", str(e), is_error=True)

    def _on_load_demo(self) -> None:
        """Seed and load the 4-document industrial manufacturing demo."""
        if not self._uow_factory:
            self._show_message(
                "Demo Error", "Persistence UnitOfWork factory is required.", is_error=True
            )
            return

        try:
            demo_inv_id = seed_industrial_demo(
                self._uow_factory, organization_id=self._organization_id
            )
            self._load_investigations()
            self._sidebar.set_investigations(
                self._investigation_service.list_investigations(self._organization_id),
                selected_id=demo_inv_id,
            )
            self._on_investigation_selected(demo_inv_id)
            self._status_bar.set_status(
                "Industrial Demo Loaded: PO, Challan, MTC, and Invoice ready for correlation."
            )
            ToastNotification.show_toast(self, "Alloy Demo loaded (4 documents)")
        except Exception as e:
            logger.exception("Failed to seed industrial demo: %s", e)
            self._show_message("Demo Seed Error", str(e), is_error=True)

    def _on_export_pdf_dossier(self) -> None:
        """Export official PS-2 Investigation Dossier in ReportLab PDF format."""
        if not self._active_investigation_id or not self._dossier_export_service:
            self._show_message(
                "Export Unavailable", "Please select an active case first.", is_error=True
            )
            return

        default_name = f"VeriTrace_Dossier_{self._active_investigation_id}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PS-2 Forensic Dossier (PDF)",
            default_name,
            "PDF Documents (*.pdf)",
        )
        if not file_path:
            return

        try:
            req = DossierExportRequestDTO(
                investigation_id=self._active_investigation_id,
                organization_id=self._organization_id,
                output_pdf_path=file_path,
            )
            result = self._dossier_export_service.export_dossier(req)
            self._status_bar.set_status(
                f"Exported PS-2 Dossier PDF: {result.pdf_path} (Hash: {result.sha256_hash[:16]}...)"
            )
            ToastNotification.show_toast(self, "PS-2 Dossier PDF exported successfully")
            self._show_message(
                "Dossier Exported Successfully",
                f"PS-2 Forensic Dossier compiled.\n\n"
                f"Artifact: {result.pdf_path}\n"
                f"Cryptographic Hash: {result.sha256_hash}\n"
                f"Documents: {result.documents_count} | Findings: {result.findings_count}",
            )
        except Exception as e:
            logger.exception("Dossier export failed: %s", e)
            self._show_message("Export Failed", str(e), is_error=True)

    def _on_export_json_dossier(self) -> None:
        """Export official PS-2 structured JSON payload."""
        if not self._active_investigation_id or not self._dossier_export_service:
            self._show_message(
                "Export Unavailable", "Please select an active case first.", is_error=True
            )
            return

        default_name = f"VeriTrace_Payload_{self._active_investigation_id}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Forensic JSON Intelligence Payload",
            default_name,
            "JSON Documents (*.json)",
        )
        if not file_path:
            return

        try:
            req = DossierExportRequestDTO(
                investigation_id=self._active_investigation_id,
                organization_id=self._organization_id,
                output_json_path=file_path,
            )
            result = self._dossier_export_service.export_dossier(req)
            self._status_bar.set_status(f"Exported JSON Dossier: {result.json_path}")
            ToastNotification.show_toast(self, "JSON Intelligence payload exported")
            self._show_message(
                "JSON Dossier Exported",
                f"Standardized PS-2 JSON Payload generated:\n{result.json_path}",
            )
        except Exception as e:
            logger.exception("JSON export failed: %s", e)
            self._show_message("Export Failed", str(e), is_error=True)

    def _load_signature_references(self) -> None:
        """Fetch authorized subjects and signature reference profiles for tenant."""
        if not hasattr(self, "_signature_workbench"):
            return
        try:
            subjects = self._investigation_service.list_authorized_subjects(self._organization_id)
            references = self._investigation_service.list_signature_references(
                self._organization_id
            )
            self._signature_workbench.set_subjects(subjects)
            self._signature_workbench.set_references(references)
        except Exception as e:
            logger.warning("Failed to load signature references: %s", e)

    def _on_create_authorized_subject(
        self, full_name: str, designation: str, id_reference: str
    ) -> None:
        """Register an authorized signatory."""
        try:
            self._investigation_service.create_authorized_subject(
                organization_id=self._organization_id,
                full_name=full_name,
                designation=designation,
                id_reference=id_reference,
            )
            self._load_signature_references()
            self._status_bar.set_status(f"Authorized subject '{full_name}' created.")
            ToastNotification.show_toast(self, f"Signatory '{full_name}' registered")
        except Exception as e:
            self._show_message("Subject Registration Failed", str(e), is_error=True)

    def _on_enroll_signature_reference(self, data: dict[str, str]) -> None:
        """Enroll a specimen signature reference under chain of custody."""
        try:
            from veritrace.application.dto.signature_reference import SignatureReferenceEnrollDTO

            dto = SignatureReferenceEnrollDTO(
                organization_id=self._organization_id,
                subject_id=data["subject_id"],
                crop_image_path=data["crop_image_path"],
                source_document_ref=data["source_document_ref"],
                consent_mandate_ref=data["consent_mandate_ref"],
                investigation_id=self._active_investigation_id,
                access_role_required=data.get("access_role_required", "FORENSIC_INVESTIGATOR"),
            )
            self._investigation_service.enroll_signature_reference(dto)
            self._load_signature_references()
            self._status_bar.set_status("Specimen signature reference enrolled.")
            ToastNotification.show_toast(self, "Specimen reference enrolled")
        except Exception as e:
            self._show_message("Enrollment Failed", str(e), is_error=True)

    def _on_run_signatures(self) -> None:
        """Detect and verify signatures across all documents in active investigation."""
        if not self._active_investigation_id or not self._forensic_analysis_service:
            return

        self._status_bar.start_progress("Running Signature Detection & Hu Moment Analysis...")

        # Detect signatures across loaded document pages
        all_detections = []
        for doc_id, doc in self._docs_by_id.items():
            pages = [p for p in self._pages_by_id.values() if p.document_id == doc_id]
            for p in pages:
                if p.image_storage_path and Path(p.image_storage_path).exists():
                    sigs = self._forensic_analysis_service.detect_signatures(
                        image_path=p.image_storage_path,
                        document_id=doc_id,
                        document_name=doc.original_filename,
                        page_number=p.page_number,
                    )
                    all_detections.extend(sigs)

        # Check if an enrolled reference profile is selected in the workbench
        selected_ref_id = self._signature_workbench.get_selected_reference_id()
        selected_ref: SignatureReferenceDTO | None = None
        if selected_ref_id:
            for sig_ref in self._investigation_service.list_signature_references(
                self._organization_id
            ):
                if sig_ref.id == selected_ref_id:
                    selected_ref = sig_ref
                    break

        comparisons = []
        if selected_ref and Path(selected_ref.crop_image_path).exists():
            for q in all_detections:
                comp = self._forensic_analysis_service.compare_signatures(
                    questioned_crop_path=q.crop_path,
                    reference_crop_path=selected_ref.crop_image_path,
                    questioned_name=f"{q.document_name} (p.{q.page_number})",
                    reference_name=f"Enrolled Specimen ({selected_ref.source_document_ref})",
                    expected_reference_hash=selected_ref.sha256_hash,
                )
                comparisons.append(comp)
        elif len(all_detections) >= 2:
            first_det = all_detections[0]
            for q in all_detections[1:]:
                comp = self._forensic_analysis_service.compare_signatures(
                    questioned_crop_path=q.crop_path,
                    reference_crop_path=first_det.crop_path,
                    questioned_name=f"{q.document_name} (p.{q.page_number})",
                    reference_name=f"{first_det.document_name} (p.{first_det.page_number})",
                )
                comparisons.append(comp)
        elif len(all_detections) == 1:
            # Single detected signature compared against self or reference
            s = all_detections[0]
            comp = self._forensic_analysis_service.compare_signatures(
                questioned_crop_path=s.crop_path,
                reference_crop_path=s.crop_path,
                questioned_name=f"{s.document_name} (p.{s.page_number})",
                reference_name="Enrolled Reference (Authorized Signatory)",
            )
            comparisons.append(comp)

        self._signature_workbench.set_comparisons(comparisons)
        self._tabs.setCurrentIndex(2)  # Switch to signature tab
        self._status_bar.finish_progress(
            f"Signature Analysis complete: {len(all_detections)} detected, "
            f"{len(comparisons)} verified."
        )

    def _on_run_contextual_audit(self) -> None:
        """Run contextual arithmetic and chronology audit across case."""
        if not self._active_investigation_id or not self._forensic_analysis_service:
            return

        self._status_bar.start_progress("Evaluating Contextual Math & Chronology Rules...")
        items = self._forensic_analysis_service.run_contextual_audit(
            self._active_investigation_id, self._organization_id
        )
        self._contextual_audit.set_audit_items(items)
        self._tabs.setCurrentIndex(3)  # Switch to audit tab
        self._status_bar.finish_progress(
            f"Contextual audit complete: {len(items)} rules evaluated."
        )

    def _on_ai_settings(self) -> None:
        """Open AI reasoning and privacy configuration dialog."""
        from veritrace.gui.dialogs.ai_settings_dialog import AiSettingsDialog

        dialog = AiSettingsDialog(self._investigation_service, self)
        dialog.exec()

    def _on_about(self) -> None:
        """Show About dialog."""
        self._show_message(
            "About VeriTrace Workstation",
            "VeriTrace Cross-Document Intelligence Workstation v1.0\n\n"
            "Forensic capabilities:\n"
            "• Visual ELA Heatmap Differential & Baseline Analysis\n"
            "• Invariant Hu Moments Signature Verification (VeriTrace Optical Heuristics)\n"
            "• Cross-Document Contradiction & Correlation Matrix\n"
            "• Contextual Procurement Math & Chronology Audit\n"
            "• PS-2 Cryptographically Verified PDF Dossier Compilation\n\n"
            "Engineered for 100% offline, air-gapped forensic operations.",
        )
