# 04_SYSTEM_ARCHITECTURE.md
# VeriTrace Desktop System Architecture & Local-First Orchestration

---

## 1. Architectural Overview & Vision

**VeriTrace Desktop** is engineered as a standalone Windows desktop application (targeting Windows 10/11 x64) combining a native **PySide6 (Qt for Python)** user interface, an in-process **Python Application Service Layer**, high-performance **Forensic Capability Engines**, and an asynchronous **Background Processing System** backed by local SQLite persistence.

The system adheres to non-negotiable architectural mandates:
1. **Native Desktop Monolith:** Built with Python 3.11 and PySide6. The UI communicates directly with application services without local HTTP loopback gateways, web browsers, or external supervisor processes.
2. **Local-First & Offline Resilience:** All core document processing (PDF parsing, 300 DPI rasterization, Tesseract OCR, OpenCV visual forensics, arithmetic rules, RapidFuzz entity correlation, and ReportLab PDF dossier generation) executes 100% locally on the host machine without requiring network connectivity.
3. **Deterministic-First Processing:** Forensic measurements (pixel compression variance, font baseline deviations, duplicate image patches, math checksums, date chronology) are computed algorithmically rather than guessed by a generative model.
4. **Optional Grounded AI Reasoning:** Large Language Models (Groq ChatGroq) operate exclusively downstream of deterministic measurements as an optional, user-controlled enhancement to synthesize narratives and explain context—strictly referencing verified document coordinates. No original documents or raw images are transmitted to external clouds.

---

## 2. High-Level Desktop System Architecture Diagram

```mermaid
graph TD
    subgraph PySide6App ["VeriTrace Native Windows Desktop Application (PySide6 / Qt 6.7+)"]
        subgraph PresentationLayer ["Presentation Layer (Qt Widgets + QSS + Model/View)"]
            UI_Main["MainWindow (QSS Forensic Dark Theme)"]
            UI_Sidebar["InvestigationSidebar (Recent Cases, TreeView)"]
            UI_Viewer["DocumentViewer (PyMuPDF High-DPI QGraphicsScene + BBox Overlays)"]
            UI_Inspector["EvidenceInspector (DockWidget, ELA Crops, Metadata)"]
            UI_Progress["JobStatusBar (QProgressBar, Stage Telemetry)"]
        end

        subgraph ApplicationLayer ["Application & Controller Layer (src/veritrace/gui/controllers & src/veritrace/application/services)"]
            Ctrl_Inv["InvestigationController & Service"]
            Ctrl_Doc["DocumentController & Service"]
            Ctrl_Forensic["ForensicsController & Service"]
            Ctrl_Dossier["DossierController & Service"]
        end

        subgraph BackgroundLayer ["Asynchronous Execution Layer"]
            Qt_Pool["QThreadPool & QRunnable (In-Process Forensic Tasks)"]
            Qt_Signals["Qt Signals & Slots (Progress, Batch Updates)"]
        end

        subgraph CapabilityEngines ["Deterministic Forensic & Processing Engines (src/veritrace/capabilities)"]
            Engine_PyMuPDF["PyMuPDF: Native Vector Text & 300 DPI Render"]
            Engine_Tesseract["Bundled Tesseract OCR: Scanned Page Extraction"]
            Engine_Quality["Quality Engine: OCR Confidence Gating & Degradation Scoring"]
            Engine_OpenCV["OpenCV & Pillow: ELA, Font Alignment, Clone Matching"]
            Engine_Rules["Contextual Rule & Checksum Validator"]
            Engine_Fuzz["RapidFuzz: Cross-Document Entity Alignment"]
            Engine_Dossier["ReportLab: Auditor-Grade PDF Dossier Generator"]
        end
    end

    subgraph DecoupledWorker ["Optional Standalone Worker Process (src/veritrace/workers)"]
        Worker_Proc["Job Runner (job_runner.py)<br/>Atomic SQLite Claim (BEGIN IMMEDIATE)"]
    end

    subgraph OptionalCloudAI ["Optional Cloud Reasoning (User-Controlled)"]
        Groq_LLM["ChatGroq: LLaMA 3.3 70B (JSON Schema Enforced)<br/>*Operates only on anonymized, pre-calculated metrics*"]
    end

    subgraph LocalStorage ["Workstation Local Storage (%LOCALAPPDATA%/VeriTrace/)"]
        DB_SQLite[("SQLite WAL Database (veritrace.sqlite)<br/>12 Core Entities + 1 Assoc Table")]
        FS_Storage["Investigation Filesystem Storage<br/>originals/, processed/, evidence/, reports/"]
        App_Logs["Structured Application & Audit Logs"]
    end

    %% Wiring & Control Flow
    PresentationLayer -->|Direct Python Calls| ApplicationLayer
    ApplicationLayer -->|Dispatches Heavy Tasks| BackgroundLayer
    BackgroundLayer -->|Executes Engines| CapabilityEngines
    BackgroundLayer -->|Emits Telemetry via Signals| PresentationLayer
    ApplicationLayer -->|CRUD & Job Queueing| DB_SQLite
    ApplicationLayer -->|File I/O (SHA-256)| FS_Storage
    CapabilityEngines -->|Persists Artifacts & Crops| FS_Storage
    CapabilityEngines -->|Saves Findings & Evidence| DB_SQLite
    DecoupledWorker -.->|Optional Out-of-Process Polling| DB_SQLite
    DecoupledWorker -.-> CapabilityEngines
    ApplicationLayer -.->|Optional Grounded Narrative| Groq_LLM
```

