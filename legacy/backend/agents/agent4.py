"""Agent 4: UI visualization structurer and branched flowchart generator.
Transforms Agent 3's dependency roadmap and structured compliances into
a multi-stage, branched DAG with parallel execution tracks and clean prerequisite links.
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq

from agents.resolver import resolve_approval_metadata


class ApprovalSource(BaseModel):
    url: str
    verified: bool = True
    label: str = "Official Link"


class ApprovalNodeData(BaseModel):
    id: str
    label: str
    authority: str
    department: Optional[str] = None
    category: str = "general"
    status: str = "required"
    mandatory: bool = True
    estimated_duration_days: int = 30
    why_required: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)
    sources: Dict[str, ApprovalSource] = Field(default_factory=dict)
    verification: Dict[str, str] = Field(default_factory=dict)
    is_parallel: bool = False
    next_steps: List[str] = Field(default_factory=list)
    physical_office: Optional[Dict[str, Any]] = None


class WorkflowNode(BaseModel):
    id: str
    type: str = "approvalNode"
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    data: ApprovalNodeData


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False
    type: str = "smoothstep"
    label: Optional[str] = None
    style: Dict[str, Any] = Field(default_factory=lambda: {"stroke": "#2563eb", "strokeWidth": 2.5})


class WorkflowSummary(BaseModel):
    total_approvals: int = 0
    mandatory_count: int = 0
    optional_count: int = 0
    parallel_tracks_count: int = 0
    critical_path_days: int = 0
    factory_name: str = "Industrial Facility"
    location: str = "Maharashtra"


class VisualizationPayload(BaseModel):
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    approvals_map: Dict[str, ApprovalNodeData]
    summary: WorkflowSummary
    raw_roadmap_text: str = ""


def build_deterministic_stages(compliances: list, selected_subsidies: list):
    """
    Groups compliances and subsidies into chronological parallel stages:
    Stage 1: Initial Statutory & Pre-requisite Clearances (Parallel tracks)
    Stage 2: Sector-Specific Clearances & Labor Compliance (Parallel tracks)
    Stage 3: Operational Clearances & State Subsidies / Incentives (Parallel tracks)
    """
    stage1 = []
    stage2 = []
    stage3 = []

    for idx, comp in enumerate(compliances):
        c_name = comp.get("name", f"Approval {idx+1}")
        c_auth = comp.get("authority", "Statutory Authority")
        c_lower = c_name.lower()
        c_id = f"app_{idx+1}"

        item = {
            "id": c_id,
            "name": c_name,
            "authority": c_auth,
            "category": "statutory",
            "mandatory": True,
            "estimated_duration_days": 30,
            "is_parallel": False,
        }

        # Stage 2: Sector-specific licenses and worker/labor compliance
        is_stage2 = any(k in c_lower for k in [
            "fssai", "food", "drug", "cdsco", "fda", "pharma", "cosmetic",
            "labor", "labour", "welfare", "esic", "epf", "epfo", "wage", "boiler",
            "explosive", "peso", "excise", "mining"
        ])
        
        # Stage 3: Operational clearances (CTO, final occupancy)
        is_stage3 = any(k in c_lower for k in [
            "consent to operate", "occupancy", "final fire"
        ]) or bool(re.search(r"\bcto\b", c_lower))

        if is_stage2:
            stage2.append(item)
        elif is_stage3:
            stage3.append(item)
        else:
            stage1.append(item)

    # Subsidies & Schemes are part of Stage 3 (Parallel milestone alongside operations)
    for s_idx, sub in enumerate(selected_subsidies):
        s_name = sub.get("name", f"Incentive Scheme {s_idx+1}")
        sub_id = f"sub_{s_idx+1}"
        stage3.append({
            "id": sub_id,
            "name": s_name,
            "authority": "Directorate of Industries, Maharashtra",
            "category": "incentive",
            "mandatory": False,
            "estimated_duration_days": 30,
            "is_parallel": True,
        })

    # Balance stages if any stage is empty but others have items
    if not stage1 and stage2:
        stage1.append(stage2.pop(0))
    if not stage2 and len(stage1) > 2:
        stage2 = [stage1.pop()]
    if not stage3 and len(stage2) > 2:
        stage3 = [stage2.pop()]

    # Mark parallel tracks for UI badges
    if len(stage1) > 1:
        for n in stage1:
            n["is_parallel"] = True
    if len(stage2) > 1:
        for n in stage2:
            n["is_parallel"] = True
    if len(stage3) > 1:
        for n in stage3:
            n["is_parallel"] = True

    raw_nodes = stage1 + stage2 + stage3
    raw_edges = []

    def connect_stages(source_stage, target_stage):
        if not source_stage or not target_stage:
            return

        # Find primary anchor in source stage (CTE, Environmental, or first node)
        anchor = source_stage[0]
        for n in source_stage:
            nl = n["name"].lower()
            if any(k in nl for k in ["consent to establish", "cte", "environment", "cdsco", "fssai"]):
                anchor = n
                break

        # 1. Distribute source nodes across target nodes
        for i, s_node in enumerate(source_stage):
            target_idx = min(len(target_stage) - 1, (i * len(target_stage)) // len(source_stage))
            t_node = target_stage[target_idx]
            raw_edges.append({"from": s_node["id"], "to": t_node["id"]})

        # 2. Anchor node fans out to all target nodes
        for t_node in target_stage:
            edge = {"from": anchor["id"], "to": t_node["id"]}
            if edge not in raw_edges:
                raw_edges.append(edge)

        # 3. Ensure every target node has at least one incoming edge
        covered_targets = {e["to"] for e in raw_edges}
        for t_node in target_stage:
            if t_node["id"] not in covered_targets:
                raw_edges.append({"from": source_stage[-1]["id"], "to": t_node["id"]})

    # Connect Stage 1 -> Stage 2, and Stage 2 -> Stage 3
    if stage1 and stage2:
        connect_stages(stage1, stage2)
        if stage3:
            connect_stages(stage2, stage3)
    elif stage1 and stage3:
        connect_stages(stage1, stage3)
    elif stage2 and stage3:
        connect_stages(stage2, stage3)

    return raw_nodes, raw_edges


def agent_4_visualizer(state: dict, llm: ChatGroq) -> dict:
    """
    Extracts direct sequential and parallel dependency tracks from the roadmap.
    Enforces clean branched connections with parallel tracks without collapsing into a straight line.
    """
    compliances = state.get("compliances", [])
    selected_subsidies = state.get("selected_subsidies", [])
    profile = state.get("profile", {})
    roadmap_text = state.get("roadmap", "")

    raw_nodes, raw_edges = build_deterministic_stages(compliances, selected_subsidies)

    approval_nodes: List[WorkflowNode] = []
    approvals_map: Dict[str, ApprovalNodeData] = {}
    workflow_edges: List[WorkflowEdge] = []
    
    # Calculate blocking relationships (reverse dependencies) with human-readable labels
    node_name_by_id = {str(n.get("id")): n.get("name", "Approval") for n in raw_nodes}
    blocks_map: Dict[str, List[str]] = {}
    deps_map: Dict[str, List[str]] = {}
    for edge in raw_edges:
        src = edge.get("from")
        tgt = edge.get("to")
        if src and tgt:
            src_name = node_name_by_id.get(src, src)
            tgt_name = node_name_by_id.get(tgt, tgt)
            blocks_map.setdefault(src, []).append(tgt_name)
            deps_map.setdefault(tgt, []).append(src_name)

    for n in raw_nodes:
        node_id = str(n.get("id"))
        node_name = n.get("name", "Approval")
        node_auth = n.get("authority", "")
        
        resolved = resolve_approval_metadata(node_name, authority_hint=node_auth)

        typed_sources = {}
        for s_key, s_val in resolved.get("sources", {}).items():
            typed_sources[s_key] = ApprovalSource(
                url=s_val.get("url", "#"),
                verified=s_val.get("verified", True),
                label=s_val.get("label", "Official Link")
            )

        duration = n.get("estimated_duration_days") or resolved.get("estimated_duration_days", 30)

        node_data = ApprovalNodeData(
            id=node_id,
            label=node_name,
            authority=resolved.get("authority") or node_auth or "Govt of Maharashtra",
            department=resolved.get("department", "State Department"),
            category=resolved.get("category") or n.get("category", "general"),
            status="required",
            mandatory=n.get("mandatory", True),
            estimated_duration_days=duration,
            why_required=resolved.get("why_required"),
            dependencies=deps_map.get(node_id, []),
            blocks=blocks_map.get(node_id, []),
            documents=resolved.get("documents", []),
            sources=typed_sources,
            verification=resolved.get("verification", {}),
            is_parallel=n.get("is_parallel", False),
            next_steps=resolved.get("next_steps", []),
            physical_office=resolved.get("physical_office")
        )

        approvals_map[node_id] = node_data
        approval_nodes.append(WorkflowNode(
            id=node_id,
            type="approvalNode",
            position={"x": 0.0, "y": 0.0},
            data=node_data
        ))

    # Build clean edges without redundant loops
    edge_idx = 0
    seen_pairs = set()
    for edge in raw_edges:
        src = edge.get("from")
        tgt = edge.get("to")
        if src and tgt and src in approvals_map and tgt in approvals_map and (src, tgt) not in seen_pairs and src != tgt:
            seen_pairs.add((src, tgt))
            workflow_edges.append(WorkflowEdge(
                id=f"e-{src}-{tgt}-{edge_idx}",
                source=src,
                target=tgt,
                animated=False,
                type="smoothstep",
                label=None,
                style={"stroke": "#2563eb", "strokeWidth": 2.5}
            ))
            edge_idx += 1

    # Compute high-level summary statistics
    fac_name = profile.get("facility_type") or "Industrial Project"
    loc_info = profile.get("location", {})
    if isinstance(loc_info, dict):
        loc_str = loc_info.get("midc_zone") or "Maharashtra Industrial Belt"
    else:
        loc_str = str(loc_info) or "Maharashtra"

    total_duration = sum(n.data.estimated_duration_days for n in approval_nodes if not n.data.is_parallel)
    if total_duration == 0:
        total_duration = 60

    parallel_count = sum(1 for n in approval_nodes if n.data.is_parallel)

    summary = WorkflowSummary(
        total_approvals=len(approval_nodes),
        mandatory_count=sum(1 for n in approval_nodes if n.data.mandatory),
        optional_count=sum(1 for n in approval_nodes if not n.data.mandatory),
        parallel_tracks_count=parallel_count,
        critical_path_days=total_duration,
        factory_name=fac_name,
        location=loc_str
    )

    payload = VisualizationPayload(
        nodes=approval_nodes,
        edges=workflow_edges,
        approvals_map=approvals_map,
        summary=summary,
        raw_roadmap_text=roadmap_text
    )

    state["ui_data"] = payload.model_dump()
    return state
