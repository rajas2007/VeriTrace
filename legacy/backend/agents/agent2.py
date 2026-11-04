"""Agent 2: Maharashtra regulatory and incentives analyst."""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq


import re

def _strip_json_fences(text: str) -> str:
    # Remove <think> blocks if any
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    # Extract from first { to last }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        return text[start:end+1]
    return text

def agent_2_regulatory(state: dict, llm: ChatGroq) -> dict:
    """Map facility profile and live spatial constraint summary to mandatory compliances and eligible subsidies."""
    
    profile = state.get("profile", {})
    geospatial_summary = state.get("geospatial_data", "No spatial analysis performed.")

    sys_prompt = f"""You are a Maharashtra Regulatory Expert. Analyze the facility profile along with live ISRO Bhuvan geospatial findings.

Facility Profile:
{json.dumps(profile, indent=2)}

Live Spatial Findings:
{geospatial_summary}

Task:
1. Determine mandatory environmental, industrial, and safety clearances (e.g., MPCB Consent to Establish, Factory License, CPCB ZLD compliance).
2. If any eco-sensitive constraints (CRZ, ESZ, ASI, or specific land-use restrictions) are mentioned in the spatial findings summary or profile, add specific mandatory clearances required for those zones (e.g., Coastal Zone Management Authority NOC, NMA Clearance).
3. Identify eligible Maharashtra industrial schemes and subsidies (e.g., PSI Scheme, Power Tariff Subsidy, ZLD Capital Subsidy).

Output strict JSON schema:
{{
  "mandatory_compliances": [
    {{"name": "", "authority": "", "head": ""}}
  ], 
  "eligible_subsidies": [
    {{"name": "", "description": ""}}
  ]
}}
"""

    # Re-instantiate ChatGroq without model_kwargs={"response_format": {"type": "json_object"}}
    # to avoid 400 Bad Request if the model outputs markdown fences.
    # We add max_tokens to prevent the output from truncating if the model reasons in <think> tags.
    safe_llm = ChatGroq(
        api_key=llm.groq_api_key.get_secret_value() if hasattr(llm, "groq_api_key") else None,
        model=llm.model_name,
        temperature=llm.temperature,
        max_tokens=8192
    )

    result = {"mandatory_compliances": [], "eligible_subsidies": []}
    
    for attempt in range(3):
        try:
            response = safe_llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"Generate compliance and incentive mapping for: {profile.get('facility_type', 'Industrial Facility')}"),
            ])
            cleaned = _strip_json_fences(response.content)
            result = json.loads(cleaned)
            break
        except Exception as e:
            print(f"AGENT 2 Exception on attempt {attempt}: {e}")
            try:
                print(f"RAW MESSAGE: {response.model_dump()}")
            except:
                pass
            continue

    state["compliances"] = result.get("mandatory_compliances", [])
    state["eligible_subsidies"] = result.get("eligible_subsidies", [])
    print(f"DEBUG AGENT 2 RETURN: compliances={state['compliances']}, subsidies={state['eligible_subsidies']}")
    return state