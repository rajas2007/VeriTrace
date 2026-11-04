import os
import uuid
from typing import Any, List, Dict, Literal, TypedDict, Optional


from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from agents.agent1 import (
    agent_1_profiler,
    agent_1_enrichment,
    agent_1_completeness_gate,
    agent_1_generate_questions,
    agent_1_merge_clarification_answers,
)
from agents.agent2 import agent_2_regulatory
from agents.agent3 import agent_3_planner
from agents.agent4 import agent_4_visualizer
from agents.category_classifier import classify_category
from geospatial.models import GeospatialRequest
from geospatial.service import GeospatialService
# Load environment variables
load_dotenv()

# Global in-memory holder for the latest Bhuvan compliance scan
geospatial_data_holder: Optional[Dict[str, Any]] = None

class MatrixGenerationRequest(BaseModel):
    project_text: str
    # Add any other payload fields required by your application

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from environment variables or .env file!")

# Initialize FastAPI App
app = FastAPI(title="UdyogPermit AI Backend", version="1.0.0")

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq model used by all agents.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

# Shared structured-output LLM for Agents 1, 2 and 4.
llm = ChatGroq(
    api_key=api_key,
    model=GROQ_MODEL,
    temperature=0.1,
    model_kwargs={"response_format": {"type": "json_object"}},
)

# ==========================================
# State & Data Models
# ==========================================

class WorkflowState(TypedDict):
    raw_input: str
    profile: dict
    compliances: list
    eligible_subsidies: list
    selected_subsidies: list
    roadmap: str
    ui_data: dict
    geospatial_data: dict
    # --- Clarifying-questions extension to Agent 1 (additive; nothing above changes) ---
    category: str
    pollution_category: str
    profile_status: Literal["complete", "needs_clarification"]
    missing_fields: list
    clarification_questions: list
    clarification_answers: dict
    clarification_round: int
    defaulted_fields: list


class StartWorkflowRequest(BaseModel):
    raw_industrial_data: str


class ResumeWorkflowRequest(BaseModel):
    thread_id: str
    selected_subsidies: List[Dict[str, str]]


class DocumentValidationRequest(BaseModel):
    document_text: str


class ClarifyAnswer(BaseModel):
    field: str
    answer: Any = None
    skipped: bool = False


class ClarifyWorkflowRequest(BaseModel):
    thread_id: str
    answers: List[ClarifyAnswer]


# ==========================================
# Agent Node Adapters
# ==========================================
# The actual agent implementations live in backend/agents/agent1.py ... agent4.py.
# These small adapters keep LangGraph's node interface clean while injecting the
# shared LLM dependency from this application module.


def run_agent_1(state: WorkflowState) -> WorkflowState:
    return agent_1_profiler(state, llm)


# --- Clarifying-questions extension node adapters (additive) ---

def run_classify_category(state: WorkflowState) -> WorkflowState:
    state["category"] = classify_category((state.get("profile") or {}).get("facility_type", ""))
    return state


def run_agent_1_enrichment(state: WorkflowState) -> WorkflowState:
    return agent_1_enrichment(state, llm)


def run_completeness_gate(state: WorkflowState) -> WorkflowState:
    return agent_1_completeness_gate(state)


def run_question_generation(state: WorkflowState) -> WorkflowState:
    return agent_1_generate_questions(state, llm)


def clarify_wait_node(state: WorkflowState) -> WorkflowState:
    """Checkpoint node used by LangGraph for the (conditional) clarification pause."""
    return state


def run_merge_clarification_answers(state: WorkflowState) -> WorkflowState:
    return agent_1_merge_clarification_answers(state)


def route_after_completeness_gate(state: WorkflowState) -> str:
    return "regulatory" if state.get("profile_status") == "complete" else "question_generation"


def run_agent_2(state: WorkflowState) -> WorkflowState:
    return agent_2_regulatory(state, llm)


def run_agent_3(state: WorkflowState) -> WorkflowState:
    # Agent 3 intentionally uses a non-JSON response because its output is prose.
    text_llm = ChatGroq(
        api_key=api_key,
        model=GROQ_MODEL,
        temperature=0.2,
    )
    return agent_3_planner(state, text_llm)


def run_agent_4(state: WorkflowState) -> WorkflowState:
    return agent_4_visualizer(state, llm)


def human_in_the_loop_node(state: WorkflowState) -> WorkflowState:
    """Checkpoint node used by LangGraph for the HITL pause."""
    return state


# ==========================================
# Graph Compilation & HITL Checkpointer
# ==========================================

