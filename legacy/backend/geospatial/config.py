import os
from dotenv import load_dotenv
load_dotenv()
DEFAULT_RADIUS_M = 3000
OVERPASS_URL = os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
OVERPASS_ENABLED = os.getenv('OVERPASS_ENABLED', 'true').lower() == 'true'
