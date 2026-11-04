# 02_SOURCE_CODE_AUDIT.md
# Source Code Audit of Migrated Foundation (UdyogPermit AI)

---

## 1. Executive Summary

This document records the exhaustive technical audit of the foundation source code migrated from the `UdyogPermit AI` repository into `VeriTrace`. The purpose of this audit is to catalogue the existing capabilities, verify actual source code implementations versus historical documentation claims, identify reusable architecture patterns, and explicitly document all technical debt and domain constraints.

**Audit Status:** All 53 non-cache source files have been copied into `VeriTrace` with 100% MD5 hash verification. The source repository was preserved in an unmodified, read-only state.

---

## 2. Source Code Inventory & Repository Structure

The migrated codebase consists of a two-tier full-stack application: a Python FastAPI backend and a Vite React frontend, containerized via a multi-stage Dockerfile.

```
VeriTrace/
├── Dockerfile                         # Multi-stage production container definition
├── .gitignore                         # Git exclusion rules
├── backend/
│   ├── main.py                        # FastAPI entrypoint & LangGraph workflow orchestration
│   ├── requirements.txt               # Backend Python dependencies
│   ├── bhuvan_checker.py              # ISRO Bhuvan OGC spatial compliance helper
│   ├── test_agent2_wrapper.py         # Test harness for Agent 2 execution
│   ├── agents/
│   │   ├── __init__.py                # Module initialization
│   │   ├── agent1.py                  # Profiler, enrichment, and clarification gate
│   │   ├── agent2.py                  # Regulatory compliance & subsidy determination
│   │   ├── agent3.py                  # Textual dependency roadmap generator
│   │   ├── agent4.py                  # ReactFlow visualizer DAG data generator
│   │   ├── category_classifier.py     # Deterministic industrial category matching
│   │   ├── resolver.py                # Regional office locator & Maharashtra rules
│   │   └── schemas.py                 # Pydantic models for industrial entities
│   └── geospatial/                    # Dedicated geospatial analysis micro-service
│       ├── .env.example
│       ├── catalog.py, config.py, engine.py, geometry.py, models.py, schemas.py
│       ├── service.py, sources.py, requirements.txt, README.md
│       └── providers/
│           ├── overpass.py            # OpenStreetMap Overpass API client
│           └── __init__.py
└── frontend/
    └── udyog-permit-frontend/
        ├── package.json               # Frontend dependencies & build scripts
        ├── package-lock.json          # Deterministic dependency lockfile
        ├── vite.config.js             # Vite 5 configuration
        ├── eslint.config.js           # ESLint configuration
        ├── index.html                 # HTML entrypoint
        ├── public/
        │   ├── favicon.svg
        │   └── icons.svg
        └── src/
            ├── main.jsx               # React DOM entrypoint
            ├── App.jsx                # Root UI state machine & tab navigator
            ├── Home.jsx               # Project submission form & hero section
            ├── Header.jsx             # Top navigation bar
            ├── Footer.jsx             # Application footer
            ├── WorkflowCanvas.jsx     # ReactFlow interactive DAG canvas
            ├── ApprovalNode.jsx       # Custom ReactFlow node component
            ├── elkLayout.js           # ELK.js layout engine integration
            ├── RightDetailPanel.jsx   # Slide-out detail drawer for nodes
            ├── AgentThinkingStatus.jsx# Step-by-step agent execution banner
            ├── GeospatialDashboard.jsx# Map display component
            ├── GeospatialScanConsole.jsx # Geospatial analysis console
            ├── index.css              # Tailwind CSS stylesheet
            └── assets/                # Static images and SVGs
```

---

## 3. Backend Architecture Audit

### 3.1 FastAPI Application ([`backend/main.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/main.py))
* **Application Initialization:** Initialized with title `"UdyogPermit AI Backend"` on FastAPI `>=0.115`.
* **CORS Middleware:** Configured with `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
* **Environment Configuration:** Reads `GROQ_API_KEY` and optional `GROQ_MODEL` (default: `"openai/gpt-oss-20b"`).
* **Static File Serving:** Mounts `/assets` from `backend/static/assets` and serves `backend/static/index.html` as a SPA catch-all route for production deployments.

### 3.2 LangGraph Orchestration ([`backend/main.py#L188-L226`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/main.py#L188-L226))
* **State Graph:** Utilizes `langgraph.graph.StateGraph` typed to `WorkflowState`.
* **In-Memory Checkpointing:** Uses `MemorySaver()`, which persists state only in volatile process RAM.
* **Nodes Defined:**
  * `profiler` (`run_agent_1`)
  * `classify_category` (`run_classify_category`)
  * `enrichment` (`run_agent_1_enrichment`)
  * `completeness_gate` (`run_completeness_gate`)
  * `question_generation` (`run_question_generation`)
  * `clarify_wait` (`clarify_wait_node`)
  * `merge_clarification_answers` (`run_merge_clarification_answers`)
  * `regulatory` (`run_agent_2`)
  * `hitl_wait` (`human_in_the_loop_node`)
  * `planner` (`run_agent_3`)
  * `visualizer` (`run_agent_4`)
