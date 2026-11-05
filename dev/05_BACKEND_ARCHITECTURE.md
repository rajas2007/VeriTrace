# 05_BACKEND_ARCHITECTURE.md
# VeriTrace Core Application Services & Capability Engine Architecture

---

## 1. Backend Design Philosophy: In-Process Application Services & Capability Engines

The VeriTrace core backend is engineered as a **modular Python application layer** serving the PySide6 native desktop interface directly in-process. Under ADR-030, all backend and application code resides within the unified `src/veritrace/` tree:

* **Direct In-Process Service Communication:** The presentation layer (`src/veritrace/gui/`) communicates directly with Python application services (`src/veritrace/application/services/`). No HTTP REST loopback servers, port allocation hazards, or network serialization overheads exist.
* **Strict Separation of Concerns:** Domain models and capability engines have zero dependency on PySide6, Qt, or UI widgets. Domain logic is pure Python with zero framework dependencies.
* **Deterministic Pipelines First:** OCR, computer vision (ELA, baseline regressions), arithmetic checksums, and cross-document fuzzy alignments execute deterministically in specialized Python capability engines.
* **Offline-First & Data Minimization:** 100% of core forensic capabilities execute offline. Optional Groq LLM reasoning operates only on pre-extracted numerical/text metrics with user consent; original document binaries are never transmitted off the user's workstation.
* **Extraction Quality Gating:** Raw text extracted from OCR or vector streams passes through a dedicated extraction quality assessment module (`capabilities/quality/`) to score confidence before rules or correlation engines consume it.
* **Dual Execution Modes:** Forensics jobs can run in-process via Qt's `QThreadPool` for interactive responsiveness, or via a decoupled background worker (`workers/job_runner.py`) for long-running batch isolation.

---

## 2. Authoritative Target Directory Structure

The core engine and backend logic is organized within `src/veritrace/`:

```
src/veritrace/
├── application/                       # Application Services & Coordination Layer
│   ├── services/                      # High-level services (Investigation, Document, Analysis, Dossier)
│   ├── workflows/                     # Forensic pipeline orchestration & state machines
│   ├── use_cases/                     # Specific command / query use cases
│   └── dtos/                          # Strongly typed data transfer objects
│
├── domain/                            # Pure Domain Logic & Business Rules (Zero external deps)
│   ├── models/                        # Core domain dataclasses (Investigation, Document, Finding)
│   ├── rules/                         # Pure deterministic rules (math checksums, date chronology)
│   ├── events/                        # Domain event definitions
│   └── interfaces/                    # Repository & adapter protocol definitions
│
├── capabilities/                      # Eight Canonical Forensic & Intelligence Engines
│   ├── ingestion/                     # File validation, MIME checking, SHA-256 calculation, batch queue
│   ├── classification/                # Industrial document type classification & script detection
│   ├── extraction/                    # PDF vector text extraction, multilingual OCR, layout understanding
│   ├── quality/                       # Extraction Quality: OCR confidence scoring, degradation assessment
│   ├── forensics/                     # Visual forensics (ELA, baselines), PDF metadata, Signature Forensics
│   ├── correlation/                   # Cross-document entity reconciliation & contradiction matrix
│   ├── reasoning/                     # Contextual intelligence narrative synthesis & prompt engineering
│   └── reporting/                     # PS-2 Section 7.1–7.6 PDF & JSON dossier compilation
│
├── infrastructure/                    # Concrete Technical Adapters
│   ├── persistence/                   # SQLite database (WAL mode), SQLAlchemy 2.0 ORM, Alembic migrations
│   ├── pdf/                           # PyMuPDF rasterizer & vector text adapter
│   ├── ocr/                           # Multilingual OCR adapters (PaddleOCR, Tesseract)
│   ├── vision/                        # OpenCV & Pillow image processing adapter
│   ├── models/                        # Local model inference adapters (ONNX Runtime for signatures)
│   ├── reporting/                     # ReportLab PDF generation adapter
│   ├── ai/                            # ChatGroq LLM adapter with fallback & mocking
│   └── security/                      # Windows DPAPI storage & local filesystem path resolution
│
└── workers/                           # Concurrency & Asynchronous Workers
    ├── job_runner.py                  # Standalone background CLI worker (atomic SQLite claim)
    ├── tasks/                         # Discrete executable background tasks
    └── pools/                         # QThreadPool / QRunnable worker implementations
```

---

## 3. Core Capability Specifications (Eight Canonical Capabilities)

### 3.1 Document Ingestion & Storage (`capabilities/ingestion/`)
* **Libraries:** Python standard library (`hashlib`, `mimetypes`, `pathlib`).
* **Responsibilities:**
  1. Validate file header magic bytes (PDF `%PDF-`, PNG `\x89PNG`, JPEG `\xFF\xD8\xFF`, TIFF `II*\x00` or `MM\x00*`).
  2. Compute SHA-256 hash immediately upon file intake to guarantee chain-of-custody.
  3. Store immutable originals under `%LOCALAPPDATA%/VeriTrace/cases/<case_id>/documents/originals/`.
  4. Manage batch intake queues and pre-screen documents for raster corruption.

### 3.2 Document Classification & Language ID (`capabilities/classification/`)
* **Responsibilities:**
  1. Classify industrial document types: Purchase Orders, Goods Receipt Notes, Mill Test Certificates, Invoices, Delivery Challans, Identity Cards, and Tax Forms.
  2. Identify primary document language and regional script (Devanagari, Latin, Bengali, Gurmukhi, Dravidian scripts) to route to appropriate OCR models.
  3. Flag mixed-language documents requiring hybrid font modeling.

