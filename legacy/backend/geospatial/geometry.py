from math import radians, sin, cos, sqrt, atan2
from shapely.geometry import Point, mapping
from shapely.ops import transform
import pyproj

def create_point(latitude, longitude): return Point(longitude, latitude)
def create_buffer(latitude, longitude, radius_m):
    point=create_point(latitude,longitude)
    local=pyproj.CRS(f'+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m +no_defs')
    wgs84=pyproj.CRS('EPSG:4326')
    forward=pyproj.Transformer.from_crs(wgs84,local,always_xy=True).transform
    backward=pyproj.Transformer.from_crs(local,wgs84,always_xy=True).transform
    return transform(backward, transform(forward,point).buffer(radius_m))
def distance_m(lat1,lon1,lat2,lon2):
    r=6371000.0; a1=radians(lat1); a2=radians(lat2); dl1=radians(lat2-lat1); dl2=radians(lon2-lon1)
    a=sin(dl1/2)**2+cos(a1)*cos(a2)*sin(dl2/2)**2
    return r*2*atan2(sqrt(a),sqrt(1-a))
def geometry_to_geojson(geometry): return mapping(geometry)
