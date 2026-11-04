from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
class SiteCoordinates(BaseModel):
    latitude: float
    longitude: float
class GeoFinding(BaseModel):
    type: str
    name: Optional[str] = None
    distance_m: Optional[float] = None
    geometry_type: Optional[str] = None
    source: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    regulatory_relevance: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
class GeospatialAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    radius_m: int = Field(default=3000, ge=100, le=10000)
class GeospatialData(BaseModel):
    site: SiteCoordinates
    analysis_radius_m: int
    findings: List[GeoFinding] = Field(default_factory=list)
    geojson: Dict[str, Any] = Field(default_factory=dict)
    sources: List[str] = Field(default_factory=list)
    analysis_status: str = 'completed'
