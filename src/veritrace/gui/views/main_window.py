"""Main forensic investigation workstation window."""

from __future__ import annotations

import logging
import os
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from veritrace.application.dto.correlation import (
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.application.dto.document import DocumentIngestionResultDTO
from veritrace.application.dto.investigation import (
    EvidenceResponseDTO,
    FindingResponseDTO,
    InvestigationCreateDTO,
    ReviewDecisionType,
    ReviewFindingRequestDTO,
)
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.document_ingestion_service import (
    DocumentIngestionService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.document import DocumentType
from veritrace.gui.components.dashboard_widget import DashboardBannerWidget
from veritrace.gui.components.document_viewer import SideBySideDocumentViewer
from veritrace.gui.components.evidence_inspector import EvidenceInspectorDock
from veritrace.gui.components.finding_table import FindingTableWidget
from veritrace.gui.components.investigation_sidebar import InvestigationSidebar
from veritrace.gui.components.status_bar import VeriTraceStatusBar
from veritrace.gui.controllers.correlation_worker import CorrelationWorker
from veritrace.gui.demo_data import seed_industrial_demo

logger = logging.getLogger("veritrace.gui.main_window")


class MainWindow(QMainWindow):
    """Forensic investigation workstation coordinating 4-pane views and background analysis."""

    def __init__(
        self,
        investigation_service: InvestigationService,
        correlation_service: CrossDocumentCorrelationService,
        ingestion_service: DocumentIngestionService | None = None,
        uow_factory: Any = None,
        organization_id: str = "org_11111111111111111111111111111111",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("VeriTrace Workstation — Cross-Document Forensic Intelligence")
        self.resize(1400, 900)

        self._investigation_service = investigation_service
        self._correlation_service = correlation_service
        self._ingestion_service = ingestion_service
        self._uow_factory = uow_factory
        self._organization_id = organization_id

        self._active_investigation_id: str | None = None
        self._current_findings: list[FindingResponseDTO] = []
        self._current_evidence: list[EvidenceResponseDTO] = []
        self._docs_by_id: dict[str, DocumentIngestionResultDTO] = {}
        self._pages_by_id: dict[str, DocumentPage] = {}
        self._active_worker: CorrelationWorker | None = None

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

    def _setup_ui(self) -> None:
        # Central Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # 1. Left Sidebar
        self._sidebar = InvestigationSidebar(main_splitter)
        self._sidebar.setMinimumWidth(280)
        self._sidebar.setMaximumWidth(360)
        self._sidebar.investigation_selected.connect(self._on_investigation_selected)
        self._sidebar.document_selected.connect(self._on_document_selected)
        self._sidebar.new_investigation_requested.connect(self._on_new_investigation)
        self._sidebar.add_document_requested.connect(self._on_add_document)
        self._sidebar.load_demo_requested.connect(self._on_load_demo)
        main_splitter.addWidget(self._sidebar)

        # 2. Central Workspace
        central_container = QWidget(main_splitter)
        central_layout = QVBoxLayout(central_container)
        central_layout.setContentsMargins(8, 8, 8, 8)
        central_layout.setSpacing(6)

        self._dashboard_banner = DashboardBannerWidget(central_container)
        self._dashboard_banner.run_correlation_requested.connect(self._on_run_correlation)
        central_layout.addWidget(self._dashboard_banner)

        self._tabs = QTabWidget(central_container)

        # Tab 0: Contradiction Matrix
        matrix_container = QWidget(self._tabs)
        matrix_layout = QVBoxLayout(matrix_container)
        matrix_layout.setContentsMargins(4, 4, 4, 4)
        self._finding_table = FindingTableWidget(matrix_container)
        self._finding_table.finding_selected.connect(self._on_finding_selected)
        self._finding_table.finding_activated.connect(self._on_finding_activated)
        matrix_layout.addWidget(self._finding_table)
        self._tabs.addTab(matrix_container, "Contradiction Matrix")

        # Tab 1: Side-by-Side Evidence Viewer
        self._doc_viewer = SideBySideDocumentViewer(self._tabs)
        self._tabs.addTab(self._doc_viewer, "Side-by-Side Evidence Canvas")

        central_layout.addWidget(self._tabs, 1)
        main_splitter.addWidget(central_container)
        main_splitter.setSizes([320, 1080])

        self.setCentralWidget(main_splitter)

        # 3. Right Evidence Inspector Dock
        self._inspector_dock = EvidenceInspectorDock(self)
        self._inspector_dock.setMinimumWidth(320)
        self._inspector_dock.setMaximumWidth(420)
        self._inspector_dock.review_action_submitted.connect(self._on_review_submitted)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._inspector_dock)

        # 4. Status Bar
        self._status_bar = VeriTraceStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.set_telemetry(f"Org: {self._organization_id}")

    def _load_investigations(self) -> None:
        """Fetch investigations for organization and populate sidebar."""
        invs = self._investigation_service.list_investigations(self._organization_id)
        if invs:
            self._sidebar.set_investigations(invs, selected_id=invs[0].id)
            self._on_investigation_selected(invs[0].id)
        else:
            self._status_bar.set_status(
                "No active investigations found. Create a case or load demo."
            )

    def _on_investigation_selected(self, investigation_id: str) -> None:
        """Handle case selection and load documents and findings."""
        self._active_investigation_id = investigation_id
        self._status_bar.set_telemetry(f"Org: {self._organization_id} | Case: {investigation_id}")
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

    def _on_run_correlation(self, is_order_closed: bool) -> None:
        """Trigger asynchronous background cross-document correlation."""
        if not self._active_investigation_id:
            self._show_message(
                "No Case Selected", "Please select or create an investigation first.", is_error=True
            )
            return

        self._dashboard_banner.set_correlate_enabled(False)
        self._status_bar.start_progress("Running cross-document correlation engine...")

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
        self._reload_case_data()

    def _on_correlation_error(self, err_msg: str) -> None:
        self._dashboard_banner.set_correlate_enabled(True)
        self._status_bar.set_status(f"Correlation error: {err_msg}", stage="ERROR")
        self._show_message(
            "Correlation Engine Error", f"Analysis failed:\n{err_msg}", is_error=True
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
            self._doc_viewer.load_comparison(
                source_doc_name=f"{doc.original_filename} (Page {first_page.page_number})",
                source_img_path=first_page.image_storage_path,
                source_evidence=None,
                target_doc_name="Select a second document or finding to compare",
                target_img_path=None,
                target_evidence=None,
            )
            self._status_bar.set_status(f"Viewing document: {doc.original_filename}")

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

        self._doc_viewer.load_comparison(
            source_doc_name=src_doc_name,
            source_img_path=src_img_path,
            source_evidence=src_ev,
            target_doc_name=tgt_doc_name,
            target_img_path=tgt_img_path,
            target_evidence=tgt_ev,
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
            from pathlib import Path

            from veritrace.application.dto.document import DocumentIngestDTO

            dto = DocumentIngestDTO(
                investigation_id=self._active_investigation_id,
                organization_id=self._organization_id,
                filename=Path(file_path).name,
                file_path=file_path,
                document_type=DocumentType.UNCLASSIFIED,
            )
            self._ingestion_service.ingest_document(dto)
            self._reload_case_data()
            self._status_bar.set_status(f"Ingested document: {Path(file_path).name}")
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
        except Exception as e:
            logger.exception("Failed to seed industrial demo: %s", e)
            self._show_message("Demo Seed Error", str(e), is_error=True)
