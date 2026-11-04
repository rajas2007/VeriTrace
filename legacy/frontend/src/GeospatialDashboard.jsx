import React, { useEffect, useRef } from 'react';

export default function GeospatialDashboard({ geoData }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);

  useEffect(() => {
    // Safety check: ensure geoData, coordinates, map ref, and Leaflet exist
    if (
      !geoData || 
      !geoData.center_point || 
      !mapRef.current || 
      !window.L
    ) {
      return;
    }

    const { center_point, search_bound_box_geojson, regulatory_layers = [] } = geoData;

    // Reset map instance on re-render to avoid "Map container is already initialized" error
    if (mapInstance.current) {
      mapInstance.current.remove();
      mapInstance.current = null;
    }

    try {
      // Initialize Leaflet Map
      const map = window.L.map(mapRef.current).setView([center_point.lat, center_point.lon], 13);
      mapInstance.current = map;

      // Base Tile Layer
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(map);

      // Render 3km Boundary Box if GeoJSON exists
      if (search_bound_box_geojson) {
        window.L.geoJSON(search_bound_box_geojson, {
          style: {
            color: "#ef4444",
            weight: 2,
            fillColor: "#ef4444",
            fillOpacity: 0.05
          }
        }).addTo(map);
      }

      // Facility Site Marker
      window.L.marker([center_point.lat, center_point.lon])
        .bindPopup(`<b>Target Facility Site</b><br/>Lat: ${center_point.lat.toFixed(4)}, Lon: ${center_point.lon.toFixed(4)}`)
        .openPopup()
        .addTo(map);

      // Filter and render active WMS layers where default_on or found is true
      const activeLayers = regulatory_layers.filter(
        layer => layer.default_on === true || layer.found === true
      );

      activeLayers.forEach(layer => {
        const wmsUrl = layer.wms_url || "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms";

        window.L.tileLayer.wms(wmsUrl, {
          layers: layer.layer_name,
          format: 'image/png',
          transparent: true,
          version: '1.1.1',
          opacity: 0.65,
          attribution: '© ISRO Bhuvan'
        }).addTo(map);
      });
    } catch (err) {
      console.error("Leaflet Map Rendering Error:", err);
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [geoData]);

  // Gracefully return null if no data is present yet
  if (!geoData || !geoData.regulatory_layers) return null;

  // Filter detected constraints for list display
  const detectedList = geoData.regulatory_layers.filter(
    layer => layer.default_on === true || layer.found === true
  );

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200 p-6 space-y-4 mt-6">
      <div>
        <h3 className="text-lg font-bold text-slate-800">EIA Environmental Siting Analysis</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Overlapping regulatory bounds detected within 3km radius (Lat: {geoData.center_point?.lat?.toFixed(4)}, Lon: {geoData.center_point?.lon?.toFixed(4)})
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {/* Map Container (now stacked on top since this panel lives on the right side) */}
        <div className="relative h-[380px]">
          <div ref={mapRef} className="w-full h-full rounded-lg border border-slate-200 z-10" style={{ minHeight: '380px' }}></div>
        </div>

        {/* Detected Constraints List */}
        <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
            Detected Constraints ({detectedList.length})
          </span>

          {detectedList.length === 0 ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs font-medium">
              ✅ No critical environmental sensitive zones detected in 3km radius.
            </div>
          ) : (
            detectedList.map((layer) => (
              <div 
                key={layer.id} 
                className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-900 shadow-xs flex items-center justify-between"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-semibold">{layer.display_name}</span>
                  <span className="text-[11px] text-amber-700 font-mono mt-0.5">
                    {layer.feature_detail || layer.category}
                  </span>
                </div>
                <span className="text-[10px] uppercase font-extrabold bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
                  Detected
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}