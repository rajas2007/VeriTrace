"""Agent 1: Industrial facility profiler.

This module also holds the clarifying-questions extension to Agent 1:
enrichment (Step 3), completeness gate (Step 4), question generation
(Step 5), and answer merging (Step 6). Agent 1's original extraction call
(agent_1_profiler) is unchanged and still runs first, unmodified.
"""

import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from .schemas import (
    compute_missing_fields,
    get_nested_field,
    set_nested_field,
)

RISK_TIER_QUESTION_CAPS = {"White": 3, "Green": 5, "Orange": 8, "Red": 20}
DEFAULT_QUESTION_CAP = 8
MAX_CLARIFICATION_ROUNDS = 2


def agent_1_profiler(state: dict, llm: ChatGroq) -> dict:
    """Extract structured facility parameters and incorporate live Bhuvan OGC spatial summary text."""
    
    # Retrieves the formatted string summary from state
    geospatial_summary = state.get("geospatial_data", "No spatial analysis performed.")
    
    sys_prompt = f"""You are an Industrial Profiling AI. Extract facility parameters into a strict JSON structure.
Use the provided raw input text AND live Bhuvan Geospatial Findings to populate the profile accurately.

Live Bhuvan Spatial Findings:
{geospatial_summary}

Output schema: 
{{
  "facility_type": "", 
  "location": {{
    "midc_zone": "", 
    "eco_sensitivity": "",
    "detected_land_use": ""
  }}, 
  "inputs": [], 
  "outputs": [], 
  "emissions": []
}}
Note: Under 'eco_sensitivity' and 'detected_land_use', reference any detected constraints or land cover categories mentioned in the Bhuvan spatial findings summary.
"""

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["raw_input"]),
    ])
    
    state["profile"] = json.loads(response.content)
    return state


# ==========================================
# Step 3 — Enrichment (LLM, no user input needed)
# ==========================================

def agent_1_enrichment(state: dict, llm: ChatGroq) -> dict:
    """Fill in generic industry knowledge the model already knows from facility_type alone.

    Never asks the user anything here — only well-known, generic facts
    (typical raw materials/byproducts/manpower, CPCB pollution category).
    This is what keeps those facts from ever becoming clarifying questions.
    """
    profile = state.get("profile", {}) or {}
    sys_prompt = """You are an Industrial Domain Knowledge AI.
Given only a facility_type, fill in GENERIC, well-known industry facts that do not depend on
facility-specific details the user hasn't provided. Do not invent facility-specific numbers.
Output strict JSON: {"typical_raw_materials": [], "typical_byproducts": [], "typical_manpower_range": "", "pollution_category": "Red|Orange|Green|White"}
Base pollution_category strictly on CPCB (Central Pollution Control Board) classification norms for this type of industry."""

    try:
        response = llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=json.dumps({"facility_type": profile.get("facility_type", "")})),
        ])
        enrichment = json.loads(response.content)
    except (json.JSONDecodeError, ValueError):
        enrichment = {}

    state["pollution_category"] = enrichment.get("pollution_category") or "Orange"
    state["profile"] = {
        **profile,
        "typical_raw_materials": enrichment.get("typical_raw_materials", []),
        "typical_byproducts": enrichment.get("typical_byproducts", []),
        "typical_manpower_range": enrichment.get("typical_manpower_range", ""),
    }
    return state


# ==========================================
# Step 4 — Completeness gate (deterministic, no LLM)
# ==========================================

def agent_1_completeness_gate(state: dict) -> dict:
    """Deterministic Pydantic check against the category-specific required fields."""
    category = state.get("category", "generic_manufacturing")
    profile = state.get("profile", {}) or {}
    round_count = state.get("clarification_round", 0)

    missing = compute_missing_fields(category, profile)

    if not missing:
        state["profile_status"] = "complete"
        state["missing_fields"] = []
    elif round_count >= MAX_CLARIFICATION_ROUNDS:
        # Loop guard: never let the user get stuck looping. Force completion,
        # flag which fields fell back to whatever value they currently hold
        # (None if never answered), and hand off to Agent 2 regardless.
        defaulted = state.get("defaulted_fields", [])
        for item in missing:
            if item["field"] not in defaulted:
                defaulted.append(item["field"])
        state["defaulted_fields"] = defaulted
        state["profile_status"] = "complete"
        state["missing_fields"] = []
    else:
        state["profile_status"] = "needs_clarification"
        state["missing_fields"] = missing

    return state


