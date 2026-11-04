# 19_DOMAIN_MODEL_SPECIFICATION.md
# Core Domain Model & Relational Schema Specification

---

## 1. Domain Model Architecture & Entity Rationalization

The VeriTrace domain model is structured to enforce **strict evidence chain-of-custody (ISO/IEC 27037)**, deterministic traceability, and complete separation between raw data, analytical measurements, and subjective human review.

### 1.1 Entity Rationalization & Justification

| Entity Name | Status | Engineering Justification |
| :--- | :---: | :--- |
| **`Investigation`** | **RETAINED** | Core root aggregate representing a multi-document forensic investigation case. |
| **`InvestigationJob`** | **NEW / RETAINED** | Tracks persistent asynchronous processing lifecycle, stage progress, and failure recovery. |
| **`Document`** | **RETAINED** | Represents an individual uploaded physical/digital file submitted within an investigation. |
| **`DocumentVersion`** | **EXCLUDED (PROTOTYPE)** | In the hackathon prototype, documents are treated as immutable evidence. Versioning is tracked via immutable file hashes (`file_hash_sha256`) and upload timestamps directly on `Document`. A separate `DocumentVersion` table is deferred to post-hackathon enterprise scope. |
| **`Page`** (`DocumentPage`) | **RETAINED** | Fundamental unit of visual inspection and coordinate reference. Bounding boxes are meaningless without page-level dimensions. |
| **`ExtractedField`** | **RETAINED** | Stores granular OCR tokens and parsed key-value pairs with normalized spatial coordinates `[ymin, xmin, ymax, xmax]`. |
| **`Entity`** | **RETAINED** | Represents a canonical real-world identity or fact (e.g., "Rajesh Sharma", "₹85,000") reconciled across multiple distinct documents. |
| **`ForensicAnalysis`** | **REFINED / EMBEDDED** | Rather than a disconnected generic table, raw analysis parameters (e.g., ELA quality, baseline deviation threshold) are recorded in the LangGraph state checkpoint and `AuditEvent` table, keeping the query model clean. |
| **`Finding`** | **RETAINED** | Standardized forensic conclusion categorized under the Three-Tier Epistemic Ontology (`CONFIRMED_OBSERVATION`, `DETECTED_INCONSISTENCY`, `SUSPECTED_MANIPULATION`). |
| **`Evidence`** | **RETAINED** | The physical visual crop and coordinate anchor that supports a `Finding`. Crucial: A Finding can have multiple Evidence anchors; an Evidence patch can support multiple findings. |
| **`CrossDocumentRelation`** | **RETAINED** | Maps semantic relationships (conflicts, confirmations, dependencies) between entities across two distinct documents. |
| **`ReviewDecision`** | **RETAINED** | Captures the human investigator's authoritative sign-off, dismissal, or note for a specific finding. |
| **`Dossier`** | **RETAINED** | Permanent record of generated investigation reports (PDF and JSON) with cryptographic output hashes. |
| **`AuditEvent`** | **RETAINED** | Immutable append-only event ledger for auditability and compliance. |

---

## 2. Complete Entity-Relationship (ER) Schema

```mermaid
erDiagram
    INVESTIGATION ||--o{ INVESTIGATION_JOB : "executes"
    INVESTIGATION ||--o{ DOCUMENT : "contains"
    INVESTIGATION ||--o{ ENTITY : "tracks"
    INVESTIGATION ||--o{ CROSS_DOCUMENT_RELATION : "identifies"
    INVESTIGATION ||--o{ FINDING : "produces"
    INVESTIGATION ||--o{ DOSSIER : "compiles"
    INVESTIGATION ||--o{ AUDIT_EVENT : "logs"

    DOCUMENT ||--o{ DOCUMENT_PAGE : "consists_of"
    DOCUMENT_PAGE ||--o{ EXTRACTED_FIELD : "yields"
    
    EXTRACTED_FIELD }o--o| ENTITY : "maps_to"
    
    DOCUMENT_PAGE ||--o{ EVIDENCE : "localizes"
    FINDING ||--|{ FINDING_EVIDENCE_MAP : "anchored_by"
    EVIDENCE ||--|{ FINDING_EVIDENCE_MAP : "supports"

    FINDING ||--o{ REVIEW_DECISION : "evaluated_by"

    CROSS_DOCUMENT_RELATION }o--|| DOCUMENT : "source_doc"
    CROSS_DOCUMENT_RELATION }o--|| DOCUMENT : "target_doc"
    CROSS_DOCUMENT_RELATION ||--o| FINDING : "triggers"
```

---

## 3. Detailed Entity Schema Definitions