### 3.3 Multilingual Document Extraction Engine (`capabilities/extraction/`, `infrastructure/pdf/`, `infrastructure/ocr/`)
* **Libraries:** `PyMuPDF` (`fitz`), `pytesseract`, `PaddleOCR` (evaluated candidate), optional `Docling` adapter.
* **Responsibilities:**
  1. Direct vector text, font descriptor, and layout extraction via PyMuPDF for native digital PDFs.
  2. Lossless 300 DPI page rasterization for visual forensics, signature analysis, and OCR fallback.
  3. Multilingual OCR engine abstraction: route Devanagari and Latin text to high-accuracy models; support 12-language Indian roadmap.
  4. Script-aware text normalization (Unicode NFC/NFKD, numeral normalization from Devanagari/regional digits to Hindu-Arabic, currency symbol normalization).
  5. Layout structure and table extraction (evaluating Docling as an optional layout adapter alongside PyMuPDF).
  6. Signature region candidate localization and bounding box extraction.

### 3.4 Extraction Quality Assessment Engine (`capabilities/quality/`)
* **Responsibilities:**
  1. Compute page-level and token-level OCR confidence distributions across supported languages.
  2. Perform Vector-vs-Raster concordance checks to detect invisible text layers or altered rendering.
  3. Detect image degradation factors (blur variance $<100$, excessive skew $>2^\circ$, low contrast, illumination noise).
  4. Enforce quality gating: flag low-confidence extractions ($<0.65$) as unverified before ingestion by downstream rules.

### 3.5 Computer Vision & Signature Forensics Engine (`capabilities/forensics/`, `infrastructure/vision/`, `infrastructure/models/`)
* **Libraries:** `OpenCV` (`cv2`), `Pillow`, `numpy`, `scipy`, `onnxruntime` (local CPU inference).
* **Algorithms & Sub-Capabilities:**
  1. **Visual Forensics Suite:**
     * **Error Level Analysis (ELA):** Mathematical pixel subtraction (`|Original - Resaved_JPEG| * Scale`) highlighting compression discontinuities ($>35\%$ local variance).
     * **Font Baseline Regression:** Group glyph bounding boxes along horizontal baselines; flag offsets exceeding $2.5\sigma_y$ as suspicious insertions.
     * **Clone & Stamp Detection:** Multi-scale ORB feature matching and Structural Similarity (SSIM) detecting duplicated stamps or seals.
  2. **Signature Forensics Sub-Capability:**
     * **Localization:** Distinguish handwritten signature contours from printed form lines, stamps, and text.
     * **Offline Stroke Analysis:** Examine stroke continuity, curvature, proportions, and tracing indicators (hesitation marks, unnatural uniform velocity).
     * **Reference Comparison:** Compare questioned signatures against enrolled reference samples of authorized subjects using metric distance via local ONNX Runtime inference.
     * **Tampering Detection:** Detect reused signature cut-and-paste images, sharp boundary masks, and compression spikes around signature blocks.
     * **Forensic Guardrails:** Enforce 6-level assessment scale; visual similarity does not prove legal authorship or fraud.

### 3.6 Cross-Document Correlation Engine (`capabilities/correlation/`)
* **Libraries:** `RapidFuzz` (Levenshtein token sort ratio), multilingual concept dictionary.
* **Responsibilities:**
  1. Multi-file entity reconciliation across transaction packages (e.g. PO $\leftrightarrow$ Delivery Challan $\leftrightarrow$ Mill Test Certificate $\leftrightarrow$ Commercial Invoice).
  2. Cross-language field concept mapping ("Total Amount" $\leftrightarrow$ "एकूण रक्कम" $\leftrightarrow$ "कुल रकम").
  3. Construct contradiction matrix flagging quantity, rate, date chronology, consignee, or tax mismatches.

### 3.7 Contextual Reasoning Engine (`capabilities/reasoning/`, `domain/rules/`)
* **Deterministic Rules:** Pure Python intra-document arithmetic verification (PO subtotal + taxes = total; net weight = gross - tare) and date chronology rules.
* **Optional Grounded AI:** Groq ChatGroq synthesizing clear, evidence-grounded explanatory narratives over verified measurements without hallucinating facts.
* **Deterministic Offline Fallback:** 100% offline rule-template narrative generation when air-gapped or when cloud AI is disabled.

### 3.8 Investigation Dossier & Reporting Engine (`capabilities/reporting/`, `infrastructure/reporting/`)
* **Libraries:** `ReportLab`, Python `json`.
* **Responsibilities:**
  1. Programmatic compilation of the standardized 6-section PS-2 Investigation Dossier.
  2. Embedded 300 DPI high-resolution visual evidence crops and ELA heatmaps with pixel coordinates.
  3. Detailed Signature Forensics Verification Reports with reference sample provenance and uncertainty metrics.
  4. Cryptographic SHA-256 hashing of compiled PDF and JSON outputs for legal admissibility.

---

## 4. Application Services Layer (`application/services/`)

The application services act as an in-process facade between the PySide6 presentation layer and underlying capability engines:
* `InvestigationService`: Manages case lifecycle, CRUD operations, document associations, and high-level status.
* `DocumentService`: Handles file ingestion, SHA-256 calculation, and page image retrieval.
* `ForensicsService`: Dispatches CV analyses and retrieves pixel-anchored findings.
* `DossierService`: Invokes ReportLab to compile Section 7.1–7.6 PDF investigation dossiers.
* `JobQueueService`: Handles SQLite atomic job claims (`BEGIN IMMEDIATE`), heartbeats, and stale worker recovery.
