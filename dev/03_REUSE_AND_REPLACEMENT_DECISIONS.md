# 03_REUSE_AND_REPLACEMENT_DECISIONS.md
# Component Reuse, Modification, Replacement & Deprecation Strategy

---

## 1. Decision Classification Framework

To transition from the industrial compliance domain (`UdyogPermit AI`) to an AI-powered document forensics system (`VeriTrace Desktop`), every migrated component is evaluated under one of five strict architectural decisions:

* **KEEP:** Reuse as-is or with trivial configuration updates. Proven, domain-agnostic foundation.
* **MODIFY:** Retain underlying core logic and UX patterns, but adapt data contracts, fields, and behavior to forensic workflows.
* **REPLACE:** Existing implementation is fundamentally inadequate or misaligned with PS-2 requirements. Replace with a purpose-built forensic component.
* **DEPRECATE / QUARANTINE:** Irrelevant industrial domain logic or obsolete architectural scaffolding (e.g. web/Tauri/FastAPI). Preserved in `legacy/` for historical reference, but quarantined from active execution.
* **NEW:** Novel capability required by PS-2 that had no counterpart in the source codebase.

---

## 2. Component Migration Decision Matrix

| Source Component | Current Location | Decision | Target VeriTrace Role | Technical Reasoning & Justification |
| :--- | :--- | :---: | :--- | :--- |
| **FastAPI Core & CORS** | `legacy/backend/fastapi_gateway.py` | **REPLACE** | Direct In-Process Python Application Services | In a native PySide6 desktop monolith, an internal HTTP REST server introduces network overhead, port collision risks, and security tokens. Replaced with direct Python service calls and Qt signals. |
| **LangGraph Architecture** | `legacy/backend/main.py#L188-L226` | **MODIFY / DEFER** | Forensic Pipeline Orchestrator | The `StateGraph` pattern and Human-in-the-Loop (`interrupt_before`) checkpointing are valuable reference patterns. Initial implementation uses lightweight Python pipeline orchestration, with LangGraph as an optional upgrade. |
| **Groq Integration** | `legacy/backend/main.py#L62-L68` | **KEEP** | Grounded AI Reasoning Engine | `ChatGroq` provides sub-second LLM inference with JSON schema enforcement. VeriTrace will use Groq (`llama-3.3-70b-versatile`) for evidence-grounded anomaly reasoning and dossier narrative generation (*strictly optional*). |
| **Agent 1 (Profiler & Gate)** | `legacy/backend/agents/agent1.py` | **REPLACE** | Ingestion & Layout Profiling Capability | Agent 1 extracts power, land, and pollution data from free text. VeriTrace requires document classification (ID, Paystub, Bank Statement, Invoice) and layout segmentation. |
| **Agent 2 (Regulatory Checker)** | `legacy/backend/agents/agent2.py` | **REPLACE** | Contextual Rules & Conflict Engine | Agent 2 matches industrial project attributes against government clearances. VeriTrace requires deterministic cross-document reconciliation (e.g., date checks, mathematical totals, entity alignment). |
| **Agent 3 (Planner / Roadmap)** | `legacy/backend/agents/agent3.py` | **REPLACE** | Anomaly Reasoning & Dossier Synthesizer | Agent 3 outputs a textual compliance roadmap. VeriTrace requires a structured investigation dossier synthesizing visual findings, evidence links, and cross-document conflicts. |
| **Agent 4 (Visualizer)** | `legacy/backend/agents/agent4.py` | **REPLACE** | Evidence Relational Graph Builder | Agent 4 translates compliance dependencies into graph nodes. In VeriTrace, relationship structures are mapped into Qt Model/View components (Tree/Table/GraphicsScene). |
| **Pydantic Schemas** | `legacy/backend/agents/schemas.py` | **REPLACE** | Forensic Data Models & Schemas | Existing schemas model factory parameters (`IndustrialProfile`). VeriTrace uses 12 Core Entities + 1 Association Table with Pydantic v2 domain schemas. |
| **React Frontend Foundation** | `legacy/frontend/`, `legacy/desktop_tauri/` | **REPLACE** | PySide6 Native Desktop UI | Active UI is built natively in Python using PySide6 (Qt Widgets, QSS, Signals & Slots). React/Tauri assets are archived in `legacy/` as visual and UX design references. |
| **ReactFlow & ELK.js** | `legacy/frontend/src/WorkflowCanvas.jsx`, `elkLayout.js` | **ARCHIVE / REFERENCE** | Evidence Relationship Views | The DAG interaction pattern serves as an architectural design reference for PySide6 visual evidence views (QGraphicsScene / QTreeView / QTableView). |
| **RightDetailPanel** | `legacy/frontend/src/RightDetailPanel.jsx` | **REPLACE** | PySide6 Evidence Inspector | The slide-out drawer pattern is implemented as a native Qt dock widget (`src/veritrace/gui/components/evidence_inspector.py`) for inspecting crops, ELA, and OCR scores. |
| **AgentThinkingStatus** | `legacy/frontend/src/AgentThinkingStatus.jsx` | **REPLACE** | PySide6 Investigation Status Bar | The multi-step execution status pattern is implemented natively in Qt (`src/veritrace/gui/components/status_bar.py`) tracking active processing stages. |
| **Geospatial & Bhuvan** | `legacy/backend/geospatial/`, `bhuvan_checker.py` | **DEPRECATE** | *None (Quarantined in `legacy/`)* | ISRO Bhuvan satellite queries and OpenStreetMap Overpass spatial queries are irrelevant to PS-2 Document Forensics. |
| **Industrial Registry** | `legacy/backend/agents/resolver.py` | **DEPRECATE** | *None (Quarantined in `legacy/`)* | Maharashtra industrial district registries and pollution classification tables are domain-specific to factory clearance. |
| **Document Validation Route** | `legacy/backend/main.py#L340-L354` | **REPLACE** | Native Forensic Capabilities Pipeline | The existing `/api/v1/document/validate` endpoint was an ungrounded text prompt. Replaced with end-to-end multi-file forensic capabilities. |
| **Docker Configuration** | `legacy/Dockerfile` | **DEPRECATE** | *None (Archived in `legacy/`)* | Docker is deprecated for desktop software; replaced by PyInstaller one-folder bundling and Inno Setup Windows installer (`VeriTrace-Setup.exe`). |