* **Conditional Edges:** Routes from `completeness_gate` to either `regulatory` or `question_generation`.
* **Human-in-the-Loop Interrupts:** Graph is compiled with `interrupt_before=["clarify_wait", "hitl_wait"]`.

### 3.3 Agent Implementations ([`backend/agents/`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/))

| Agent File | Actual Verified Functionality | Reusability in VeriTrace |
| :--- | :--- | :--- |
| [`agent1.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/agent1.py) | Extracts industrial profile (power, land, emissions) from raw text; manages clarification loops. | Pattern of state gating and LLM parsing is reusable; industrial fields must be replaced. |
| [`agent2.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/agent2.py) | Analyzes compliance permits (PCB, Fire, Factory) and subsidy schemes using Groq JSON mode. | Multi-rule evaluation pattern is reusable; permit logic must be replaced with forensic checks. |
| [`agent3.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/agent3.py) | Generates a sequential Markdown roadmap explaining dependencies. | Reusable as the narrative synthesis generator for the Investigation Dossier. |
| [`agent4.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/agent4.py) | Transforms state into ReactFlow nodes, edges, and swimlanes with layout coordinates. | Highly reusable for transforming cross-document evidence into a visual relationship graph. |
| [`category_classifier.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/category_classifier.py) | Keyword-based matching of industrial facilities into Red/Orange/Green/White pollution categories. | Irrelevant to document forensics; to be deprecated. |
| [`resolver.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/resolver.py) | Massive 33KB hardcoded registry of Maharashtra government offices, districts, and approvals. | Irrelevant to document forensics; to be deprecated. |

### 3.4 Pydantic Schemas ([`backend/agents/schemas.py`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/agents/schemas.py))
* Uses Pydantic V2 (`pydantic>=2.0`).
* Defines `IndustrialProfile`, `RequiredApproval`, `Subsidy`, `FlowNode`, `FlowEdge`, `FlowLayoutData`, and `ClarificationQuestion`.
* Fully typed models with `Field(...)` descriptions, enabling automatic JSON schema generation for Groq structured output.

### 3.5 Existing Document Validation Endpoint ([`backend/main.py#L340-L354`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/main.py#L340-L354))
* **Verified Implementation:**
  ```python
  @app.post("/api/v1/document/validate")
  async def validate_document(req: DocumentValidationRequest):
      text_llm = ChatGroq(api_key=api_key, model=GROQ_MODEL, temperature=0.1)
      sys_prompt = "You are a Document Pre-Validation AI. Check for missing mandatory fields, signatures, or engineer seals. Output Pass/Fail and fix recommendations."
      response = text_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=req.document_text)])
      return {"validation_report": response.content}
  ```
* **Critical Finding:** This endpoint is a rudimentary text-in/text-out prompt. It performs **no OCR, no file upload parsing, no image processing, no bounding box generation, and has no grounding**. It is completely inadequate for PS-2 and must be replaced.

### 3.6 Geospatial & ISRO Bhuvan Module ([`backend/geospatial/`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/backend/geospatial/))
* Complex GIS engine using `shapely`, `pyproj`, and OpenStreetMap Overpass querying buffers around latitude/longitude coordinates.
* `bhuvan_checker.py` sends OGC requests to ISRO Bhuvan WMS servers to detect eco-sensitive zones.
* **Finding:** Entirely outside the scope of PS-2 Document Forensics. Must be isolated and deprecated.

---

## 4. Frontend Architecture Audit

### 4.1 Technology Stack ([`frontend/udyog-permit-frontend/package.json`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/package.json))
* **Framework:** React 18.3.1 with Vite 5.4.1
* **Styling:** Tailwind CSS 4.0.0
* **Graphing & Visualization:**
  * `@xyflow/react` v12.11.6 (ReactFlow v12)
  * `elkjs` v0.12.0 (Eclipse Layout Kernel for automated DAG layout)
  * `@tisoap/react-flow-smart-edge` v5.0.0 & `@jalez/react-flow-smart-edge` v4.0.0
  * `@dagrejs/dagre` v3.1.1
* **Icons:** `lucide-react` v1.41.0

### 4.2 Component Breakdown & Visual Capabilities