memory = MemorySaver()
workflow = StateGraph(WorkflowState)

workflow.add_node("profiler", run_agent_1)
# --- Clarifying-questions extension nodes (additive) ---
workflow.add_node("classify_category", run_classify_category)
workflow.add_node("enrichment", run_agent_1_enrichment)
workflow.add_node("completeness_gate", run_completeness_gate)
workflow.add_node("question_generation", run_question_generation)
workflow.add_node("clarify_wait", clarify_wait_node)
workflow.add_node("merge_clarification_answers", run_merge_clarification_answers)
# --- Agents 2-4 nodes: unchanged ---
workflow.add_node("regulatory", run_agent_2)
workflow.add_node("hitl_wait", human_in_the_loop_node)
workflow.add_node("planner", run_agent_3)
workflow.add_node("visualizer", run_agent_4)

workflow.add_edge(START, "profiler")
workflow.add_edge("profiler", "classify_category")
workflow.add_edge("classify_category", "enrichment")
workflow.add_edge("enrichment", "completeness_gate")
workflow.add_conditional_edges(
    "completeness_gate",
    route_after_completeness_gate,
    {"regulatory": "regulatory", "question_generation": "question_generation"},
)
workflow.add_edge("question_generation", "clarify_wait")
workflow.add_edge("clarify_wait", "merge_clarification_answers")
workflow.add_edge("merge_clarification_answers", "completeness_gate")
# --- Agent 2 onward: unchanged edges ---
workflow.add_edge("regulatory", "hitl_wait")
workflow.add_edge("hitl_wait", "planner")
workflow.add_edge("planner", "visualizer")
workflow.add_edge("visualizer", END)

app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["clarify_wait", "hitl_wait"],
)

# ==========================================
# API Endpoints
# ==========================================

def _clarification_response(thread_id: str, current_state: dict) -> dict:
    return {
        "thread_id": thread_id,
        "status": "needs_clarification",
        "profile": current_state.get("profile"),
        "category": current_state.get("category"),
        "pollution_category": current_state.get("pollution_category"),
        "clarification_questions": current_state.get("clarification_questions", []),
        "clarification_round": current_state.get("clarification_round", 0),
    }


@app.post("/api/v1/workflow/start")
async def start_workflow(req: StartWorkflowRequest):
    global geospatial_data_holder

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Inject cached geospatial scan if present
    initial_state = {
        "raw_input": req.raw_industrial_data,
        "geospatial_data": geospatial_data_holder if geospatial_data_holder else {},
        "clarification_round": 0
    }

    if geospatial_data_holder:
        print("[SUCCESS] Injected geospatial_data_holder into WorkflowState.")
    else:
        print("[WARNING] No geospatial scan found in holder. Initializing workflow with empty spatial data.")

    app_graph.invoke(initial_state, config=config)
    snapshot = app_graph.get_state(config)
    current_state = snapshot.values

    if snapshot.next and "clarify_wait" in snapshot.next:
        return _clarification_response(thread_id, current_state)

    return {
        "thread_id": thread_id,
        "status": "waiting_for_user_input",
        "profile": current_state.get("profile"),
        "compliances": current_state.get("compliances"),
        "eligible_subsidies": current_state.get("eligible_subsidies"),
        "geospatial_data": current_state.get("geospatial_data")
    }


@app.post("/api/v1/workflow/clarify")
async def clarify_workflow(req: ClarifyWorkflowRequest):
    """Resume a thread paused at the (conditional) clarification interrupt.

    Mirrors /workflow/resume's shape/conventions but targets the
    clarify_wait interrupt point instead of hitl_wait. Answers are merged
    into the profile deterministically, then the completeness gate re-runs
    (capped at 2 rounds) before eventually handing off to Agent 2 exactly as
    the unmodified /workflow/start path already does.
    """
    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot = app_graph.get_state(config)
    if not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="Thread is not waiting for input or does not exist.",
        )

    answers_payload = {a.field: {"answer": a.answer, "skipped": a.skipped} for a in req.answers}
    app_graph.update_state(config, {"clarification_answers": answers_payload})
    try:
        app_graph.invoke(None, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow error during clarification: {exc}")

    snapshot = app_graph.get_state(config)
    current_state = snapshot.values

    if snapshot.next and "clarify_wait" in snapshot.next:
        return _clarification_response(req.thread_id, current_state)

    return {
        "thread_id": req.thread_id,
        "status": "waiting_for_user_input",
        "profile": current_state.get("profile"),
        "compliances": current_state.get("compliances"),
        "eligible_subsidies": current_state.get("eligible_subsidies"),
    }


@app.post("/api/v1/workflow/resume")
async def resume_workflow(req: ResumeWorkflowRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    state_snapshot = app_graph.get_state(config)
    if not state_snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="Thread is not waiting for input or does not exist.",
        )

    app_graph.update_state(config, {"selected_subsidies": req.selected_subsidies})
    final_output = app_graph.invoke(None, config=config)

    return {
        "status": "completed",
        "dependency_roadmap": final_output.get("roadmap"),
        "ui_swimlane_data": final_output.get("ui_data"),
    }


@app.post("/api/v1/document/validate")
async def validate_document(req: DocumentValidationRequest):
    text_llm = ChatGroq(
        api_key=api_key,
        model=GROQ_MODEL,
        temperature=0.1,
    )
    sys_prompt = "You are a Document Pre-Validation AI. Check for missing mandatory fields, signatures, or engineer seals. Output Pass/Fail and fix recommendations."

    response = text_llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=req.document_text),
    ])
    return {"validation_report": response.content}

