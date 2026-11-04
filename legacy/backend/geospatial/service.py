import os
import math
from typing import Any, Dict, List

import httpx
from shapely.geometry import Point, mapping
from shapely.ops import transform
from pyproj import Transformer

from .models import (
    GeospatialRequest,
    GeospatialResult,
    GeospatialFinding,
)


class GeospatialService:
    """
    Geospatial intelligence service for UdyogPermit AI.

    Current implementation:
    - Creates a radius polygon around the user's location.
    - Queries OpenStreetMap through Overpass.
    - Converts relevant OSM objects into structured findings.
    - Returns GeoJSON suitable for frontend visualization.

    Regulatory GIS sources can be added later without changing
    the API contract used by main.py.
    """

    def __init__(self):
        self.overpass_enabled = (
            os.getenv("OVERPASS_ENABLED", "true").lower() == "true"
        )

        self.overpass_url = os.getenv(
            "OVERPASS_URL",
            "https://overpass-api.de/api/interpreter",
        )

    async def analyze(
        self,
        request: GeospatialRequest,
    ) -> GeospatialResult:

        latitude = request.latitude
        longitude = request.longitude
        radius_m = request.radius_m

        # --------------------------------------------------
        # 1. Create analysis polygon
        # --------------------------------------------------

        point = Point(longitude, latitude)

        # Transform WGS84 -> Web Mercator for metric buffering
        to_metric = Transformer.from_crs(
            "EPSG:4326",
            "EPSG:3857",
            always_xy=True,
        ).transform

        to_wgs84 = Transformer.from_crs(
            "EPSG:3857",
            "EPSG:4326",
            always_xy=True,
        ).transform

        metric_point = transform(to_metric, point)

        buffered = metric_point.buffer(radius_m)

        analysis_polygon = transform(
            to_wgs84,
            buffered,
        )

        geojson = mapping(analysis_polygon)

        findings: List[GeospatialFinding] = []

        # --------------------------------------------------
        # 2. Query OpenStreetMap / Overpass
        # --------------------------------------------------

        if self.overpass_enabled:

            osm_findings = await self._query_overpass(
                latitude,
                longitude,
                radius_m,
            )

            findings.extend(osm_findings)

        # --------------------------------------------------
        # 3. Return normalized result
        # --------------------------------------------------

        return GeospatialResult(
            site={
                "latitude": latitude,
                "longitude": longitude,
            },
            analysis_radius_m=radius_m,
            findings=findings,
            geojson={
                "type": "Feature",
                "geometry": geojson,
                "properties": {
                    "analysis_radius_m": radius_m,
                    "latitude": latitude,
                    "longitude": longitude,
                },
            },
        )

    async def _query_overpass(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
    ) -> List[GeospatialFinding]:

        query = f"""
        [out:json][timeout:25];

        (
          nwr["leisure"="nature_reserve"](around:{radius_m},{latitude},{longitude});
          nwr["boundary"="protected_area"](around:{radius_m},{latitude},{longitude});

          nwr["landuse"="forest"](around:{radius_m},{latitude},{longitude});
          nwr["natural"="wood"](around:{radius_m},{latitude},{longitude});

          nwr["natural"="wetland"](around:{radius_m},{latitude},{longitude});
          nwr["natural"="water"](around:{radius_m},{latitude},{longitude});

          nwr["waterway"="river"](around:{radius_m},{latitude},{longitude});
          nwr["waterway"="stream"](around:{radius_m},{latitude},{longitude});

          nwr["amenity"="hospital"](around:{radius_m},{latitude},{longitude});
          nwr["amenity"="school"](around:{radius_m},{latitude},{longitude});

          nwr["landuse"="residential"](around:{radius_m},{latitude},{longitude});
          nwr["landuse"="industrial"](around:{radius_m},{latitude},{longitude});

          nwr["natural"="coastline"](around:{radius_m},{latitude},{longitude});
        );

        out center tags;
        """

        try:

            async with httpx.AsyncClient(timeout=35.0) as client:

                response = await client.post(
                    self.overpass_url,
                    data={"data": query},
                )

                response.raise_for_status()

                payload = response.json()

        except Exception as exc:

            # Don't crash the complete application if OSM is unavailable.
            print(
                f"[Geospatial] Overpass query failed: {exc}"
            )

            return []

        findings: List[GeospatialFinding] = []

        for element in payload.get("elements", []):

            tags: Dict[str, Any] = element.get("tags", {})

            finding = self._classify_osm_element(
                element,
                tags,
                latitude,
                longitude,
            )

            if finding:
                findings.append(finding)

        return findings

    def _classify_osm_element(
        self,
        element: Dict[str, Any],
        tags: Dict[str, Any],
        latitude: float,
        longitude: float,
    ):

        finding_type = None

        # --------------------------------------------------
        # Environmental
        # --------------------------------------------------

        if (
            tags.get("leisure") == "nature_reserve"
            or tags.get("boundary") == "protected_area"
        ):
            finding_type = "protected_area"

        elif (
            tags.get("landuse") == "forest"
            or tags.get("natural") == "wood"
        ):
            finding_type = "forest"

        elif tags.get("natural") == "wetland":
            finding_type = "wetland"

        elif tags.get("waterway") in {
            "river",
            "stream",
            "canal",
        }:
            finding_type = "waterway"

        elif tags.get("natural") == "water":
            finding_type = "water_body"

        elif tags.get("natural") == "coastline":
            finding_type = "coastal_area"

        # --------------------------------------------------
        # Built environment
        # --------------------------------------------------

        elif tags.get("amenity") == "hospital":
            finding_type = "hospital"

        elif tags.get("amenity") == "school":
            finding_type = "school"

        elif tags.get("landuse") == "residential":
            finding_type = "residential_area"

        elif tags.get("landuse") == "industrial":
            finding_type = "industrial_area"

        if not finding_type:
            return None

        name = (
            tags.get("name")
            or tags.get("official_name")
            or tags.get("short_name")
        )

        # OSM doesn't always give us an exact geometry centroid
        # in a convenient format. For now distance is optional.
        distance = self._extract_distance(
            element,
            latitude,
            longitude,
        )

        return GeospatialFinding(
            type=finding_type,
            name=name,
            distance_m=distance,
            confidence=0.75,
            source="OpenStreetMap / Overpass",
            metadata={
                "osm_type": element.get("type"),
                "osm_id": element.get("id"),
                "tags": tags,
            },
        )

    def _extract_distance(
        self,
        element: Dict[str, Any],
        latitude: float,
        longitude: float,
    ):

        center = element.get("center")

        if not center:
            lat = element.get("lat")
            lon = element.get("lon")

            if lat is None or lon is None:
                return None

        else:
            lat = center.get("lat")
            lon = center.get("lon")

            if lat is None or lon is None:
                return None

        return self._haversine_distance(
            latitude,
            longitude,
            float(lat),
            float(lon),
        )

    @staticmethod
    def _haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        earth_radius = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)

        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            +
            math.cos(phi1)
            * math.cos(phi2)
            * math.sin(delta_lambda / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

        return round(earth_radius * c, 2)