### 3.1 `Investigation`
* **Table:** `investigations`
* **Purpose:** Root case entity.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `title` (`VARCHAR(255)`, NOT NULL): Human-readable label.
  * `reference_code` (`VARCHAR(64)`, UNIQUE, NOT NULL): Business case reference.
  * `status` (`VARCHAR(32)`, NOT NULL, DEFAULT `'DRAFT'`): `DRAFT`, `PROCESSING`, `WAITING_REVIEW`, `COMPLETED`, `FAILED`.
  * `risk_score` (`FLOAT`, DEFAULT `0.0`): Aggregate risk score in `[0.0, 1.0]`.
  * `risk_classification` (`VARCHAR(32)`, DEFAULT `'UNDETERMINED'`): `LOW_RISK`, `FLAGGED_INCONSISTENCY`, `SUSPECTED_MANIPULATION`.
  * `created_at` (`DATETIME`, NOT NULL): UTC creation timestamp.
  * `updated_at` (`DATETIME`, NOT NULL): UTC update timestamp.
* **Indexes:** `idx_inv_ref` (`reference_code`), `idx_inv_status` (`status`).

---

### 3.2 `InvestigationJob`
* **Table:** `investigation_jobs`
* **Purpose:** Manages persistent asynchronous processing lifecycle, stage progress, and failure recovery.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Parent investigation.
  * `status` (`VARCHAR(32)`, NOT NULL, DEFAULT `'QUEUED'`): `QUEUED`, `RUNNING`, `WAITING_REVIEW`, `COMPLETED`, `FAILED`.
  * `current_stage` (`VARCHAR(64)`, NOT NULL, DEFAULT `'INIT'`): Active processing capability stage.
  * `progress_pct` (`INTEGER`, NOT NULL, DEFAULT `0`): Overall completion percentage (0 - 100).
  * `stage_message` (`VARCHAR(255)`, NULLABLE): Human-readable status update.
  * `error_message` (`TEXT`, NULLABLE): Detailed error message if failed.
  * `can_resume` (`BOOLEAN`, NOT NULL, DEFAULT `FALSE`): Flag indicating eligibility for stage-level resume.
  * `started_at` (`DATETIME`, NULLABLE): UTC timestamp of job execution start.
  * `completed_at` (`DATETIME`, NULLABLE): UTC timestamp of job completion.
  * `created_at` (`DATETIME`, NOT NULL): UTC creation timestamp.
* **Indexes:** `idx_job_inv_status` (`investigation_id`, `status`).

---

### 3.3 `Document`
* **Table:** `documents`
* **Purpose:** Represents an ingested file.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Cascades on delete.
  * `original_filename` (`VARCHAR(255)`, NOT NULL): Name of uploaded file.
  * `file_hash_sha256` (`VARCHAR(64)`, NOT NULL): SHA-256 integrity hash.
  * `mime_type` (`VARCHAR(64)`, NOT NULL): `application/pdf`, `image/png`, `image/jpeg`.
  * `document_type` (`VARCHAR(64)`, NOT NULL, DEFAULT `'UNCLASSIFIED'`): `IDENTITY_PROOF`, `INCOME_PROOF`, `FINANCIAL_STATEMENT`, `COMMERCIAL_RECORD`, `GENERAL_AFFIDAVIT`.
  * `classification_confidence` (`FLOAT`, DEFAULT `0.0`): `[0.0 - 1.0]`.
  * `page_count` (`INTEGER`, NOT NULL, DEFAULT `1`): Number of pages.
  * `file_size_bytes` (`INTEGER`, NOT NULL): File size in bytes.
  * `storage_path` (`VARCHAR(512)`, NOT NULL): Path to stored raw binary.
  * `structured_content` (`JSON`, NULLABLE): Hierarchical key-value pairs and tables.
  * `metadata_json` (`JSON`, NULLABLE): PDF Producer, CreationDate, font descriptors.
  * `status` (`VARCHAR(32)`, NOT NULL, DEFAULT `'UPLOADED'`): `UPLOADED`, `PROCESSED`, `ERROR_CORRUPTED`.
  * `created_at` (`DATETIME`, NOT NULL): UTC timestamp.
* **Indexes:** `idx_doc_inv` (`investigation_id`), `idx_doc_hash` (`file_hash_sha256`).

---

### 3.4 `DocumentPage`
* **Table:** `document_pages`
* **Purpose:** Represents an individual rasterized page.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `document_id` (`VARCHAR(36)`, FK $\to$ `documents.id`, NOT NULL): Cascades on delete.
  * `page_number` (`INTEGER`, NOT NULL): 1-based page sequence number.
  * `width_pixels` (`INTEGER`, NOT NULL): Image width at 300 DPI render.
  * `height_pixels` (`INTEGER`, NOT NULL): Image height at 300 DPI render.
  * `image_storage_path` (`VARCHAR(512)`, NOT NULL): Relative path to rendered PNG.
  * `has_digital_text` (`BOOLEAN`, NOT NULL, DEFAULT `FALSE`): Vector text layer flag.