| Component | Source Path | Key Verified Features | Reusability in VeriTrace |
| :--- | :--- | :--- | :--- |
| **`WorkflowCanvas.jsx`** | [`src/WorkflowCanvas.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/WorkflowCanvas.jsx) | ReactFlow canvas with MiniMap, Controls, Background grid, custom node rendering, node click selection, and responsive zoom/pan. | **HIGH (KEEP/MODIFY):** Serves directly as the Document-Evidence Relational Graph viewer. |
| **`ApprovalNode.jsx`** | [`src/ApprovalNode.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/ApprovalNode.jsx) | Custom ReactFlow node with status badges, icons, department tags, and handle connection points. | **HIGH (MODIFY):** Repurpose into `DocumentNode` and `EvidenceNode`. |
| **`elkLayout.js`** | [`src/elkLayout.js`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/elkLayout.js) | Asynchronous layout calculation organizing nodes into layered hierarchical swimlanes. | **HIGH (KEEP):** Automatically arranges documents, extracted entities, and anomaly clusters. |
| **`RightDetailPanel.jsx`** | [`src/RightDetailPanel.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/RightDetailPanel.jsx) | Slide-out drawer with tabs, status tags, document checklists, and action buttons. | **HIGH (MODIFY):** Adapt into the **Evidence Inspector** to display bounding box crops, confidence scores, and ELA heatmaps. |
| **`AgentThinkingStatus.jsx`** | [`src/AgentThinkingStatus.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/AgentThinkingStatus.jsx) | Animated execution status indicator showing which agent is processing in real-time. | **HIGH (MODIFY):** Update agent step labels to match the 10-stage forensic workflow. |
| **`Home.jsx`** | [`src/Home.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/Home.jsx) | Massive 77KB single-page form for entering industrial project details, capital investment, and location. | **LOW (REPLACE):** Replace with a clean Multi-Document Investigation Upload & Case Setup interface. |
| **`App.jsx`** | [`src/App.jsx`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/frontend/udyog-permit-frontend/src/App.jsx) | Orchestrates navigation state, API calls (`/start`, `/clarify`, `/resume`), and modal overlays. | **MEDIUM (MODIFY):** Adapt state flow to handle multi-file uploads and forensic investigation stages. |

---

## 5. Docker & Containerization Audit ([`Dockerfile`](file:///c:/Users/ghong/OneDrive/Attachments/Desktop/VeriTrace/Dockerfile))

The existing Dockerfile implements a two-stage build:
1. `node:20-alpine` builds the Vite production static bundle.
2. `python:3.11-slim` installs Python requirements and runs Uvicorn on dynamic port `$PORT`.
3. Frontend static files are copied to `/app/static` and served directly by FastAPI.

**Audit Finding for VeriTrace:**
* `python:3.11-slim` lacks native system shared libraries required for OpenCV (`libgl1`, `libglib2.0-0`) and Tesseract OCR (`tesseract-ocr`).
* When transitioning to active containerization in Phase 7, the Dockerfile must be modified to install these native system dependencies.

---

## 6. Audit of Existing Limitations & Technical Debt

1. **Volatile In-Memory Persistence:**
   * The backend relies exclusively on `MemorySaver()` in LangGraph. All threads, states, and history disappear whenever the Uvicorn process restarts.
   * There is no SQLite, PostgreSQL, or disk database.
2. **Missing Forensic & Vision Libraries:**
   * No computer vision (`opencv-python`), image manipulation (`pillow`), PDF parsing (`pymupdf`), or fuzzy matching (`rapidfuzz`) libraries are currently present in `backend/requirements.txt`.
3. **No File Upload or Storage Pipeline:**
   * The existing endpoints only accept JSON strings (`raw_industrial_data`, `document_text`). There is no `multipart/form-data` file upload endpoint, no file caching directory, and no PDF page rasterization engine.
4. **Hardcoded Industrial Domain Logic:**
   * Core files (`agent1.py`, `agent2.py`, `resolver.py`, `category_classifier.py`) are tightly bound to industrial environmental clearances, water consumption, power thresholds, and Maharashtra state authorities.
5. **Lack of Evidence Grounding:**
   * The existing validation endpoint generates subjective text evaluations with zero link to visual evidence or pixel coordinates.

---

## 7. Reusability Assessment Matrix

| Architecture Component | Migrated File Reference | Audit Verdict | VeriTrace Role |
| :--- | :--- | :---: | :--- |
| **FastAPI Core & CORS** | `backend/main.py` | **KEEP** | API routing foundation and static production host. |
| **LangGraph StateGraph** | `backend/main.py` | **MODIFY** | Core orchestrator for the 10-stage forensic pipeline. |
| **Groq ChatGroq Client** | `backend/main.py` | **KEEP** | High-speed LLM reasoning with JSON mode enforcement. |
| **ELK.js Layout Engine** | `frontend/.../elkLayout.js` | **KEEP** | Automated layout for multi-document evidence DAG. |
| **ReactFlow Canvas** | `frontend/.../WorkflowCanvas.jsx` | **KEEP** | Interactive Document-to-Evidence graph visualizer. |
| **Evidence Drawer** | `frontend/.../RightDetailPanel.jsx` | **MODIFY** | Slide-out panel for inspecting anomalies and crops. |
| **Thinking Status Banner**| `frontend/.../AgentThinkingStatus.jsx` | **MODIFY** | Live pipeline execution tracker. |
| **Multi-Stage Dockerfile**| `Dockerfile` | **MODIFY** | Containerization with added CV/OCR native libraries. |
| **Industrial Agents (1-3)**| `backend/agents/agent[1-3].py` | **REPLACE** | Replace with Ingestion, Forensics, and Dossier agents. |
| **Geospatial & Bhuvan** | `backend/geospatial/`, `bhuvan_checker.py` | **DEPRECATE** | Quarantine; isolate from active routing. |
| **Industrial Registry** | `backend/agents/resolver.py` | **DEPRECATE** | Quarantine; isolate from active routing. |
