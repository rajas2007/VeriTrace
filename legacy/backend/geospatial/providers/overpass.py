import requests
from ..catalog import SPATIAL_CATALOG
from ..geometry import distance_m
class OverpassProvider:
    def __init__(self, endpoint): self.endpoint=endpoint
    def query(self, latitude, longitude, radius_m):
        blocks=[]
        for config in SPATIAL_CATALOG.values():
            for key,value in config['osm_tags']:
                blocks.append(f'nwr(around:{radius_m},{latitude},{longitude})["{key}"="{value}"];')
        query='[out:json][timeout:60];('+''.join(blocks)+');out center tags;'
        r=requests.post(self.endpoint,data={'data':query},timeout=90,headers={'User-Agent':'UdyogPermitAI/1.0'})
        r.raise_for_status(); return r.json()
    def normalize(self, raw, latitude, longitude):
        out=[]
        for e in raw.get('elements',[]):
            tags=e.get('tags',{}); lat=e.get('lat'); lon=e.get('lon')
            if lat is None:
                c=e.get('center',{}); lat=c.get('lat'); lon=c.get('lon')
            if lat is None or lon is None: continue
            category=self._classify(tags)
            if not category: continue
            out.append({'type':category,'name':tags.get('name') or tags.get('name:en'),'distance_m':round(distance_m(latitude,longitude,lat,lon),2),'geometry_type':e.get('type'),'source':'OpenStreetMap/Overpass','confidence':0.85,'regulatory_relevance':SPATIAL_CATALOG[category]['regulatory_relevance'],'properties':tags})
        return out
    def _classify(self,tags):
        for category,config in SPATIAL_CATALOG.items():
            for key,value in config['osm_tags']:
                if tags.get(key)==value: return category
        return None