---

## 3. Detailed Component Technical Rationale

### 3.1 Direct Python Services vs. Local Web Servers
* **Why Eliminate FastAPI?** In the previous web/Tauri design, FastAPI was required as a bridge between the browser webview and Python runtime. In a native PySide6 application, the presentation layer and application services both run in Python. Calling an HTTP REST loopback server in the same process introduces unnecessary JSON serialization overhead, ephemeral port binding hazards, Windows firewall prompts, and supervisor complexity. Direct Python method calls provide sub-millisecond execution, zero serialization lag, and type safety.

### 3.2 Visual Forensics & Evidence Graph: Concept Translation from ReactFlow
* In `UdyogPermit AI`, Agent 4 and ReactFlow rendered approval dependencies as DAG nodes with custom handles.
* In `VeriTrace Desktop`, a multi-document investigation forms a directed relational graph:
  * **Document Nodes:** Representing ingested files (e.g., "Aadhaar Card", "Salary Slip Nov 2023").
  * **Entity Nodes:** Extracted facts (e.g., "PAN: ABCDE1234F", "Name: Rajesh Sharma", "Gross Pay: ₹85,000").
  * **Anomaly / Conflict Nodes:** Highlighting discrepancies (e.g., "Name Spelled 'Rajesh' vs 'Rakesh'", "Altered Paystub Pixel Grid").
  * **Edges:** Tracing provenance from document pages to entities and flagged conflicts.
* While the original ReactFlow implementation remains safely archived under `legacy/frontend/`, the PySide6 UI translates these concepts into native Qt Widgets (e.g. `QGraphicsView` / `QGraphicsScene` or hierarchical `QTreeView` with custom forensic delegates).

### 3.3 RightDetailPanel: Evolution into Qt Evidence Inspector
* The archived `RightDetailPanel.jsx` contains comprehensive state handling for drawer animation, tab navigation, badge rendering, and action triggers.
* The native PySide6 equivalent (`src/veritrace/gui/components/evidence_inspector.py`) implements this as a high-performance Qt Inspector panel allowing investigators to inspect:
  1. High-resolution original image crops.
  2. Corresponding Error Level Analysis (ELA) heatmaps.
  3. Exact OCR text strings, character bounding box coordinates, and confidence scores.
  4. Deterministic rule violations and optional LLM forensic explanations.
  5. Action buttons to "Confirm Finding", "Dismiss as False Positive", or "Add Investigator Note".

### 3.4 Quarantining Industrial & Geospatial Modules (Safe Deprecation)
* Modules such as `bhuvan_checker.py`, `geospatial/`, and `resolver.py` are strictly isolated inside `legacy/backend/`:
  * All references are severed from the active VeriTrace desktop codebase.
  * The files remain in `legacy/` for historical auditability and licensing compliance.

---

## 4. Summary of New Capabilities Built for VeriTrace Desktop

1. **Multi-Document Ingestion Engine:** Handles local file intake (PDF, PNG, JPG), computes SHA-256 integrity hashes, and renders PDF pages to 300 DPI raster images.
2. **Hybrid OCR Service:** Combines PyMuPDF digital text layer extraction with Tesseract OCR fallback for scanned imagery, maintaining bounding box token coordinates.
3. **Computer Vision Forensics Engine:** Computes Error Level Analysis (ELA) compression differentials, detects font baseline misalignments, and flags copy-move cloned regions using OpenCV and Pillow.
4. **Cross-Document Correlation Engine:** Executes fuzzy string reconciliation (RapidFuzz) and deterministic rule matrices to identify conflicting data across distinct documents.
5. **Dossier Builder:** Compiles an ISO/IEC 27037-compliant Investigation Dossier in JSON and exportable PDF format via ReportLab.
6. **SQLite Persistent Database:** Persistent relational storage (12 Core Entities + 1 Association Table) in SQLite WAL mode.
7. **Native PySide6 GUI:** Custom desktop UI with High-DPI support, dark forensic theme (QSS), and responsive background task execution.
