# 08_API_CONTRACTS.md
# VeriTrace Internal Application Service Contracts & Data Schemas

---

## 1. Interface Architecture Overview: Direct Python Service Contracts

In the VeriTrace PySide6 desktop architecture, communication between the presentation layer (`src/veritrace/gui/`) and the application layer (`src/veritrace/application/services/`) occurs via **strongly typed in-process Python service contracts**:
* **Superseded Architecture:** The previous local FastAPI loopback interface (`127.0.0.1:{dynamic_port}`) has been eliminated (see ADR-026). It introduced unnecessary serialization latency, ephemeral port collisions, Windows Defender firewall alerts, and security token management.
* **Direct In-Process Method Invocations:** The PySide6 UI controllers call Python application service methods directly. All calls are synchronous for fast database reads, or dispatched via Qt's `QThreadPool` / `QRunnable` for heavy processing.
* **Data Contracts:** All payloads are validated using **Pydantic v2** models, ensuring strict data integrity and type safety across domain boundaries.

---

## 2. Core Service Contracts

### 2.1 `InvestigationService` Contract
Manages the lifecycle and state transitions of multi-document investigation cases.

```python
class CreateInvestigationDTO(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    reference_code: str = Field(..., min_length=3, max_length=64)
    notes: Optional[str] = None

class InvestigationSummaryDTO(BaseModel):
    investigation_id: str
    title: str
    reference_code: str
    status: str
    risk_score: float
    document_count: int
    created_at: datetime
    updated_at: datetime

class IInvestigationService(ABC):
    @abstractmethod
    def create_investigation(self, dto: CreateInvestigationDTO) -> InvestigationSummaryDTO: ...
    
    @abstractmethod
    def get_investigation(self, investigation_id: str) -> InvestigationSummaryDTO: ...
    
    @abstractmethod
    def list_investigations(self) -> list[InvestigationSummaryDTO]: ...
    
    @abstractmethod
    def delete_investigation(self, investigation_id: str) -> bool: ...
```

---

### 2.2 `DocumentService` Contract
Manages file ingestion, cryptographic hashing, 300 DPI rasterization, and coordinate retrieval.

```python
class IngestDocumentDTO(BaseModel):
    investigation_id: str
    source_file_path: Path
    document_hint: Optional[str] = None

class DocumentDetailDTO(BaseModel):
    document_id: str
    investigation_id: str
    original_filename: str
    file_hash_sha256: str
    mime_type: str
    document_type: str
    page_count: int
    file_size_bytes: int
    storage_path: str
    uploaded_at: datetime

class IDocumentService(ABC):
    @abstractmethod
    def ingest_documents(self, dtos: list[IngestDocumentDTO]) -> list[DocumentDetailDTO]: ...
    
    @abstractmethod
    def get_document(self, document_id: str) -> DocumentDetailDTO: ...
    
    @abstractmethod
    def get_page_image_path(self, document_id: str, page_number: int) -> Path: ...
```

---

### 2.3 `JobQueueService` Contract
Manages asynchronous processing jobs, atomic claims (`BEGIN IMMEDIATE`), and progress reporting.

```python
class JobStatusDTO(BaseModel):
    job_id: str
    investigation_id: str
    status: str  # QUEUED, CLAIMED, RUNNING, COMPLETED, FAILED
    stage: str   # INTAKE, PAGE_RENDER, TEXT_EXTRACTION, VISUAL_FORENSICS, CROSS_MATCHING, DOSSIER_GEN
    progress_percent: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class IJobQueueService(ABC):
    @abstractmethod
    def enqueue_job(self, investigation_id: str) -> JobStatusDTO: ...
    
    @abstractmethod
    def claim_next_job(self, worker_id: str) -> Optional[JobStatusDTO]: ...
    
    @abstractmethod
    def update_progress(self, job_id: str, stage: str, percent: int) -> None: ...
    
    @abstractmethod
    def complete_job(self, job_id: str) -> None: ...
    
    @abstractmethod
    def fail_job(self, job_id: str, error: str) -> None: ...
```

---

### 2.4 `ForensicsService` Contract
Retrieves findings, coordinates, ELA heatmaps, and evidence anchors.

```python
class FindingDTO(BaseModel):
    finding_id: str
    investigation_id: str
    tier: str  # CONFIRMED_OBSERVATION, DETECTED_INCONSISTENCY, SUSPECTED_MANIPULATION
    category: str
    severity: str  # CRITICAL, WARNING, INFORMATIONAL
    title: str
    description: str
    metric_score: float
    evidence_anchors: list["EvidenceAnchorDTO"]

class EvidenceAnchorDTO(BaseModel):
    evidence_id: str
    page_id: str
    document_id: str
    page_number: int
    normalized_bbox: list[float]  # [ymin, xmin, ymax, xmax]
    crop_image_path: str
    heatmap_image_path: Optional[str]
    grounding_explanation: str

class SignatureVerificationDTO(BaseModel):
    signature_id: str
    document_id: str
    page_number: int
    normalized_bbox: list[float]
    subject_id: Optional[str]
    assessment: str  # 6-level scale (SIGNATURE_DETECTED, VISUAL_ANOMALY_OBSERVED, etc.)
    similarity_distance: Optional[float]
    threshold: Optional[float]
    stroke_anomaly_score: float
    is_clone_suspect: bool
    notes: str

class IForensicsService(ABC):
    @abstractmethod
    def get_findings(self, investigation_id: str, tier: Optional[str] = None) -> list[FindingDTO]: ...
    
    @abstractmethod
    def verify_signature(self, investigation_id: str, document_id: str, page_number: int, bbox: list[float], subject_id: Optional[str] = None) -> SignatureVerificationDTO: ...

    @abstractmethod
    def record_review_decision(self, finding_id: str, decision: str, notes: str) -> None: ...
```

---

### 2.5 `DossierService` Contract
Compiles and exports the PS-2 Section 7.1–7.6 Investigation Dossier.

```python
class DossierExportDTO(BaseModel):
    investigation_id: str
    pdf_path: str
    json_path: str
    file_hash_sha256: str
    generated_at: datetime

class IDossierService(ABC):
    @abstractmethod
    def generate_dossier(self, investigation_id: str) -> DossierExportDTO: ...
    
    @abstractmethod
    def get_dossier(self, investigation_id: str) -> Optional[DossierExportDTO]: ...
```