* **Constraints:** `UNIQUE(document_id, page_number)`.
* **Indexes:** `idx_page_doc_num` (`document_id`, `page_number`).

---

### 3.5 `ExtractedField`
* **Table:** `extracted_fields`
* **Purpose:** Stores extracted text tokens and structured key-values.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `page_id` (`VARCHAR(36)`, FK $\to$ `document_pages.id`, NOT NULL): Cascades on delete.
  * `entity_id` (`VARCHAR(36)`, FK $\to$ `entities.id`, NULLABLE): Mapped canonical entity.
  * `field_key` (`VARCHAR(128)`, NOT NULL): Normalized key (e.g., `net_pay`, `pan_number`).
  * `raw_value` (`TEXT`, NOT NULL): Extracted text string.
  * `normalized_value` (`TEXT`, NULLABLE): Cleaned value (e.g., standard date string or numeric float).
  * `confidence` (`FLOAT`, NOT NULL): OCR confidence in `[0.0, 1.0]`.
  * `norm_ymin` (`FLOAT`, NOT NULL): Normalized top coordinate in `[0.0, 1.0]`.
  * `norm_xmin` (`FLOAT`, NOT NULL): Normalized left coordinate in `[0.0, 1.0]`.
  * `norm_ymax` (`FLOAT`, NOT NULL): Normalized bottom coordinate in `[0.0, 1.0]`.
  * `norm_xmax` (`FLOAT`, NOT NULL): Normalized right coordinate in `[0.0, 1.0]`.
  * `extraction_source` (`VARCHAR(32)`, NOT NULL): `PYMUPDF_VECTOR`, `TESSERACT_OCR`.
* **Indexes:** `idx_field_page` (`page_id`), `idx_field_key` (`field_key`).

---

### 3.6 `Entity`
* **Table:** `entities`
* **Purpose:** Canonical identity or factual claim across the case.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Cascades on delete.
  * `entity_type` (`VARCHAR(64)`, NOT NULL): `PERSON_NAME`, `DATE_OF_BIRTH`, `GOVERNMENT_ID`, `EMPLOYER_NAME`, `FINANCIAL_TOTAL`.
  * `canonical_value` (`TEXT`, NOT NULL): Reconciled standardized representation.
* **Indexes:** `idx_entity_inv_type` (`investigation_id`, `entity_type`).

---

### 3.7 `Finding`
* **Table:** `findings`
* **Purpose:** Standardized investigation finding.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Cascades on delete.
  * `category` (`VARCHAR(64)`, NOT NULL): `ELA_COMPRESSION_VARIANCE`, `FONT_BASELINE_MISALIGNMENT`, `COPY_MOVE_CLONE`, `ARITHMETIC_MISMATCH`, `TEMPORAL_CONTRADICTION`, `CROSS_DOC_MISMATCH`.
  * `epistemic_tier` (`VARCHAR(32)`, NOT NULL): `CONFIRMED_OBSERVATION`, `DETECTED_INCONSISTENCY`, `SUSPECTED_MANIPULATION`.
  * `severity` (`VARCHAR(16)`, NOT NULL): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  * `title` (`VARCHAR(255)`, NOT NULL): Short summary.
  * `narrative_explanation` (`TEXT`, NOT NULL): Evidence-grounded explanation.
  * `investigator_guidance` (`TEXT`, NULLABLE): Recommended human verification steps.
  * `review_status` (`VARCHAR(32)`, NOT NULL, DEFAULT `'PENDING_REVIEW'`): `PENDING_REVIEW`, `CONFIRMED`, `DISMISSED`.
  * `created_at` (`DATETIME`, NOT NULL): UTC timestamp.
* **Indexes:** `idx_finding_inv` (`investigation_id`), `idx_finding_severity` (`severity`), `idx_finding_tier` (`epistemic_tier`).

---

