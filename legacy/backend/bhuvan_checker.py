import math
import requests
import urllib3
from bs4 import BeautifulSoup

# Suppress SSL warnings when verify=False is used for local testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Official ISRO Bhuvan OGC Vector Service Subdomain Node
BHUVAN_WMS_URL = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Core EIA Reference Layers Config
EIA_LAYERS_CONFIG = [
    {
        "id": "land_use",
        "category": "Zoning",
        "display_name": "🗺️ Base Land Cover (MH LULC 50K)",
        "layer_name": "lulc:MH_LULC50K_1516"
    },
    {
        "id": "crz_zones",
        "category": "Environmental",
        "display_name": "🌊 Coastal Regulation Zones (CRZ)",
        "layer_name": "coastal:CZMP_Layers"
    },
    {
        "id": "protected_areas",
        "category": "Environmental",
        "display_name": "🌳 Eco-Sensitive Zones (ESZ)",
        "layer_name": "biodiversity:PA_Boundaries"
    },
    {
        "id": "asi_monuments",
        "category": "Heritage",
        "display_name": "🏛️ Archaeological Buffers (ASI)",
        "layer_name": "culture:ASI_Monuments"
    }
]

def generate_micro_bbox(lat: float, lon: float) -> str:
    """
    Constructs an ultra-tight bounding box (~20 meters) around the exact target coordinate
    to perform a precise Point-in-Polygon intersection check via WMS.
    """
    lat_offset = 0.0001
    lon_offset = 0.0001 / math.cos(math.radians(lat))
    min_lat, max_lat = lat - lat_offset, lat + lat_offset
    min_lon, max_lon = lon - lon_offset, lon + lon_offset
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


def scan_eia_compliance(lat: float, lon: float, layer_name: str) -> tuple[bool, str]:
    """
    Queries Bhuvan WMS GetFeatureInfo using micro-bbox math.
    Returns (True, detail_string) if a spatial table row is parsed, else (False, "").
    """
    bbox = generate_micro_bbox(lat, lon)
    
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer_name,
        "QUERY_LAYERS": layer_name,
        "STYLES": "",
        "BBOX": bbox,
        "SRS": "EPSG:4326",
        "WIDTH": "101",
        "HEIGHT": "101",
        "X": "50",  # Checks exact center pixel
        "Y": "50",
        "INFO_FORMAT": "text/html",
        "FEATURE_COUNT": "5"
    }
    
    print(f"\n[DEBUG] Querying layer: [{layer_name}]")
    print(f"[DEBUG] Target Micro-BBOX: {bbox}")

    try:
        response = requests.get(
            BHUVAN_WMS_URL, 
            params=params, 
            headers=HEADERS, 
            timeout=5,
            verify=False
        )
        
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Request URL: {response.url}")
        print(f"[+] Response Preview: {response.text[:200].strip()}")
        
        if response.status_code == 200 and "table" in response.text.lower():
            soup = BeautifulSoup(response.text, 'html.parser')
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                if len(rows) >= 2:
                    data_cells = rows[1].find_all('td')
                    if len(data_cells) >= 2:
                        detail = data_cells[1].get_text(strip=True)
                        print(f"  └── 🚨 FEATURE FOUND: {detail}")
                        return True, detail
            print("  └── 🚨 FEATURE FOUND: Feature table detected")
            return True, "Detected feature zone"
            
        print("  └── ℹ️ No feature detected.")
        return False, ""

    except requests.exceptions.Timeout:
        print(f"  └── ❌ TIMEOUT ERROR on layer [{layer_name}]")
        return False, ""
    except Exception as err:
        print(f"  └── ❌ ERROR on layer [{layer_name}]: {type(err).__name__} - {err}")
        return False, ""


def prepare_eia_payload(lat: float, lon: float) -> dict:
    """
    Calculates 3km EIA boundary box and returns dynamic Bhuvan layer detections.
    """
    delta_lat = 0.027
    delta_lon = 0.028

    bbox = [
        lon - delta_lon, lat - delta_lat,
        lon + delta_lon, lat + delta_lat
    ]

    processed_layers = []
    
    for layer in EIA_LAYERS_CONFIG:
        is_found, detail_text = scan_eia_compliance(lat, lon, layer["layer_name"])
        
        processed_layers.append({
            "id": layer["id"],
            "category": layer["category"],
            "display_name": layer["display_name"],
            "wms_url": BHUVAN_WMS_URL,
            "layer_name": layer["layer_name"],
            "default_on": is_found,
            "found": is_found,
            "feature_detail": detail_text if is_found else None
        })

    return {
        "status": "success",
        "center_point": {"lat": lat, "lon": lon},
        "bbox_bounds": bbox,
        "search_bound_box_geojson": {
            "type": "Feature",
            "properties": {"name": "3km Search Boundary Area"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]]
                ]]
            }
        },
        "regulatory_layers": processed_layers
    }


# Standalone CLI Testing Execution
if __name__ == "__main__":
    import json

    # Test Sample: Mumbai Colaba / Naval Dockyard Sector Coordinates
    TEST_LAT = 18.9220
    TEST_LON = 72.8347

    print("=" * 60)
    print("🚀 RUNNING STANDALONE BHUVAN EIA COMPLIANCE CHECK")
    print(f"📍 Testing Target Point -> Latitude: {TEST_LAT}, Longitude: {TEST_LON}")
    print("=" * 60)

    payload = prepare_eia_payload(TEST_LAT, TEST_LON)

    print("\n" + "=" * 60)
    print("📋 FINAL OUTPUT JSON PAYLOAD")
    print("=" * 60)
    print(json.dumps(payload, indent=2))