import React, { useState, useEffect } from 'react';
import Home from './Home';
import Header from './Header';
import Footer from './Footer';
import { RotateCcw } from 'lucide-react';
import GeospatialDashboard from './GeospatialDashboard';
import GeospatialScanConsole from './GeospatialScanConsole';
import AgentThinkingStatus from './AgentThinkingStatus';
import WorkflowCanvas from './WorkflowCanvas';

const API_BASE = window.location.hostname === "localhost" 
  ? "http://localhost:8000/api/v1" 
  : "/api/v1";

// Helper function to extract or default coordinates from raw user input text
const extractLocationFromText = (text) => {
  // Regex to match raw coordinates like "18.5204, 73.8567" or "Lat 18.5204 Lon 73.8567"
  const coordRegex = /(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)/;
  const match = text.match(coordRegex);

  if (match) {
    return {
      latitude: parseFloat(match[1]),
      longitude: parseFloat(match[2])
    };
  }

  // Default fallback (e.g. Chakan MIDC / Pune coordinates) if location name geocoding isn't available
  return {
    latitude: 18.7600,
    longitude: 73.8600
  };
};

function WorkflowApp({ onGoHome }) {
  const [activeTab, setActiveTab] = useState('workflow');

  // Workflow States
  const [rawInput, setRawInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [threadId, setThreadId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [compliances, setCompliances] = useState([]);
  const [eligibleSubsidies, setEligibleSubsidies] = useState([]);
  const [selectedSubsidies, setSelectedSubsidies] = useState({});
  const [roadmapResult, setRoadmapResult] = useState(null);

  // Clarifying Questions State (Step 1.5)
  const [clarificationQuestions, setClarificationQuestions] = useState([]);
  const [clarificationRound, setClarificationRound] = useState(0);
  const [clarificationCategory, setClarificationCategory] = useState(null);
  const [pollutionCategory, setPollutionCategory] = useState(null);
  const [clarificationAnswers, setClarificationAnswers] = useState({});
  const [clarifyLoading, setClarifyLoading] = useState(false);

  // Geospatial Intelligence State Hooks
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoData, setGeoData] = useState(null);
  const [showGeo, setShowGeo] = useState(false);
  const [geoMode, setGeoMode] = useState('idle'); // 'idle', 'detecting', 'detected', 'error', 'manual_entry'
  const [geoError, setGeoError] = useState('');
  const [geoResolvedName, setGeoResolvedName] = useState({ city: '', state: '' });
  const [manualLocationInput, setManualLocationInput] = useState('');

  

  // Handle Geospatial Activation based on user text input
  const handleActivateGeospatial = async (manualCoords = null, manualName = null) => {
    setShowGeo(true);
    setGeoLoading(true);
    setGeoData(null);
    setGeoError('');
    
    let coordsToUse = manualCoords;
    
    if (!coordsToUse) {
      setGeoMode('detecting');
      try {
        coordsToUse = await new Promise((resolve, reject) => {
          if (!navigator.geolocation) {
            reject(new Error("Geolocation is not supported by your browser."));
            return;
          }
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
            (err) => reject(new Error(err.message || "Location access was not provided."))
          );
        });
      } catch (err) {
        setGeoLoading(false);
        setGeoError(err.message || "Unable to determine your current location.");
        setGeoMode('error');
        return;
      }
    }
    
    // Reverse geocode to get city/state
    if (manualName) {
      setGeoResolvedName({ city: manualName, state: '' });
    } else {
      try {
        const nomRes = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${coordsToUse.latitude}&lon=${coordsToUse.longitude}&format=json`);
        const nomData = await nomRes.json();
        if (nomData && nomData.address) {
          const addr = nomData.address;
          const city = addr.city || addr.town || addr.municipality || addr.county || addr.district || 'Unknown';
          const state = addr.state || 'Unknown';
          setGeoResolvedName({ city, state });
        } else {
          setGeoResolvedName({ city: 'Unknown', state: 'Unknown' });
        }
      } catch(e) {
        setGeoResolvedName({ city: 'Unknown', state: 'Unknown' });
      }
    }
    
    setGeoMode('detected');
    
    try {
      const res = await fetch(`${API_BASE}/geospatial/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latitude: coordsToUse.latitude,
          longitude: coordsToUse.longitude,
          input_text: rawInput
        })
      });

      if (!res.ok) {
        setGeoError("Backend returned an error code: " + res.status);
        setGeoMode('error');
        setGeoLoading(false);
        return;
      }

      const data = await res.json();
      setGeoData(data);
    } catch (err) {
      setGeoError("Failed to fetch geospatial data.");
      setGeoMode('error');
    } finally {
      setGeoLoading(false);
    }
  };

  const handleTestAnotherLocationSubmit = async () => {
    if (!manualLocationInput.trim()) return;
    setGeoMode('detecting'); // visual loading
    const coordRegex = /(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)/;
    const match = manualLocationInput.match(coordRegex);
    if (match) {
      await handleActivateGeospatial({ latitude: parseFloat(match[1]), longitude: parseFloat(match[2]) }, manualLocationInput);
      return;
    }
    // Forward geocode
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(manualLocationInput)}&format=json&limit=1`);
      const data = await res.json();
      if (data && data.length > 0) {
        const locName = data[0].display_name.split(',').slice(0, 2).join(',');
        await handleActivateGeospatial({ latitude: parseFloat(data[0].lat), longitude: parseFloat(data[0].lon) }, locName);
      } else {
        setGeoError("Location not found. Try entering Latitude, Longitude or a valid city name.");
        setGeoMode('error');
      }
    } catch (err) {
      setGeoError("Geocoding failed.");
      setGeoMode('error');
    }
  };

  const handleToggleLayer = (layerId) => {
    if (!geoData) return;
    setGeoData({
      ...geoData,
      regulatory_layers: geoData.regulatory_layers.map(l => 
        l.id === layerId ? { ...l, default_on: !l.default_on } : l
      )
    });
  };

  // Validation States
  const [docText, setDocText] = useState('');
  const [validationReport, setValidationReport] = useState(null);
  const [validating, setValidating] = useState(false);

  // --- Workflow Handlers ---
  const handleStartWorkflow = async (e) => {
    e.preventDefault();
    if (!rawInput.trim()) return;
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/workflow/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_industrial_data: rawInput })
      });
      const data = await res.json();
      setThreadId(data.thread_id);

      if (data.status === 'needs_clarification') {
        enterClarificationStep(data);
        return;
      }

      setProfile(data.profile);
      setCompliances(data.compliances || []);

      const subMap = {};
      (data.eligible_subsidies || []).forEach((sub, idx) => {
        subMap[idx] = false;
      });
      setEligibleSubsidies(data.eligible_subsidies || []);
      setSelectedSubsidies(subMap);
      setStep(2);
    } catch (err) {
      alert("Failed to connect to backend. Ensure FastAPI is running.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const enterClarificationStep = (data) => {
    const questions = data.clarification_questions || [];
    const initialAnswers = {};
    questions.forEach((q) => {
      initialAnswers[q.field] = { value: q.default ?? '', skipped: false };
    });
    setClarificationQuestions(questions);
    setClarificationRound(data.clarification_round || 0);
    setClarificationCategory(data.category || null);
    setPollutionCategory(data.pollution_category || null);
    setProfile(data.profile);
    setClarificationAnswers(initialAnswers);
    setStep(1.5);
  };

  const handleClarificationChange = (field, value) => {
    setClarificationAnswers((prev) => ({
      ...prev,
      [field]: { ...prev[field], value, skipped: false },
    }));
  };

  const handleClarificationSkip = (field) => {
    setClarificationAnswers((prev) => ({
      ...prev,
      [field]: { ...prev[field], skipped: true },
    }));
  };

  const handleSubmitClarifications = async () => {
    setClarifyLoading(true);
    try {
      const answers = clarificationQuestions.map((q) => {
        const entry = clarificationAnswers[q.field] || {};
        return { field: q.field, answer: entry.value, skipped: !!entry.skipped };
      });

      const res = await fetch(`${API_BASE}/workflow/clarify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, answers }),
      });
      const data = await res.json();

      if (data.status === 'needs_clarification') {
        enterClarificationStep(data);
        return;
      }

      setProfile(data.profile);
      setCompliances(data.compliances || []);
      const subMap = {};
      (data.eligible_subsidies || []).forEach((sub, idx) => {
        subMap[idx] = false;
      });
      setEligibleSubsidies(data.eligible_subsidies || []);
      setSelectedSubsidies(subMap);
      setStep(2);
    } catch (err) {
      alert("Error submitting clarification answers.");
      console.error(err);
    } finally {
      setClarifyLoading(false);
    }
  };

  const handleResumeWorkflow = async () => {
    setLoading(true);
    const chosen = eligibleSubsidies.filter((_, idx) => selectedSubsidies[idx]);

    try {
      const res = await fetch(`${API_BASE}/workflow/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, selected_subsidies: chosen })
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Error resuming workflow: ${data.detail || JSON.stringify(data)}`);
        return;
      }
      setRoadmapResult(data);
      setStep(3);
    } catch (err) {
      alert("Error resuming workflow.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleValidateDoc = async (e) => {
    e.preventDefault();
    if (!docText.trim()) return;
    setValidating(true);

    try {
      const res = await fetch(`${API_BASE}/document/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_text: docText })
      });
      const data = await res.json();
      setValidationReport(data.validation_report);
    } catch (err) {
      alert("Validation service error.");
      console.error(err);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="min-h-screen text-slate-900 font-sans" style={{ background: "#fff", display: "flex", flexDirection: "column" }}>
      <Header step={step} onNavigate={(s) => { if (s > 0) setStep(s); }} onGoHome={onGoHome} />

      {/* Internal tab bar for Compliance vs Validation */}
      <div style={{ borderBottom: "1px solid #DCE9EF", background: "#fff" }}>
        <div className="max-w-7xl mx-auto px-6" style={{ display: "flex", gap: 8, paddingTop: 8, paddingBottom: 8 }}>
          <button
            onClick={() => setActiveTab('workflow')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'workflow'
                ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Compliance & Roadmap Engine
          </button>
          <button
            onClick={() => setActiveTab('validation')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'validation'
                ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Document Pre-Validation
          </button>
        </div>
      </div>

      <main style={{ flex: 1, background: "var(--gray-bg)", display: "flex", flexDirection: "column" }}>
        {activeTab === 'workflow' && (
          <div className="space-y-6">
            {step === 1 && (
              <div className="fade-in" style={{ width: "100%" }}>
                <div style={{ background: "var(--navy)", borderBottom: "3px solid #D4A017", padding: "2rem 1.5rem" }}>
                  <div style={{ maxWidth: 1160, margin: "0 auto" }}>
                    <div className="section-label" style={{ color: "rgba(255,255,255,0.5)", marginBottom: "0.5rem" }}>
                      Step 1 of 3
                    </div>
                    <h1 style={{ color: "white", fontSize: "1.75rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                      Tell us about your project
                    </h1>
                    <p style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.9375rem", lineHeight: 1.6, margin: 0, maxWidth: 600 }}>
                      Provide information about your proposed business or industrial activity. This information will be used to identify relevant approvals and requirements.
                    </p>
                  </div>
                </div>

                <div style={{ maxWidth: 1160, margin: "0 auto", padding: "2rem 1.5rem 3rem" }}>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                    
                    {/* LEFT: Industrial Input Form */}
                    <div className="gov-card" style={{ padding: "1.75rem" }}>
                      <h2 style={{ color: "var(--navy)", fontSize: "1.0625rem", marginBottom: "0.25rem", fontWeight: 600 }}>
                        Project &amp; Business Information
                      </h2>
                      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
                        Describe your project in as much detail as possible.
                      </p>

                      <form onSubmit={handleStartWorkflow} className="space-y-5">
                        <div>
                          <label className="gov-label" htmlFor="project-input">
                            Project Description
                            <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "0.8125rem", marginLeft: "0.5rem" }}>
                              (required)
                            </span>
                          </label>
                          <textarea
                            id="project-input"
                            rows="9"
                            className="gov-textarea"
                            placeholder="e.g., Setting up a lithium-ion battery assembly plant in Chakan MIDC, Pune. Raw materials include cells and casings..."
                            value={rawInput}
                            onChange={(e) => setRawInput(e.target.value)}
                            disabled={loading}
                          />
                        </div>
                        {loading && <AgentThinkingStatus phase="start" />}
                        <div style={{ marginTop: "1.25rem", display: "flex", justifyContent: "flex-end" }}>
                          <button
                            type="submit"
                            disabled={loading || rawInput.trim().length < 10}
                            className="btn-primary"
                            style={{
                              opacity: (loading || rawInput.trim().length < 10) ? 0.5 : 1,
                              cursor: (loading || rawInput.trim().length < 10) ? "not-allowed" : "pointer",
                              fontSize: "0.9375rem",
                              padding: "0.75rem 1.5rem",
                              width: "100%",
                              justifyContent: "center"
                            }}
                          >
                            {loading ? "Analyzing Profile & Mapping Compliance..." : "Generate Compliance & Incentive Matrix"}
                          </button>
                        </div>
                      </form>

                      <div className="gov-divider" style={{ margin: "2rem 0" }}></div>

                      <h3 style={{ color: "var(--navy)", fontSize: "0.9375rem", marginBottom: "1rem", fontWeight: 600 }}>
                        Spatial Analysis Option
                      </h3>
                      {(geoMode === 'idle' || geoMode === 'detecting') && (
                        <button
                          type="button"
                          onClick={() => handleActivateGeospatial()}
                          disabled={geoLoading || geoMode === 'detecting'}
                          className="btn-secondary"
                          style={{ width: "100%", justifyContent: "center", padding: "0.75rem 1.5rem" }}
                        >
                          {geoMode === 'detecting' ? "Detecting your current location..." : "Activate Geospatial Intelligence"}
                        </button>
                      )}

                      {geoMode === 'detected' && (
                        <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                           <div className="flex items-center gap-2 mb-2">
                             <span>??</span>
                             <span className="font-semibold text-slate-800 text-sm">Location detected</span>
                           </div>
                           <div className="text-sm text-slate-600 ml-6">
                             <div>City/District: <span className="font-medium text-slate-800">{geoResolvedName.city}</span></div>
                             <div>State: <span className="font-medium text-slate-800">{geoResolvedName.state}</span></div>
                           </div>
                           <div className="mt-3 ml-6 flex gap-2">
                             <button type="button" onClick={() => setGeoMode('manual_entry')} className="text-xs text-blue-600 hover:text-blue-800 underline">Test Another Location</button>
                           </div>
                        </div>
                      )}
                      
                      {geoMode === 'error' && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                           <div className="text-sm text-red-700 font-medium mb-2">{geoError || "Unable to determine your current location."}</div>
                           <div className="flex gap-3">
                             <button type="button" onClick={() => handleActivateGeospatial()} className="text-xs bg-white border border-red-300 text-red-700 px-3 py-1 rounded hover:bg-red-50">Try Again</button>
                             <button type="button" onClick={() => setGeoMode('manual_entry')} className="text-xs bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700">Test Another Location</button>
                           </div>
                        </div>
                      )}

                      {geoMode === 'manual_entry' && (
                        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                           <label className="block text-sm font-semibold text-slate-800 mb-2">Enter Test Location</label>
                           <input type="text" className="w-full rounded border border-slate-300 p-2 text-sm mb-2" placeholder="e.g. Pune, Maharashtra OR 18.52, 73.85" value={manualLocationInput} onChange={e => setManualLocationInput(e.target.value)} disabled={geoLoading} />
                           <div className="flex gap-2">
                              <button type="button" onClick={handleTestAnotherLocationSubmit} className="btn-primary" style={{ padding: "0.5rem 1rem", fontSize: "0.875rem" }} disabled={geoLoading}>{geoLoading ? 'Detecting...' : 'Run Test Location'}</button>
                              <button type="button" onClick={() => handleActivateGeospatial()} className="text-xs text-blue-600 hover:text-blue-800 underline" disabled={geoLoading}>Use My Current Location</button>
                           </div>
                        </div>
                      )}
                    </div>

                    {/* RIGHT: Delayed Geospatial Panel */}
                    <div className="space-y-4">
                      {showGeo ? (
                        <>
                          <GeospatialScanConsole geoLoading={geoLoading} geoData={geoData} />
                          {geoData && <GeospatialDashboard geoData={geoData} />}
                        </>
                      ) : (
                        <div className="gov-card" style={{ height: "100%", minHeight: "300px", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "2rem", color: "var(--text-muted)", fontSize: "0.875rem", borderStyle: "dashed" }}>
                          Activate Geospatial Intelligence to run the environmental siting scan and view the map here.
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              </div>
            )}
            
            <div className="max-w-7xl mx-auto px-6 pb-8 w-full">
              {/* Step 1.5: Clarifying Questions */}
            {step === 1.5 && (
              <div className="bg-white rounded-xl shadow-md border border-slate-200 p-8 max-w-3xl mx-auto space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-slate-800">A Few Details Needed</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    {clarificationCategory ? `Category: ${clarificationCategory}. ` : ''}
                    {pollutionCategory ? `CPCB pollution category: ${pollutionCategory}. ` : ''}
                    Round {clarificationRound} of 2. Answer what you can — anything skipped uses a sensible default.
                  </p>
                </div>

                <div className="space-y-4">
                  {clarificationQuestions.map((q) => {
                    const entry = clarificationAnswers[q.field] || { value: '', skipped: false };
                    const isHazard = q.impact === 'high';
                    return (
                      <div
                        key={q.field}
                        className={`p-4 rounded-lg border bg-white shadow-xs ${
                          isHazard ? 'border-l-4 border-l-red-400 border-slate-200' : 'border-slate-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <label className="text-sm font-medium text-slate-800 block mb-2">
                            {q.question}
                            {isHazard && (
                              <span className="ml-2 text-xs font-semibold text-red-500 uppercase tracking-wide">
                                Hazard-critical
                              </span>
                            )}
                          </label>
                          <button
                            type="button"
                            onClick={() => handleClarificationSkip(q.field)}
                            className={`text-xs font-medium px-2 py-1 rounded border transition-all shrink-0 ${
                              entry.skipped
                                ? 'bg-slate-800 text-white border-slate-800'
                                : 'text-slate-500 border-slate-300 hover:bg-slate-100'
                            }`}
                          >
                            {entry.skipped ? 'Skipped' : 'Skip'}
                          </button>
                        </div>

                        {q.input_type === 'boolean' && (
                          <select
                            className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            value={entry.value === true ? 'true' : entry.value === false ? 'false' : ''}
                            onChange={(e) => handleClarificationChange(q.field, e.target.value === 'true')}
                            disabled={entry.skipped}
                          >
                            <option value="">Select...</option>
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                          </select>
                        )}

                        {q.input_type === 'single_select' && (
                          <select
                            className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            value={entry.value || ''}
                            onChange={(e) => handleClarificationChange(q.field, e.target.value)}
                            disabled={entry.skipped}
                          >
                            <option value="">Select...</option>
                            {(q.options || []).map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        )}

                        {q.input_type === 'number' && (
                          <input
                            type="number"
                            className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            value={entry.value ?? ''}
                            onChange={(e) => handleClarificationChange(q.field, e.target.value === '' ? '' : Number(e.target.value))}
                            disabled={entry.skipped}
                          />
                        )}

                        {(q.input_type === 'text' || !q.input_type) && (
                          <input
                            type="text"
                            className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                            value={entry.value ?? ''}
                            onChange={(e) => handleClarificationChange(q.field, e.target.value)}
                            disabled={entry.skipped}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                {clarifyLoading && <AgentThinkingStatus phase="clarify" />}
                <button
                  onClick={handleSubmitClarifications}
                  disabled={clarifyLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center disabled:opacity-50"
                >
                  {clarifyLoading ? <span>Re-checking Profile...</span> : <span>Continue</span>}
                </button>
              </div>
            )}

            {/* Step 2: Incentive Selection */}
            {step === 2 && (
                <div className="max-w-7xl mx-auto px-6 py-8 w-full">
                  <div className="bg-white rounded-xl shadow-md border border-slate-200 p-8 space-y-8">
                    <div>
                      <h2 className="text-xl font-bold text-slate-800" style={{ color: "var(--navy)" }}>Review Approvals &amp; Select Subsidies</h2>
                      <p className="text-sm text-slate-500 mt-1">
                        Agent 2 identified {compliances.length} mandatory compliances and {eligibleSubsidies.length} eligible state subsidies.
                      </p>
                    </div>

                    <div className="gov-card p-5">
                      <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4" style={{ color: "var(--navy)" }}>Extracted Facility Profile</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(profile || {}).map(([key, val]) => (
                          <div key={key} className="bg-slate-50 p-3 rounded border border-slate-100">
                            <div className="text-xs text-slate-400 font-medium uppercase mb-1">{key.replace(/_/g, ' ')}</div>
                            <div className="text-sm font-medium text-slate-800">{Array.isArray(val) ? val.join(', ') : String(val)}</div>
                          </div>
                        ))}
                      </div>
                      {(!profile || Object.keys(profile).length === 0) && (
                        <div className="text-sm text-slate-500">No profile data extracted.</div>
                      )}
                    </div>

                    <div>
                      <div className="flex justify-between items-end mb-4">
                        <h3 className="font-bold text-lg" style={{ color: "var(--navy)" }}>Required Mandatory Compliances</h3>
                        <span className="text-xs font-semibold px-2 py-1 bg-blue-50 text-blue-700 rounded-md border border-blue-100">{compliances.length} approvals identified</span>
                      </div>
                      
                      {compliances.length > 0 ? (
                        <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
                          <table className="gov-table w-full">
                            <thead>
                              <tr>
                                <th style={{ width: "5%", padding: "12px", borderBottom: "1px solid #e2e8f0", textAlign: "left" }}>#</th>
                                <th style={{ width: "50%", padding: "12px", borderBottom: "1px solid #e2e8f0", textAlign: "left" }}>Approval / Compliance</th>
                                <th style={{ width: "45%", padding: "12px", borderBottom: "1px solid #e2e8f0", textAlign: "left" }}>Authority</th>
                              </tr>
                            </thead>
                            <tbody>
                              {compliances.map((comp, idx) => (
                                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                  <td className="font-medium text-slate-400" style={{ padding: "12px", borderBottom: "1px solid #e2e8f0" }}>{idx + 1}</td>
                                  <td className="font-semibold text-slate-800" style={{ padding: "12px", borderBottom: "1px solid #e2e8f0" }}>{comp.name}</td>
                                  <td style={{ padding: "12px", borderBottom: "1px solid #e2e8f0" }}>{comp.authority || "N/A"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="gov-card p-8 text-center text-slate-500 bg-slate-50 border-dashed">
                          No mandatory compliances identified for this profile.
                        </div>
                      )}
                    </div>

                    <div className="gov-divider"></div>

                    <div>
                      <div className="flex justify-between items-end mb-4">
                        <h3 className="font-bold text-lg" style={{ color: "var(--navy)" }}>Eligible State Subsidies</h3>
                        <span className="text-xs font-semibold px-2 py-1 bg-green-50 text-green-700 rounded-md border border-green-100">{eligibleSubsidies.length} incentives available</span>
                      </div>
                      <p className="text-sm text-slate-500 mb-4">Select the subsidies you wish to apply for during this project.</p>
                      
                      {eligibleSubsidies.length > 0 ? (
                        <div className="space-y-3">
                          {eligibleSubsidies.map((sub, idx) => {
                            const isSelected = selectedSubsidies[idx] || false;
                            const cls = "flex items-start space-x-4 p-5 rounded-xl border transition-all cursor-pointer " + (isSelected ? "border-blue-500 bg-blue-50/30 ring-1 ring-blue-500" : "border-slate-200 bg-white hover:border-blue-300");
                            return (
                              <label key={idx} className={cls}>
                                <input
                                  type="checkbox"
                                  className="mt-1 h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                  checked={isSelected}
                                  onChange={(e) => setSelectedSubsidies({...selectedSubsidies, [idx]: e.target.checked})}
                                />
                                <div>
                                  <span className="font-bold text-slate-800 text-base block mb-1">{sub.name}</span>
                                  <span className="text-sm text-slate-600 block leading-relaxed">{sub.description}</span>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="gov-card p-8 text-center text-slate-500 bg-slate-50 border-dashed">
                          No eligible subsidies found for this profile.
                        </div>
                      )}
                    </div>

                    <div className="pt-4 flex justify-end">
                      <button
                        onClick={handleResumeWorkflow}
                        className="btn-primary"
                        style={{ padding: "0.875rem 2rem", fontSize: "1rem" }}
                      >
                        Generate Workflow Roadmap
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Step 3: Roadmap */}
            {step === 3 && roadmapResult && (
              <div className="space-y-6">
                {/* Executive Control Header */}
                <div className="bg-white rounded-xl shadow-md border border-slate-200 p-6 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                        Workflow Generated
                      </span>
                      <span className="text-xs text-slate-500">
                        Session Thread: <code className="font-mono text-[11px] text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">{threadId?.slice(0, 8)}...</code>
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-slate-800 mt-1">
                      Interactive Approval Roadmap & Dependency Canvas
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Explorable n8n DAG canvas mapping parallel clearances, verified portals, prerequisite blockers, and authority timelines.
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setStep(1)}
                      className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-100 transition-all flex items-center space-x-1.5"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>New Assessment</span>
                    </button>
                  </div>

                  <div className="w-full mt-8">
                    <h3 className="text-lg font-bold mb-4" style={{ color: "var(--navy)" }}>Chronological Action Map</h3>
                    <div className="space-y-4">
                      {roadmapResult.ui_swimlane_data?.nodes?.map((node, idx) => {
                        const d = node.data || {};
                        const nLabel = d.label || d.name || "Unknown Action";
                        const nAuth = d.authority || "N/A";
                        const nDur = d.estimated_duration_days ? d.estimated_duration_days + " days" : "TBD";
                        const nStatus = d.status || "Pending";
                        const nMandatory = d.mandatory !== false;
                        
                        return (
                          <div key={node.id} className="gov-card flex overflow-hidden">
                            <div className="bg-slate-100 px-4 py-6 flex flex-col items-center justify-center border-r border-slate-200 min-w-[80px]">
                              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Step</span>
                              <span className="text-xl font-bold" style={{ color: "var(--navy)" }}>{(idx + 1).toString().padStart(2, '0')}</span>
                            </div>
                            <div className="p-5 flex-1">
                              <div className="flex justify-between items-start mb-2">
                                <h4 className="font-bold text-base" style={{ color: "var(--navy)" }}>{nLabel}</h4>
                                <div className="flex gap-2">
                                  {nMandatory && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-100 uppercase tracking-wider">Mandatory</span>}
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 uppercase tracking-wider">{nStatus}</span>
                                </div>
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-y-2 gap-x-4 text-sm mt-3">
                                <div><span className="text-slate-500 font-medium">Authority:</span> <span className="text-slate-800 font-semibold">{nAuth}</span></div>
                                <div><span className="text-slate-500 font-medium">Est. Time:</span> <span className="text-slate-800 font-semibold">{nDur}</span></div>
                                {d.why_required && <div className="md:col-span-2 mt-1"><span className="text-slate-500 font-medium">Description:</span> <span className="text-slate-700 leading-relaxed">{d.why_required}</span></div>}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Interactive Workflow Canvas (Restored) */}
                <WorkflowCanvas uiData={roadmapResult.ui_swimlane_data} />
              </div>
            )}
            </div>
          </div>
        )}

        {/* TAB 2: DOCUMENT PRE-VALIDATION */}
        {activeTab === 'validation' && (
          <div className="bg-white rounded-xl shadow-md border border-slate-200 p-8 max-w-3xl mx-auto">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-800">Autonomous Document Pre-Validation</h2>
              <p className="text-sm text-slate-500 mt-1">
                Upload or paste drafted text from application forms and blueprints to screen for missing fields.
              </p>
            </div>

            <form onSubmit={handleValidateDoc} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Extracted Document / Form Text
                </label>
                <textarea
                  rows="6"
                  className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all font-mono"
                  placeholder="Paste document text or form mock data here..."
                  value={docText}
                  onChange={(e) => setDocText(e.target.value)}
                />
              </div>
              {validating && <AgentThinkingStatus phase="validate" />}
              <button
                type="submit"
                disabled={validating}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-3 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {validating ? <span>Screening Document with Vision AI...</span> : <span>Run Pre-Validation Check</span>}
              </button>
            </form>

            {validationReport && (
              <div className="mt-8 bg-slate-50 p-5 rounded-lg border border-slate-200">
                <h3 className="font-semibold text-slate-800 mb-3 text-sm">Validation Report Card</h3>
                <div className="text-sm text-slate-700 whitespace-pre-line bg-white p-4 rounded border border-slate-200 font-mono">
                  {validationReport}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
      <Footer onNavigate={() => {}} />
    </div>
  );
}

export default function App() {
  const [currentRoute, setCurrentRoute] = useState(window.location.pathname === '/workflow' ? '/workflow' : '/');

  useEffect(() => {
    const handlePopState = () => {
      setCurrentRoute(window.location.pathname === '/workflow' ? '/workflow' : '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleStartWorkflow = () => {
    window.history.pushState({}, '', '/workflow');
    setCurrentRoute('/workflow');
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleGoHome = () => {
    window.history.pushState({}, '', '/');
    setCurrentRoute('/');
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (currentRoute === '/') {
    return (
      <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
        <Header step={0} onNavigate={(s) => { if(s > 0) handleStartWorkflow() }} onGoHome={handleGoHome} />
        <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <Home onStart={handleStartWorkflow} />
        </main>
        <Footer onNavigate={(s) => { if(s > 0) handleStartWorkflow() }} />
      </div>
    );
  }

  return <WorkflowApp onGoHome={handleGoHome} />;
}

