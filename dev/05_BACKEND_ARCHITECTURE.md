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
├── capabilities/                      # Algorithmic & Forensic Processing Engines
│   ├── ingestion/                     # File validation, MIME checking, SHA-256 calculation
│   ├── extraction/                    # PDF vector text extraction, OCR raster extraction
│   ├── quality/                       # Extraction Quality: OCR confidence scoring, degradation assessment
│   ├── forensics/                     # Visual forensics (ELA, baseline alignment, copy-move), PDF metadata
│   ├── correlation/                   # Cross-document entity reconciliation & contradiction matrix
│   ├── reasoning/                     # Contextual intelligence narrative synthesis & prompt engineering
│   └── reporting/                     # PS-2 Section 7.1–7.6 PDF & JSON dossier compilation
│
├── infrastructure/                    # Concrete Technical Adapters
│   ├── persistence/                   # SQLite database (WAL mode), SQLAlchemy 2.0 ORM, Alembic migrations
│   ├── pdf/                           # PyMuPDF rasterizer & vector text adapter
│   ├── ocr/                           # Tesseract / RapidOCR engine adapter
│   ├── vision/                        # OpenCV & Pillow image processing adapter
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

## 3. Core Capability Specifications

### 3.1 Document Ingestion & Storage (`capabilities/ingestion/`)
* **Libraries:** Python standard library (`hashlib`, `mimetypes`, `pathlib`).
* **Responsibilities:**
  1. Validate file header magic bytes (PDF `%PDF-`, PNG `\x89PNG`, JPEG `\xFF\xD8\xFF`).
  2. Compute SHA-256 hash immediately upon file intake to guarantee chain-of-custody.
  3. Store immutable originals under `%LOCALAPPDATA%/VeriTrace/cases/<case_id>/documents/originals/`.

### 3.2 PDF & Page Rasterization Engine (`infrastructure/pdf/`, `capabilities/extraction/`)
* **Library:** `PyMuPDF` (`import fitz`).
* **Responsibilities:**
  1. Inspect PDF metadata (Creator, Producer, CreationDate, ModDate).
  2. Render every page to a lossless PNG image at 300 DPI (`zoom = 300 / 72 ≈ 4.166`) for visual forensic examination and UI display.
  3. Extract direct vector text blocks with exact bounding box coordinates: `[x0, y0, x1, y1]`.

### 3.3 Hybrid OCR Engine (`capabilities/extraction/`, `infrastructure/ocr/`)
* **Libraries:** `PyMuPDF` for native digital text; `pytesseract` (backed by Tesseract OCR) for scanned images and raster overlays.
* **Responsibilities:**
  1. If vector text is available and consistent, extract words, lines, and spans directly.
  2. For scanned pages or image regions without vector text, apply image pre-processing (grayscale, Otsu thresholding, deskewing) and invoke Tesseract OCR with `output_type=Output.DICT`.
  3. Capture token text, normalized bounding box `[ymin, xmin, ymax, xmax]`, and token-level confidence score `[0.0 - 1.0]`.

### 3.4 Extraction Quality Assessment Engine (`capabilities/quality/`)
* **Responsibilities:**
  1. Compute page-level and token-level OCR confidence distributions.
  2. Perform Vector-vs-Raster concordance checks to detect invisible text layers or altered rendering.
  3. Detect image degradation factors (blur variance $<100$, excessive skew $>2^\circ$, low contrast).
  4. Enforce quality gating: flag low-confidence extractions as unverified before ingestion by downstream rules.

### 3.5 Computer Vision Forensics Engine (`capabilities/forensics/`, `infrastructure/vision/`)
* **Libraries:** `OpenCV` (`cv2`), `Pillow` (`PIL.Image`, `PIL.ImageChops`, `PIL.ImageEnhance`), `numpy`.
* **Algorithms Implemented:**
  1. **Error Level Analysis (ELA):**
     * Save the original image as a temporary JPEG at quality `90%`.
     * Compute pixel-wise difference: `diff = ImageChops.difference(original, resaved)`.
     * Scale brightness by multiplier (e.g., `15x`) to highlight compression discontinuities.
     * Calculate localized variance; flag clusters exceeding background noise by $>35\%$.
  2. **Font & Baseline Deviation Analysis:**
     * Group extracted character bounding boxes along horizontal text lines.
     * Compute mean baseline $y$-coordinate and standard deviation $\sigma_y$.
     * Flag glyphs with baseline offset exceeding $2.5\sigma_y$ as potential insertions or modifications.
  3. **Signature & Clone Detection:**
     * Extract high-contrast stroke contours.
     * Match features across documents using ORB and Structural Similarity (SSIM).

### 3.6 Contextual Rules & Cross-Document Correlation (`domain/rules/`, `capabilities/correlation/`)
* **Intra-Document Rules:** Deterministic arithmetic verifications (Gross = Basic + HRA + Allowances; Net = Gross - Deductions) and format regexes (PAN, Aadhaar).
* **Cross-Document Correlation:** Fuzzy entity alignment via `RapidFuzz` (token sort ratio $>85\%$), detecting cross-file name, birthdate, and financial discrepancies.

---

## 4. Application Services Layer (`application/services/`)

The application services act as an in-process facade between the PySide6 presentation layer and underlying capability engines:
* `InvestigationService`: Manages case lifecycle, CRUD operations, document associations, and high-level status.
* `DocumentService`: Handles file ingestion, SHA-256 calculation, and page image retrieval.
* `ForensicsService`: Dispatches CV analyses and retrieves pixel-anchored findings.
* `DossierService`: Invokes ReportLab to compile Section 7.1–7.6 PDF investigation dossiers.
* `JobQueueService`: Handles SQLite atomic job claims (`BEGIN IMMEDIATE`), heartbeats, and stale worker recovery.
