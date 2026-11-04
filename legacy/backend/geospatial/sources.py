from .config import OVERPASS_ENABLED, OVERPASS_URL
from .providers.overpass import OverpassProvider
def get_providers():
    return [OverpassProvider(OVERPASS_URL)] if OVERPASS_ENABLED else []
