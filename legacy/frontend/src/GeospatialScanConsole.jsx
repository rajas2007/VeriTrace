import React, { useEffect, useState, useRef } from 'react';

// Maps each real backend layer id (see backend/bhuvan_checker.py EIA_LAYERS_CONFIG)
// to a plain-English description of what's actually being scanned for.
const LAYER_SCAN_LABELS = {
  land_use: 'Classifying base land-use / land-cover',
  crz_zones: 'Scanning for Coastal Regulation Zones & major water bodies',
  protected_areas: 'Scanning for forest cover & Eco-Sensitive Zones',
  asi_monuments: 'Scanning for ASI-protected archaeological buffers',
};

const REVEAL_DELAY_MS = 950;

export default function GeospatialScanConsole({ geoLoading, geoData }) {
  const [revealedCount, setRevealedCount] = useState(0);
  const logEndRef = useRef(null);
  const layers = geoData?.regulatory_layers || [];

  // Whenever a *new* geoData object arrives, reset and step through the
  // real results one at a time instead of dumping them all at once.
  useEffect(() => {
    if (!geoData) {
      setRevealedCount(0);
      return;
    }
    setRevealedCount(0);
    const timer = setInterval(() => {
      setRevealedCount((c) => {
        if (c >= layers.length) {
          clearInterval(timer);
          return c;
        }
        return c + 1;
      });
    }, REVEAL_DELAY_MS);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geoData]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [revealedCount, geoLoading]);

  if (!geoLoading && !geoData) return null;

  const lat = geoData?.center_point?.lat;
  const lon = geoData?.center_point?.lon;
  const isScanning = !!geoData && revealedCount < layers.length;
  const isComplete = !!geoData && layers.length > 0 && revealedCount >= layers.length;

  return (
    <div className="bg-slate-900 rounded-xl shadow-md border border-slate-700 p-4 font-mono text-xs leading-relaxed text-slate-200 h-[240px] overflow-y-auto">
      <div className="flex items-center gap-2 mb-3 text-slate-400 text-[11px] uppercase tracking-wider sticky top-0 bg-slate-900 pb-1">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        Environmental Siting Scan — Live
      </div>

      {!geoData && geoLoading && (
        <div className="flex items-center gap-2 text-sky-300">
          <span className="agent-wave" aria-hidden="true">
            <span></span><span></span><span></span><span></span><span></span>
          </span>
          Acquiring device location & contacting ISRO Bhuvan...
        </div>
      )}

      {geoData && (
        <div className="space-y-1.5">
          <p className="text-emerald-400">
            ✔ Location found — Lat {lat?.toFixed(4)}, Lon {lon?.toFixed(4)}
          </p>
          <p className="text-slate-400">→ Establishing 3km regulatory scan radius...</p>

          {layers.slice(0, revealedCount).map((layer) => (
            <div key={layer.id} className="pt-1">
              <p className="text-slate-300">
                → {LAYER_SCAN_LABELS[layer.id] || layer.display_name}...
              </p>
              {layer.found ? (
                <p className="text-amber-400 pl-4">
                  ⚠ Detected within 3km radius — {layer.feature_detail || layer.category}
                </p>
              ) : (
                <p className="text-emerald-400 pl-4">✔ Not found within 3km radius</p>
              )}
            </div>
          ))}

          {isScanning && (
            <p className="text-sky-300 pt-1 animate-pulse">
              → {LAYER_SCAN_LABELS[layers[revealedCount]?.id] || 'Scanning next layer'}...
            </p>
          )}

          {isComplete && (
            <p className="text-emerald-400 pt-2 font-semibold">
              ✔ Environmental siting scan complete — {layers.filter(l => l.found).length} constraint(s) detected.
            </p>
          )}
        </div>
      )}
      <div ref={logEndRef} />
    </div>
  );
}