---

## 3. End-to-End Desktop Investigation Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Forensic Investigator
    participant UI as PySide6 UI (MainWindow)
    participant Ctrl as Application Controller & Services
    participant DB as SQLite WAL (%LOCALAPPDATA%)
    participant Pool as QThreadPool / QRunnable
    participant Engines as Capability Engines (PyMuPDF / CV / OCR)
    participant LLM as Optional Groq API

    Note over UI,Engines: Application Launch: PySide6 loads dark theme, mounts SQLite WAL database
    Analyst->>UI: Drops documents into Investigation Workspace
    UI->>Ctrl: create_investigation(files)
    Ctrl->>DB: Store files in %LOCALAPPDATA%, compute SHA-256, insert DB records
    Ctrl-->>UI: Update DocumentListModel & InvestigationViewModel

    Analyst->>UI: Clicks "Analyze Investigation"
    UI->>Ctrl: start_investigation_job(investigation_id)
    Ctrl->>DB: INSERT INTO investigation_jobs (status='QUEUED', stage='INTAKE')
    Ctrl->>Pool: Submit ForensicPipelineRunnable(job_id)

    Pool->>DB: BEGIN IMMEDIATE; update job status='RUNNING'
    Pool->>Engines: 1. Render 300 DPI pages & Multi-Factor OCR
    Engines-->>Pool: Extracted tokens, word bboxes, geometry
    Pool-->>UI: Qt Signal progress_updated(stage="OCR", percent=25)

    Pool->>Engines: 2. Run ELA, font baseline regression, clone matching
    Engines-->>Pool: Anomalies, pixel coordinates, visual evidence crops
    Pool-->>UI: Qt Signal progress_updated(stage="FORENSICS", percent=50)

    Pool->>Engines: 3. Contextual rules & RapidFuzz cross-document reconciliation
    Engines-->>Pool: Inconsistencies, entity conflicts, mapped evidence
    Pool-->>UI: Qt Signal progress_updated(stage="CORRELATION", percent=75)

    opt Optional Groq Reasoning Enabled & Online
        Pool->>LLM: Pass structured anomaly metrics (no raw scans)
        LLM-->>Pool: Evidence-grounded narrative analysis (JSON)
    end

    Pool->>Engines: 4. Compile ReportLab PDF & JSON dossier
    Engines-->>Pool: Dossier generated and SHA-256 hashed
    Pool->>DB: Mark job COMPLETED (100%)
    Pool-->>UI: Qt Signal pipeline_finished(investigation_id)

    UI->>Ctrl: reload_investigation_data(investigation_id)
    Ctrl->>DB: Fetch findings, evidence references, dossier path
    DB-->>Ctrl: Hydrate UI models
    Ctrl-->>UI: Update FindingTableModel, EvidenceTreeModel
    Analyst->>UI: Inspects anomalies in EvidenceInspector, reviews dossier