# ==========================================
# Step 5 — Question generation (LLM, only runs on gaps)
# ==========================================

def _confirm_fallback_field(profile: Dict[str, Any]) -> Dict[str, Any]:
    """When nothing is missing but the risk tier still wants >=1 question,
    ask the user to confirm an already-filled field instead of fabricating
    a question from nothing."""
    for path in ("facility_type", "location.midc_zone", "inputs"):
        value = get_nested_field(profile, path)
        if value:
            return {"field": path, "impact": "low", "input_type": "text", "options": None, "default": value}
    return {
        "field": "facility_type",
        "impact": "low",
        "input_type": "text",
        "options": None,
        "default": profile.get("facility_type", ""),
    }


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _parse_questions_response(raw_content: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Defensive parse: strip markdown fences, validate shape, else raise for the caller to retry."""
    cleaned = _strip_json_fences(raw_content)
    parsed = json.loads(cleaned)
    questions = parsed.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("malformed questions payload")

    by_field = {c["field"]: c for c in candidates}
    result = []
    for q in questions:
        field = q.get("field")
        candidate = by_field.get(field)
        if not candidate:
            continue
        result.append({
            "field": field,
            "question": q.get("question") or f"Please provide a value for {field}.",
            "input_type": candidate["input_type"],
            "options": candidate["options"],
            "impact": candidate["impact"],
            "default": q.get("default", candidate.get("default")),
        })
    if not result:
        raise ValueError("no questions matched known candidate fields")
    return result


def _fallback_questions(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Last-resort, fully deterministic question set if the LLM call/parse fails twice."""
    return [
        {
            "field": c["field"],
            "question": f"Could you provide a value for '{c['field']}'?",
            "input_type": c["input_type"],
            "options": c["options"],
            "impact": c["impact"],
            "default": c.get("default"),
        }
        for c in candidates
    ]


def agent_1_generate_questions(state: dict, llm: ChatGroq) -> dict:
    """Phrase gaps as typed, answerable questions. Capped by risk tier, min 1 always."""
    missing = state.get("missing_fields", []) or []
    pollution_category = state.get("pollution_category", "Orange")
    cap = RISK_TIER_QUESTION_CAPS.get(pollution_category, DEFAULT_QUESTION_CAP)

    candidates = missing[:cap]
    if not candidates:
        candidates = [_confirm_fallback_field(state.get("profile", {}))]

    sys_prompt = """You are an Intake Question Writer for an industrial permitting assistant.
Given a list of missing/to-confirm fields (each with "field", "impact", "input_type", "options"),
write a short, plain-language question a facility owner could answer for each, plus a sensible
"default" value to use if they skip it.
Output strict JSON only, no markdown fences, no preamble:
{"questions": [{"field": "", "question": "", "default": ""}]}
Keep "field" values EXACTLY as given. Do not add fields that were not given to you."""

    payload = json.dumps({"fields": candidates})
    questions = None
    last_error = None
    for _attempt in range(2):
        try:
            response = llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=payload),
            ])
            questions = _parse_questions_response(response.content, candidates)
            break
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            last_error = exc
            continue

    if questions is None:
        questions = _fallback_questions(candidates)

    state["clarification_questions"] = questions
    state["clarification_round"] = state.get("clarification_round", 0) + 1
    return state


# ==========================================
# Step 6 — Merge answers back into the profile
# ==========================================

def agent_1_merge_clarification_answers(state: dict) -> dict:
    """Merge user-submitted (or skipped-with-default) answers into the profile,
    then clear the pending answers so the next completeness_gate pass re-checks
    against the merged profile."""
    profile = state.get("profile", {}) or {}
    answers = state.get("clarification_answers", {}) or {}
    defaulted = list(state.get("defaulted_fields", []))

    for field, payload in answers.items():
        if payload.get("skipped"):
            question = next((q for q in state.get("clarification_questions", []) if q["field"] == field), None)
            value = question.get("default") if question else None
            if field not in defaulted:
                defaulted.append(field)
        else:
            value = payload.get("answer")
        set_nested_field(profile, field, value)

    state["profile"] = profile
    state["defaulted_fields"] = defaulted
    state["clarification_answers"] = {}
    return state