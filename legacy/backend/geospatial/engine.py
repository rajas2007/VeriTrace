from .config import DEFAULT_RADIUS_M
from .geometry import create_buffer, geometry_to_geojson
from .schemas import GeospatialData, SiteCoordinates, GeoFinding
from .sources import get_providers
class GeospatialEngine:
    def __init__(self): self.providers=get_providers()
    def analyze(self,latitude,longitude,radius_m=DEFAULT_RADIUS_M):
        findings=[]; sources=[]
        for p in self.providers:
            try:
                findings.extend(p.normalize(p.query(latitude,longitude,radius_m),latitude,longitude)); sources.append(p.__class__.__name__)
            except Exception as exc: print(f'Geospatial provider failed: {p.__class__.__name__}: {exc}')
        findings=self._deduplicate(findings); polygon=create_buffer(latitude,longitude,radius_m)
        geojson={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'type':'analysis_boundary','radius_m':radius_m},'geometry':geometry_to_geojson(polygon)}]}
        return GeospatialData(site=SiteCoordinates(latitude=latitude,longitude=longitude),analysis_radius_m=radius_m,findings=[GeoFinding(**x) for x in findings],geojson=geojson,sources=sources,analysis_status='completed')
    @staticmethod
    def _deduplicate(findings):
        seen=set(); result=[]
        for x in findings:
            key=(x['type'],x.get('name'),round(x['distance_m'],-1))
            if key not in seen: seen.add(key); result.append(x)
        return sorted(result,key=lambda x:x['distance_m'])
