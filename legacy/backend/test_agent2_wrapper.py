from main import llm
from langchain_groq import ChatGroq
import copy
import json
from langchain_core.messages import HumanMessage, SystemMessage

# We override the model_kwargs to test without json mode
llm_no_json = ChatGroq(
    api_key=llm.groq_api_key.get_secret_value(),
    model=llm.model_name,
    temperature=0.1
)

state = {
    'profile': {'facility_type': 'A small manufacturing unit producing packaged food products in Pune.'},
    'geospatial_data': 'No spatial analysis performed.'
}
sys_prompt = f"""You are a Maharashtra Regulatory Expert. Analyze the facility profile along with live ISRO Bhuvan geospatial findings.

Facility Profile:
{json.dumps(state['profile'], indent=2)}

Live Spatial Findings:
{state['geospatial_data']}

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

resp = llm_no_json.invoke([
    SystemMessage(content=sys_prompt),
    HumanMessage(content=f"Generate compliance and incentive mapping for: {state['profile'].get('facility_type', 'Industrial Facility')}")
])
print("====RAW====")
print(resp.content)
