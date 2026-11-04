"""Step 2 — category classification.

Deterministic keyword lookup mapping a facility_type string to a known
category key. Falls back to "generic_manufacturing" when no dedicated
schema/keyword set exists yet.

Kept as a plain dict lookup for now per the design doc; can be upgraded to an
LLM classification call later if raw inputs get messier.
"""

from typing import Dict, List

GENERIC_CATEGORY = "generic_manufacturing"

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "li_ion_battery_pack_assembly": [
        "lithium",
        "li-ion",
        "li ion",
        "battery",
        "battery pack",
        "cell assembly",
        "bess",
    ],
    "food_processing": [
        "food processing",
        "food unit",
        "snack",
        "bakery",
        "dairy",
        "beverage",
        "frying",
        "confectionery",
        "namkeen",
    ],
    "pottery": [
        "pottery",
        "ceramic",
        "kiln",
        "terracotta",
        "clay",
        "earthenware",
    ],
    "chemicals": [
        "chemical",
        "solvent",
        "acid",
        "dye manufacturing",
        "paint",
        "pesticide",
        "petrochemical",
        "resin",
        "pharma",
        "pharmaceutical",
        "api manufacturing",
        "bulk drug",
        "formulation unit",
    ],
    "textile_dyeing": [
        "textile",
        "dyeing",
        "dye house",
        "fabric",
        "yarn",
        "garment processing",
        "printing and dyeing",
    ],
    "foundry_metal_casting": [
        "foundry",
        "metal casting",
        "casting unit",
        "cupola",
        "induction furnace",
        "forging",
    ],
    "plastics_rubber_processing": [
        "plastic",
        "rubber",
        "injection molding",
        "injection moulding",
        "extrusion",
        "vulcanization",
        "vulcanisation",
        "pvc",
    ],
}


def classify_category(facility_type: str) -> str:
    ft = (facility_type or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in ft for keyword in keywords):
            return category
    return GENERIC_CATEGORY