```

---

## 4. Module Responsibilities & Architectural Boundaries

### 4.1 Presentation Layer (`src/veritrace/gui/`)
* **Strict Boundary:** The UI layer contains zero forensic algorithms, OCR code, or direct SQL execution.
* **Component Roles:**
  * `views/`: MainWindow, InvestigationView, DocumentViewer, EvidenceInspector, DossierView, SettingsView.
  * `components/`: DocumentViewer (`QGraphicsView` / `QGraphicsScene` for zoom, pan, bounding box overlays), EvidenceInspector (dock widget for high-resolution visual evidence crops, ELA heatmaps, and OCR confidence), Status bars, and custom cards.
  * `controllers/`: Mediators translating user interactions into application service calls and handling signals.
  * `viewmodels/`: UI state holders decoupling raw domain entities from widget state.
  * `styles/`: Theme engine loading custom QSS stylesheets (`dark_theme.qss`).
  * `resources/`: Icons, fonts, and static assets.

### 4.2 Application Services Layer (`src/veritrace/application/`)
* **Service Facade:** Direct in-process Python classes providing clean APIs for the UI:
  * `services/`: `InvestigationService`, `DocumentService`, `AnalysisService`, `DossierService`, `JobService`.
  * `workflows/`: Pipeline coordinator and execution workflows.
  * `use_cases/`: Specialized command/query handlers.
  * `dtos/`: Strongly typed data transfer objects.

### 4.3 Capability Engines (`src/veritrace/capabilities/`)
* **Independent Python Modules:** Pure forensic and document processing logic completely decoupled from PySide6:
  * `ingestion/`: Ingests files, computes SHA-256 hashes, validates MIME types, partitions storage.
  * `extraction/`: Hybrid OCR routing (PyMuPDF vector text + Tesseract scanned fallback) and layout parsing.
  * `quality/`: Extraction quality scoring, OCR character/word confidence gating, degradation assessment.
  * `forensics/`: OpenCV + Pillow implementation of ELA, baseline regression, and clone stamp detection.
  * `correlation/`: Cross-document entity matching and contradiction identification via RapidFuzz.
  * `reasoning/`: Structured, grounded narrative synthesis from deterministic findings.
  * `reporting/`: PS-2 Sections 7.1–7.6 report compilation via ReportLab.

### 4.4 Domain & Infrastructure Layers (`src/veritrace/domain/`, `src/veritrace/infrastructure/`)
* **Domain Layer (`src/veritrace/domain/`):** Pure models (Investigation, Document, Finding, Evidence), validation rules, enums, events, and repository interfaces without external dependencies.
* **Infrastructure Layer (`src/veritrace/infrastructure/`):** Technical adapters implementing persistence (SQLite in WAL mode via SQLAlchemy 2.0 with Alembic migrations), PDF rasterization (PyMuPDF), OCR engines, OpenCV vision adapters, and secure storage in `%LOCALAPPDATA%/VeriTrace/`.

---

## 5. Deterministic vs. AI-Powered Processing Division

| Processing Task | Engine | Processing Type | Justification & Verification Standard |
| :--- | :--- | :---: | :--- |
| **File Integrity & Hashing** | Python `hashlib` | **Deterministic** | Cryptographic SHA-256 hash ensures evidence chain-of-custody. |
| **PDF Page Rasterization** | PyMuPDF (`fitz`) | **Deterministic** | Precise pixel rendering at 300 DPI without interpolation distortion. |
| **OCR Text & Coordinate Extraction** | PyMuPDF / Tesseract | **Deterministic** | Extracted character/word coordinates directly from document stream. |
| **Error Level Analysis (ELA)** | OpenCV / Pillow | **Deterministic** | Mathematical pixel subtraction: `\|Original - Resaved_JPEG\| * Scale`. |
| **Font Baseline Alignment** | OpenCV Contours | **Deterministic** | Geometric calculation of bounding box variance on horizontal lines. |
| **Math & Date Chronology Rules** | Python Rule Matrix | **Deterministic** | Exact arithmetic and calendar date comparisons. |
| **Entity Name Alignment** | RapidFuzz Token Match | **Deterministic** | Levenshtein distance metrics with deterministic similarity thresholds. |
| **Document Classification** | Hybrid / Groq LLM | *AI-Assisted* | Layout structure and header keyword evaluation. |
| **Contextual Forensic Reasoning** | Groq ChatGroq | *AI-Assisted* | Synthesizing disparate visual and contextual findings into clear prose (*optional*). |
| **Dossier Executive Summary** | Groq ChatGroq | *AI-Assisted* | Summarizing investigation outcomes grounded strictly in recorded evidence (*optional*). |
| **PDF Dossier Compilation** | ReportLab | **Deterministic** | Programmatic document layout with exact coordinate image crops. |

---

## 6. Human Review Gate (HITL Strategy)

In accordance with forensic standards (ISO/IEC 27042) and PS-2 assessment guidelines, VeriTrace maintains **human oversight for consequential decisions**:
* The investigation state machine contains a checkpoint stage (`HUMAN_REVIEW`).
* When critical anomalies (e.g., potential salary inflation or duplicate signatures) are detected, the pipeline records findings as `PENDING_REVIEW`.
* In the desktop UI, the investigator inspects evidence crops, views mathematical indicators, and selects:
  * **Confirm:** Mark the finding as verified evidence.
  * **Dismiss:** Mark as an acceptable artifact (e.g., normal scan compression or known nickname variation).
  * **Annotate:** Attach investigator commentary.
* Confirmed findings and investigator notes are formally included in the final Investigation Dossier.

---

## 7. Resilient Error Handling & Graceful Degradation

| Failure Scenario | Mitigation & Fallback Strategy |
| :--- | :--- |
| **Corrupted or Password-Protected PDF** | Pre-validation check catches decryption error; marks document with `ERROR_CORRUPTED` status and proceeds with other documents in bundle. |
| **Low-Contrast or Blurry Scanned Document** | PyMuPDF detects lack of digital text; triggers adaptive image binarization (CLAHE) before passing to Tesseract OCR; flags low-confidence OCR warning. |
| **OpenCV Computer Vision Memory Exception** | Large images (>4000px) are downsampled to 2048px maximum dimension before running ELA; prevents process crashes. |
| **Groq API Rate Limit or Timeout** | Structured deterministic findings are formatted into the dossier using a fallback deterministic template without LLM prose synthesis. |
| **Unsupported Foreign Language** | System flags unsupported script tokens, records `UNSUPPORTED_LANGUAGE` in dossier Section 7.6 (Investigation Limitations). |
