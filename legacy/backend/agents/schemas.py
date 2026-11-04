"""Category-specific facility profile schemas for the clarifying-questions extension.

These are deterministic, LLM-free Pydantic models used by the completeness gate
(Step 4) to decide which required fields are still missing after extraction +
enrichment. Each field carries an "impact" tier (high/medium/low) and an
"input_type" hint so the question-generation step (Step 5) and the frontend
question form can render the right widget without guessing.

New industries are added by defining a new BaseFacilityProfile subclass and
registering it in CATEGORY_SCHEMA_MAP. Anything not registered falls back to
the generic FacilityProfile (5-field schema), per the "known gaps" note in the
design doc: dedicated schemas are authored one industry at a time.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

# ==========================================
# Nested-path helpers
# ==========================================
# Agent 1's extracted profile keeps location fields nested
# (profile["location"]["midc_zone"]), but Pydantic model fields are flat.
# These helpers translate between the two so schemas stay simple.

_NESTED_LOCATION_FIELDS = {"midc_zone", "eco_sensitivity"}


def flatten_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten profile['location'][...] into top-level keys for schema validation."""
    flat = dict(profile or {})
    location = flat.pop("location", None) or {}
    flat["midc_zone"] = location.get("midc_zone")
    flat["eco_sensitivity"] = location.get("eco_sensitivity")
    return flat


def field_name_to_path(name: str) -> str:
    """Map a flat schema field name back to its dotted path in the real profile dict."""
    if name in _NESTED_LOCATION_FIELDS:
        return f"location.{name}"
    return name


def get_nested_field(profile: Dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    node: Any = profile or {}
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def set_nested_field(profile: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    node = profile
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


# ==========================================
# Category schemas
# ==========================================


class BaseFacilityProfile(BaseModel):
    """Fields common to every category. Every category schema extends this."""

    facility_type: Optional[str] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "text"}
    )
    midc_zone: Optional[str] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )
    eco_sensitivity: Optional[str] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "text"}
    )
    inputs: Optional[List[str]] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )
    outputs: Optional[List[str]] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "text"}
    )
    emissions: Optional[List[str]] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )

    model_config = {"extra": "allow"}


class FacilityProfile(BaseFacilityProfile):
    """Generic fallback schema (~5 fields) for any category without a dedicated schema."""


class BatteryPackFacilityProfile(BaseFacilityProfile):
    """Hazard/storage-critical schema for li-ion battery pack assembly facilities."""

    max_stored_energy_kwh: Optional[float] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "number"}
    )
    cell_chemistry: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "high",
            "input_type": "single_select",
            "options": ["LFP", "NMC", "NCA", "Other"],
        },
    )
    storage_type: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "high",
            "input_type": "single_select",
            "options": ["Indoor", "Outdoor", "Both"],
        },
    )
    fire_suppression_system: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    hazardous_waste_generated: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class FoodProcessingProfile(BaseFacilityProfile):
    """Schema for food/beverage processing units (typically Orange/Green CPCB category)."""

    product_type: Optional[str] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )
    effluent_treatment_plant: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    water_source: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "medium",
            "input_type": "single_select",
            "options": ["Municipal", "Borewell", "Tanker", "Other"],
        },
    )
    cold_storage_required: Optional[bool] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "boolean"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class PotteryFacilityProfile(BaseFacilityProfile):
    """Small, low-field-count schema for pottery/ceramics units (typically Green/White)."""

    kiln_fuel_type: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "high",
            "input_type": "single_select",
            "options": ["Electric", "LPG", "Coal", "Wood"],
        },
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class ChemicalManufacturingProfile(BaseFacilityProfile):
    """Hazard-critical schema for chemical/pharma manufacturing and processing units (typically Red)."""

    hazardous_chemicals_handled: Optional[List[str]] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "text"}
    )
    storage_capacity_kl: Optional[float] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "number"}
    )
    effluent_treatment_plant: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    fire_safety_noc: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    hazardous_waste_generated: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    gmp_certification_required: Optional[bool] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "boolean"}
    )
    cold_chain_required: Optional[bool] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "boolean"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class TextileDyeingProfile(BaseFacilityProfile):
    """Effluent-heavy schema for textile/dyeing units (typically Orange/Red)."""

    dye_type: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "medium",
            "input_type": "single_select",
            "options": ["Reactive", "Azo", "Vat", "Other"],
        },
    )
    effluent_treatment_plant: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    zld_compliance: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    water_consumption_kl_per_day: Optional[float] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "number"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class FoundryMetalCastingProfile(BaseFacilityProfile):
    """Distinct-emissions schema for foundry/metal casting units (typically Red)."""

    furnace_type: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "high",
            "input_type": "single_select",
            "options": ["Induction", "Cupola", "Electric Arc", "Other"],
        },
    )
    metal_type: Optional[str] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )
    dust_collection_system: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    hazardous_waste_generated: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


