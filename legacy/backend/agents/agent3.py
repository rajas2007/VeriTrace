"""Agent 3: Compliance and incentive route planner."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq


def agent_3_planner(state: dict, llm: ChatGroq) -> dict:
    """Create a chronological roadmap and identify tasks that can run in parallel."""
    print(f"DEBUG AGENT 3 STATE: {state}")
    sys_prompt = "You are a Workflow Planner. Create a strict chronological text roadmap from the provided compliances and selected subsidies. Group parallel tasks."

    compliances = state.get("compliances", [])
    selected_subsidies = state.get("selected_subsidies", [])

    input_content = (
        f"Compliances: {compliances}\n"
        f"Selected Subsidies: {selected_subsidies}"
    )
    try:
        response = llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=input_content),
        ])
        state["roadmap"] = response.content
    except Exception:
        # Fallback text roadmap in case LLM rate-limits or fails
        fallback_lines = ["# Industrial Compliance & Subsidy Execution Roadmap\n"]
        fallback_lines.append("## Phase 1: Statutory Approvals & Mandatory Clearances")
        for idx, comp in enumerate(compliances, 1):
            name = comp.get("name", f"Approval {idx}")
            auth = comp.get("authority", "Statutory Authority")
            fallback_lines.append(f"{idx}. **{name}** - Authority: {auth}")
        if selected_subsidies:
            fallback_lines.append("\n## Phase 2: Incentive & Subsidy Applications")
            for idx, sub in enumerate(selected_subsidies, 1):
                name = sub.get("name", "Subsidy Scheme")
                fallback_lines.append(f"{idx}. **{name}** - Application & Verification")
        state["roadmap"] = "\n".join(fallback_lines)

    return state