# ==========================================
# Add these definitions to your existing data models block in main.py
# ==========================================

class CoordinateInputRequest(BaseModel):
    latitude: float
    longitude: float

from typing import Optional
class OfficeLookupRequest(BaseModel):
    latitude: float
    longitude: float
    approval_id: str
    authority: str
    project_location_text: str = ""
    force_project_location: bool = False

# ==========================================
# Add this endpoint route block to main.py
# ==========================================

@app.post("/api/v1/geospatial/check")
async def check_geospatial_compliance(req: CoordinateInputRequest):
    global geospatial_data_holder

    if not (-90.0 <= req.latitude <= 90.0) or not (-180.0 <= req.longitude <= 180.0):
        raise HTTPException(
            status_code=400, 
            detail="Invalid geospatial coordinate ranges provided."
        )

    try:
        from bhuvan_checker import prepare_eia_payload
        
        lat_val = float(req.latitude)
        lon_val = float(req.longitude)
        
        # 1. Fetch live ISRO Bhuvan OGC findings
        spatial_payload = prepare_eia_payload(lat_val, lon_val)
        
        # 2. Store findings in global backend holder
        detected_names = [layer["display_name"] for layer in spatial_payload["regulatory_layers"] if layer.get("found")]
        geospatial_data_holder = f"Regulatory layers: {', '.join(detected_names) if detected_names else 'None'} were found when performed geospatial analysis"
        
        print("[+] Updated geospatial_data_holder with live Bhuvan findings.")
        return spatial_payload

    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="Spatial utility module 'bhuvan_checker.py' is missing."
        )
    except Exception as server_error:
        raise HTTPException(
            status_code=500, 
            detail=f"Geospatial Processing Engine Failure: {str(server_error)}"
        )


@app.post("/api/v1/geospatial/office")
async def resolve_office_location(req: OfficeLookupRequest):
    import httpx
    from agents.resolver import normalize_district, resolve_regional_office

    project_district = normalize_district(req.project_location_text) if req.project_location_text else ""
    user_district = ""
    
    if req.latitude and req.longitude:
        # Nominatim lookup with proper User-Agent
        url = f"https://nominatim.openstreetmap.org/reverse?lat={req.latitude}&lon={req.longitude}&format=json"
        headers = {"User-Agent": "UdyogPermitAI/1.0 (contact@udyogpermit.ai)"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    addr = resp.json().get("address", {})
                    # Prioritized fallback for administrative district fields
                    for key in ["district", "county", "state_district", "city", "town", "municipality"]:
                        val = addr.get(key)
                        if val:
                            user_district = normalize_district(val)
                            if user_district:
                                break
        except Exception as e:
            print(f"[Geospatial] Reverse geocode failed: {e}")
            pass
            
    # Compare project and user districts
    if user_district and project_district and user_district != project_district and not req.force_project_location:
        return {
            "status": "mismatch",
            "project_district": project_district,
            "user_district": user_district
        }
        
    target_district = project_district or user_district or "Maharashtra"
    
    # Resolve regional office based on the target district
    office = resolve_regional_office(req.authority, target_district)
    
    return {
        "status": "success",
        "target_district": target_district,
        "office": office,
        "source": "Nominatim OSM + UdyogPermit Registry"
    }


# ==========================================
# Unified React Static Serving
# ==========================================

dist_path = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(dist_path):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(dist_path, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        return FileResponse(os.path.join(dist_path, "index.html"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)