class PlasticsRubberProcessingProfile(BaseFacilityProfile):
    """Schema for plastics/rubber processing units (typically Orange)."""

    process_type: Optional[str] = Field(
        None,
        json_schema_extra={
            "impact": "medium",
            "input_type": "single_select",
            "options": ["Injection Molding", "Extrusion", "Vulcanization", "Other"],
        },
    )
    raw_material_type: Optional[str] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "text"}
    )
    emission_control_system: Optional[bool] = Field(
        None, json_schema_extra={"impact": "high", "input_type": "boolean"}
    )
    hazardous_waste_generated: Optional[bool] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "boolean"}
    )
    manpower_count: Optional[int] = Field(
        None, json_schema_extra={"impact": "medium", "input_type": "number"}
    )
    fci_inr_crore: Optional[float] = Field(
        None, json_schema_extra={"impact": "low", "input_type": "number"}
    )


CATEGORY_SCHEMA_MAP: Dict[str, type[BaseFacilityProfile]] = {
    "li_ion_battery_pack_assembly": BatteryPackFacilityProfile,
    "food_processing": FoodProcessingProfile,
    "pottery": PotteryFacilityProfile,
    "chemicals": ChemicalManufacturingProfile,
    "textile_dyeing": TextileDyeingProfile,
    "foundry_metal_casting": FoundryMetalCastingProfile,
    "plastics_rubber_processing": PlasticsRubberProcessingProfile,
    "generic_manufacturing": FacilityProfile,
}


def get_schema_for_category(category: str) -> type[BaseFacilityProfile]:
    return CATEGORY_SCHEMA_MAP.get(category, FacilityProfile)


def compute_missing_fields(category: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic completeness check (Step 4). No LLM involved.

    Returns a list of {"field", "impact", "input_type", "options"} dicts for
    every schema field that is still null/empty, ordered high -> medium -> low
    impact so callers can cap by risk tier without re-sorting.
    """
    schema_cls = get_schema_for_category(category)
    flat = flatten_profile(profile)
    known = {k: v for k, v in flat.items() if k in schema_cls.model_fields}

    try:
        instance = schema_cls(**known)
    except ValidationError as exc:
        # A previously-merged answer/default doesn't match the field's type
        # (e.g. a non-numeric default landed in a numeric field). Rather than
        # crash the whole request, drop only the offending fields — they'll
        # show back up as "missing" and get re-asked with a clean prompt.
        bad_fields = {err["loc"][0] for err in exc.errors() if err.get("loc")}
        known_clean = {k: v for k, v in known.items() if k not in bad_fields}
        instance = schema_cls(**known_clean)

    missing: List[Dict[str, Any]] = []
    for name, field in schema_cls.model_fields.items():
        value = getattr(instance, name)
        if value in (None, "", []):
            extra = field.json_schema_extra or {}
            missing.append(
                {
                    "field": field_name_to_path(name),
                    "impact": extra.get("impact", "medium"),
                    "input_type": extra.get("input_type", "text"),
                    "options": extra.get("options"),
                }
            )

    impact_rank = {"high": 0, "medium": 1, "low": 2}
    missing.sort(key=lambda m: impact_rank.get(m["impact"], 1))
    return missing