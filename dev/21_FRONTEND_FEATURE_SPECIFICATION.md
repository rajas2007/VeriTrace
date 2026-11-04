# 21_FRONTEND_FEATURE_SPECIFICATION.md
# Desktop Investigation Workstation UI/UX & PySide6 Feature Specification

---

## 1. User Experience Philosophy & Native Workstation Design

The VeriTrace user interface is architected as an **Integrated Desktop Forensic Workstation** built natively with **PySide6 (Qt 6.7+ for Python)**. Investigators analyze sensitive evidence through native drag-and-drop ingestion, flexible 4-pane docking layouts, synchronized side-by-side viewports, and interactive inspector dock widgets:

### 1.1 Desktop Shell & Layout Components
* **Native Workstation Window (`MainWindow`):** Hosts the custom forensic dark theme (QSS), top toolbar, active Case Reference Code (`CASE-2026-0891`), Case Risk Badge (`LOW`, `FLAGGED`, `SUSPECTED_MANIPULATION`), and quick action buttons ("New Investigation", "Export PDF Dossier").
* **Docking Workspace Layout:**
  1. **Left Sidebar (`InvestigationSidebar`):** Tree hierarchy displaying active cases, documents, pages, and historical investigations stored in `%LOCALAPPDATA%/VeriTrace/database/veritrace.sqlite`.
  2. **Central Workspace (`DocumentViewer`):** Hardware-accelerated 2D canvas (`QGraphicsView` + `QGraphicsScene`) rendering 300 DPI pages with sub-millimeter bounding box overlays and split-screen comparison.
  3. **Right Inspector (`EvidenceInspector`):** QDockWidget displaying visual crops, side-by-side ELA heatmaps, OCR token confidences, and Human-in-the-Loop review buttons.
  4. **Bottom Status Bar (`StatusBar`):** Persistent `QStatusBar` with embedded `QProgressBar` tracking background pipeline stages in real time.
* **Direct Python Service Communication:** All actions call in-process Python application services directly, eliminating network latency and loopback HTTP hazards.

---

## 2. Core UI Feature Specifications

---

### Feature 1: Multi-Document Intake & Case Setup
* **User Purpose:** Allows the investigator to create a new case and import a batch of related documents (e.g., ID card + Salary Slip + Bank Statement).
* **Main Components:** `new_investigation_dialog.py`, `investigation_sidebar.py`.
* **Service Interactions:**
  * `InvestigationService.create_investigation(dto)` (Creates case container).
  * `DocumentService.ingest_documents(dtos)` (Validates and stores original files).
  * `JobQueueService.enqueue_job(inv_id)` (Schedules background analysis).
* **Required Data:** Case title, reference code, array of local file paths (`.pdf`, `.png`, `.jpg`).
* **User Actions:** Drag and drop files; remove individual files; assign optional classification hint; click "Start Investigation".
* **States:**
  * *Empty State:* Case setup dialog with dropzone and sample fixture quick-load buttons.
  * *Loading State:* Progress bar tracking SHA-256 calculation and file copying to `%LOCALAPPDATA%`.
  * *Error State:* Error dialog displaying format rejections (e.g., "File exceeds 20MB limit" or "Unsupported file format").

---

### Feature 2: High-Resolution Document Viewer & Bounding Box Overlay
* **User Purpose:** Enables the analyst to examine high-resolution document pages and inspect visually highlighted forensic anomalies.
* **Main Components:** `document_viewer.py`, `document_controller.py`.
* **Service Interactions:**
  * `DocumentService.get_document(doc_id)` (Fetches page metadata and dimensions).
  * `DocumentService.get_page_image_path(doc_id, page_num)` (Retrieves rendered 300 DPI PNG path).
* **Required Data:** 300 DPI rendered page PNG, width/height in pixels, array of extracted fields and findings with normalized coordinates `[ymin, xmin, ymax, xmax]`.
* **User Actions:**
  * Pan and zoom canvas via mouse drag and wheel.
  * Click any bounding box on the page to populate the **Evidence Inspector**.
  * Switch view mode via toolbar toggle:
    * *Original View:* Standard scan render with colored bounding boxes.
    * *Error Level Analysis (ELA) Heatmap:* Overlays high-contrast compression noise heatmap.
    * *Contour / Threshold View:* Displays binary threshold mask for signature/stamp isolation.
  * Switch pages via page selector or thumbnail strip.

---

### Feature 3: Findings Table & Anomaly Triage
* **User Purpose:** Displays a prioritized table of all detected anomalies across the document bundle.
* **Main Components:** `finding_table.py`, `finding_table_model.py`.
* **Service Interactions:**
  * `ForensicsService.get_findings(inv_id, tier)` (Fetches categorized findings).
* **Required Data:** Array of findings with title, severity, epistemic tier, category, and source document references.
* **User Actions:**
  * Filter findings by Epistemic Tier (`CONFIRMED_OBSERVATION`, `DETECTED_INCONSISTENCY`, `SUSPECTED_MANIPULATION`).
  * Filter by Severity (`CRITICAL`, `WARNING`, `INFORMATIONAL`).
  * Click a finding row: automatically pans the Document Viewer to the corresponding page and highlights the bounding box.

---

### Feature 4: Evidence Inspector Dock Widget
* **User Purpose:** Provides deep-dive forensic inspection of a specific flagged region.
* **Main Components:** `evidence_inspector.py`, `forensics_controller.py`.
* **Service Interactions:**
  * `ForensicsService.record_review_decision(finding_id, decision, notes)` (Submits human decision).
* **Required Data:**
  * High-resolution cropped image patch of the original document.
  * High-resolution cropped patch of the ELA heatmap.
  * Exact OCR text and character confidence scores.
  * Mathematical rule discrepancy details (expected vs. actual).
  * Optional Groq grounded narrative explanation.
* **User Actions:**
  * Compare Original Crop vs. ELA Heatmap side by side.
  * Read forensic explanation.
  * Human Review Actions: Click **"Confirm Finding"**, **"Dismiss as Artifact"**, or **"Add Investigator Note"**.

---

### Feature 5: Cross-Document Relational Evidence View
* **User Purpose:** Enables the analyst to visualize connections, common entities, and contradictory claims across distinct documents.
* **Main Components:** `evidence_tree_model.py`, `workspace_layout.py`.
* **Data Visualized:**
  * Ingested documents (nodes) $\to$ Extracted entities (names, dates, accounts) $\to$ Flagged contradictions.
* **User Actions:** Click any entity or conflict to focus the Document Viewer directly on the relevant page coordinates.

---

### Feature 6: Automated Dossier Export
* **User Purpose:** One-click export of an auditor-grade investigation report complying with PS-2 Sections 7.1–7.6.
* **Main Components:** `export_dossier_dialog.py`, `dossier_service.py`.
* **User Actions:** Select destination folder on Windows; click "Generate Dossier"; open compiled PDF directly in default OS PDF viewer.
