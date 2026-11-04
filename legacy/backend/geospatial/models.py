from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GeospatialRequest(BaseModel):
    latitude: float
    longitude: float

    radius_m: float = Field(default=3000, gt=0, le=50000)

    categories: Optional[List[str]] = None


class GeospatialFinding(BaseModel):
    type: str
    name: Optional[str] = None
    distance_m: Optional[float] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeospatialResult(BaseModel):
    site: Dict[str, float]
    analysis_radius_m: float
    findings: List[GeospatialFinding] = Field(default_factory=list)
    geojson: Dict[str, Any] = Field(default_factory=dict)