### 3.8 `Evidence`
* **Table:** `evidence`
* **Purpose:** Pixel-level visual crop and coordinates supporting a finding.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `page_id` (`VARCHAR(36)`, FK $\to$ `document_pages.id`, NOT NULL): Source page.
  * `crop_image_path` (`VARCHAR(512)`, NOT NULL): Path to high-res visual patch PNG.
  * `heatmap_image_path` (`VARCHAR(512)`, NULLABLE): Path to ELA/contour heatmap PNG.
  * `pixel_x` (`INTEGER`, NOT NULL): Crop top-left X on 300 DPI image.
  * `pixel_y` (`INTEGER`, NOT NULL): Crop top-left Y on 300 DPI image.
  * `pixel_width` (`INTEGER`, NOT NULL): Crop width in pixels.
  * `pixel_height` (`INTEGER`, NOT NULL): Crop height in pixels.
  * `norm_ymin` (`FLOAT`, NOT NULL): Normalized top coordinate.
  * `norm_xmin` (`FLOAT`, NOT NULL): Normalized left coordinate.
  * `norm_ymax` (`FLOAT`, NOT NULL): Normalized bottom coordinate.
  * `norm_xmax` (`FLOAT`, NOT NULL): Normalized right coordinate.
* **Indexes:** `idx_evidence_page` (`page_id`).

---

### 3.9 `FindingEvidenceMap` (Association Table)
* **Table:** `finding_evidence_map`
* **Purpose:** Many-to-many relationship linking findings to visual evidence crops.
* **Fields:**
  * `finding_id` (`VARCHAR(36)`, FK $\to$ `findings.id`, PK): Finding reference.
  * `evidence_id` (`VARCHAR(36)`, FK $\to$ `evidence.id`, PK): Evidence reference.

---

### 3.10 `CrossDocumentRelation`
* **Table:** `cross_document_relations`
* **Purpose:** Explicit links between documents (conflicts, cross-references).
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Case scope.
  * `source_document_id` (`VARCHAR(36)`, FK $\to$ `documents.id`, NOT NULL): Document A.
  * `target_document_id` (`VARCHAR(36)`, FK $\to$ `documents.id`, NOT NULL): Document B.
  * `relation_type` (`VARCHAR(32)`, NOT NULL): `CONFLICTS_WITH`, `CORROBORATES`, `SUPPLEMENTS`.
  * `finding_id` (`VARCHAR(36)`, FK $\to$ `findings.id`, NULLABLE): Associated conflict finding.
  * `similarity_score` (`FLOAT`, NULLABLE): RapidFuzz score if entity comparison.
  * `description` (`TEXT`, NOT NULL): Detailed relation narrative.
* **Indexes:** `idx_rel_inv` (`investigation_id`), `idx_rel_src_tgt` (`source_document_id`, `target_document_id`).

---

### 3.11 `ReviewDecision`
* **Table:** `review_decisions`
* **Purpose:** Records human analyst verification and oversight.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `finding_id` (`VARCHAR(36)`, FK $\to$ `findings.id`, NOT NULL): Evaluated finding.
  * `reviewer_id` (`VARCHAR(64)`, NOT NULL): Investigator ID/handle.
  * `decision` (`VARCHAR(32)`, NOT NULL): `CONFIRMED`, `DISMISSED`, `ANNOTATED`.
  * `rationale` (`TEXT`, NOT NULL): Human justification.
  * `timestamp` (`DATETIME`, NOT NULL): UTC timestamp.
* **Indexes:** `idx_review_finding` (`finding_id`).

---

### 3.12 `Dossier`
* **Table:** `dossiers`
* **Purpose:** Records compiled investigation reports.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Associated case.
  * `dossier_json` (`JSON`, NOT NULL): Full 6-section PS-2 structured JSON payload.
  * `pdf_storage_path` (`VARCHAR(512)`, NOT NULL): File path to compiled PDF.
  * `pdf_hash_sha256` (`VARCHAR(64)`, NOT NULL): Cryptographic hash of generated PDF report.
  * `generated_at` (`DATETIME`, NOT NULL): UTC timestamp.
* **Indexes:** `idx_dossier_inv` (`investigation_id`).

---

### 3.13 `AuditEvent`
* **Table:** `audit_events`
* **Purpose:** Immutable append-only audit trail.
* **Fields:**
  * `id` (`VARCHAR(36)`, PK): UUIDv4 string.
  * `investigation_id` (`VARCHAR(36)`, FK $\to$ `investigations.id`, NOT NULL): Case context.
  * `event_type` (`VARCHAR(64)`, NOT NULL): `CASE_CREATED`, `DOC_UPLOADED`, `OCR_EXTRACTED`, `ANOMALY_FLAGGED`, `HUMAN_REVIEW_CONFIRMED`, `DOSSIER_COMPILED`.
  * `actor_type` (`VARCHAR(32)`, NOT NULL): `SYSTEM_PIPELINE`, `HUMAN_ANALYST`, `AI_SYNTHESIZER`.
  * `event_payload` (`JSON`, NOT NULL): Structured event parameters.
  * `timestamp` (`DATETIME`, NOT NULL): UTC timestamp.
* **Indexes:** `idx_audit_inv_time` (`investigation_id`, `timestamp`).
