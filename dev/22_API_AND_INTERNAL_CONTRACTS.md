# 22_API_AND_INTERNAL_CONTRACTS.md
# Internal Application Service Specifications & Python Capability Contracts

---

## 1. Interface Architecture Overview: Direct Python In-Process Contracts

In VeriTrace Desktop, the previous local HTTP REST loopback gateway (`127.0.0.1:{dynamic_port}`) is replaced by **direct in-process Python application services** (see ADR-026 and ADR-030):
* **Direct Python Method Calls:** The PySide6 UI controllers call Python Application Services (`src/veritrace/application/services/`) directly. This completely eliminates JSON serialization overhead, ephemeral port binding conflicts, Windows Firewall prompts, and security token management.
* **Dual Execution Model:**
  1. **Synchronous Data Operations:** File metadata retrieval, case listings, and review decisions execute synchronously and return immediately.
  2. **Asynchronous Processing Pipeline:** Multi-document processing (300 DPI rasterization, OCR, extraction quality scoring, ELA computation, and cross-document reconciliation) is submitted to Qt's `QThreadPool` / `QRunnable` (or decoupled `src/veritrace/workers/job_runner.py`), executing across background worker threads without blocking the Qt event loop.
  3. **Reactive Progress Telemetry:** Background tasks emit custom Qt Signals (`progress_updated`, `stage_changed`, `pipeline_finished`, `pipeline_failed`), allowing the status bar and document viewer to update smoothly and reactively.

---

## 2. Application Services Interface Specifications

### 2.1 `InvestigationService`
* **File:** `src/veritrace/application/services/investigation_service.py`
* **Methods:**
  * `create_investigation(title: str, reference_code: str, notes: Optional[str] = None) -> InvestigationDTO`: Creates case container in SQLite.
  * `get_investigation(investigation_id: str) -> InvestigationDetailDTO`: Retrieves case details, risk score, and document counts.
  * `list_investigations() -> list[InvestigationSummaryDTO]`: Retrieves all cases for the sidebar.
  * `delete_investigation(investigation_id: str) -> bool`: Cascades deletion across documents and evidence files.

### 2.2 `DocumentService`
* **File:** `src/veritrace/application/services/document_service.py`
* **Methods:**
  * `ingest_documents(investigation_id: str, file_paths: list[Path]) -> list[DocumentDTO]`: Validates magic bytes, calculates SHA-256 digests, stores originals in `%LOCALAPPDATA%/VeriTrace/investigations/{id}/originals/`, and inserts records.
  * `get_document_pages(document_id: str) -> list[PageDTO]`: Returns page numbers and dimensions.
  * `get_page_image_path(document_id: str, page_number: int) -> Path`: Returns relative path to rendered 300 DPI PNG.

### 2.3 `JobQueueService`
* **File:** `src/veritrace/application/services/job_service.py`
* **Methods:**
  * `enqueue_job(investigation_id: str) -> JobStatusDTO`: Inserts a job record in `investigation_jobs` (`status='QUEUED'`). Rejects duplicate active jobs.
  * `claim_next_job(worker_id: str) -> Optional[JobStatusDTO]`: Atomically claims the next pending job using SQLite `BEGIN IMMEDIATE`.
  * `update_progress(job_id: str, stage: str, progress_percent: int) -> None`: Updates stage and heartbeat.
  * `complete_job(job_id: str) -> None`: Marks job completed (100%).
  * `fail_job(job_id: str, error_message: str) -> None`: Records failure diagnostic.

### 2.4 `ForensicsService`
* **File:** `src/veritrace/application/services/forensics_service.py`
* **Methods:**
  * `get_findings(investigation_id: str, tier: Optional[str] = None) -> list[FindingDTO]`: Retrieves 3-tier findings.
  * `get_evidence_anchor(evidence_id: str) -> EvidenceAnchorDTO`: Retrieves high-res crop path, ELA heatmap path, and normalized coordinates `[ymin, xmin, ymax, xmax]`.
  * `verify_signature(investigation_id: str, document_id: str, page_number: int, bbox: list[float], subject_id: Optional[str] = None) -> SignatureVerificationDTO`: Extracts signature features via local ONNX Runtime CPU inference and evaluates against reference profile using the 6-level forensic assessment scale.
  * `record_review_decision(finding_id: str, decision: str, notes: str) -> ReviewDecisionDTO`: Persists human investigator decision (`CONFIRMED`, `DISMISSED`).

### 2.5 `DossierService`
* **File:** `src/veritrace/application/services/dossier_service.py`
* **Methods:**
  * `generate_dossier(investigation_id: str) -> DossierExportDTO`: Compiles the PS-2 Section 7.1–7.6 report via ReportLab and serializes structured JSON, including specialized Signature Verification Reports.
  * `get_dossier(investigation_id: str) -> Optional[DossierExportDTO]`: Retrieves existing compiled report paths and SHA-256 hashes.

---

## 3. Internal Capability Protocols (Pure Python Interfaces)

```python
from typing import Protocol, List, Optional
from pathlib import Path
from veritrace.domain.models import (
    ExtractedToken,
    ELAResult,
    BaselineAnomaly,
    GroundedFinding,
    SignatureResult,
)

class DocumentRasterizerProtocol(Protocol):
    def render_pages(self, pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]: ...

class TextExtractorProtocol(Protocol):
    def extract_tokens(self, pdf_path: Path, page_num: int, raster_path: Path, lang: str = "eng") -> list[ExtractedToken]: ...

class VisualForensicsProtocol(Protocol):
    def compute_ela(self, image_path: Path, quality: int = 90) -> ELAResult: ...
    def detect_baseline_misalignments(self, tokens: list[ExtractedToken]) -> list[BaselineAnomaly]: ...

class SignatureForensicsProtocol(Protocol):
    def detect_signatures(self, page_image_path: Path) -> list[dict]: ...
    def verify_against_reference(self, signature_crop_path: Path, reference_id: str) -> SignatureResult: ...

class DossierCompilerProtocol(Protocol):
    def compile_pdf_dossier(self, investigation_id: str, findings: list[GroundedFinding], output_path: Path) -> Path: ...
```
