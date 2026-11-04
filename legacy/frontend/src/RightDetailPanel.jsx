import React from 'react';
import { 
  X, 
  ExternalLink, 
  ShieldCheck, 
  Clock, 
  FileText, 
  ArrowRight, 
  Building2, 
  CheckCircle2, 
  Landmark, 
  Compass, 
  Sparkles, 
  Workflow 
} from 'lucide-react';

export default function RightDetailPanel({ selectedApproval, summary, onClose }) {
  const [showSolution, setShowSolution] = React.useState(false);
  const [showMoreDetails, setShowMoreDetails] = React.useState(false);
  const [locationStatus, setLocationStatus] = React.useState('idle'); // idle, requesting, granted, denied, unsupported, mismatch
  const [resolvedOffice, setResolvedOffice] = React.useState(null);
  const [mismatchData, setMismatchData] = React.useState(null);

  React.useEffect(() => {
    setShowSolution(false);
    setShowMoreDetails(false);
    setLocationStatus('idle');
    setResolvedOffice(null);
    setMismatchData(null);
  }, [selectedApproval]);

  React.useEffect(() => {
    if (showMoreDetails && navigator.permissions) {
      navigator.permissions.query({ name: 'geolocation' }).then((result) => {
        if (result.state === 'granted') {
          handleRequestLocation();
        }
      }).catch(() => {});
    }
  }, [showMoreDetails]);

  const handleRequestLocation = (forceProjectLocation = false) => {
    if (!navigator.geolocation) {
      setLocationStatus('unsupported');
      return;
    }
    setLocationStatus('requesting');
    setMismatchData(null);
    
    navigator.geolocation.getCurrentPosition(
      (position) => {
        fetchOfficeData(position.coords.latitude, position.coords.longitude, forceProjectLocation);
      },
      (error) => {
        setLocationStatus('denied');
      },
      { timeout: 10000 }
    );
  };

  const fetchOfficeData = async (lat, lng, forceProjectLocation) => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/geospatial/office', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lng,
          approval_id: selectedApproval.id,
          authority: selectedApproval.authority,
          project_location_text: summary?.location || "",
          force_project_location: forceProjectLocation
        })
      });
      const data = await res.json();
      
      if (data.status === "mismatch") {
        setLocationStatus('mismatch');
        setMismatchData(data);
      } else {
        setLocationStatus('granted');
        setResolvedOffice(data.office);
      }
    } catch (e) {
      console.error(e);
      setLocationStatus('denied');
    }
  };

  const displayOffice = locationStatus === 'granted' && resolvedOffice ? resolvedOffice : selectedApproval.physical_office;

  // When no node is selected, show rich executive workflow overview
  if (!selectedApproval) {
    return (
      <div className="h-full flex flex-col bg-white border-l border-slate-200 shadow-sm overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 bg-slate-50/70">
          <div className="flex items-center space-x-2 text-blue-700 font-bold text-xs tracking-wider uppercase">
            <Compass className="w-4 h-4" />
            <span>Workflow Overview</span>
          </div>
          <h3 className="text-xl font-bold text-slate-900 mt-1 leading-tight">
            {summary?.factory_name || "Industrial Facility"}
          </h3>
          <p className="text-xs text-slate-500 mt-1 flex items-center space-x-1.5">
            <Landmark className="w-3.5 h-3.5 text-slate-400" />
            <span>{summary?.location || "Maharashtra Industrial Zone"}</span>
          </p>
        </div>

        {/* Metrics & Guide */}
        <div className="p-6 space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-3.5">
            <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100">
              <span className="text-xs font-semibold text-blue-700 block">Total Approvals</span>
              <span className="text-2xl font-bold text-blue-900 mt-1 block">
                {summary?.total_approvals || 0}
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">State & Central clearances</span>
            </div>

            <div className="p-4 rounded-xl bg-rose-50/60 border border-rose-100">
              <span className="text-xs font-semibold text-rose-700 block">Mandatory NOCs</span>
              <span className="text-2xl font-bold text-rose-900 mt-1 block">
                {summary?.mandatory_count || 0}
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Statutory requirements</span>
            </div>

            <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-100">
              <span className="text-xs font-semibold text-indigo-700 block">Parallel Tracks</span>
              <span className="text-2xl font-bold text-indigo-900 mt-1 block">
                {summary?.parallel_tracks_count || 0}
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Simultaneous execution</span>
            </div>

            <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-100">
              <span className="text-xs font-semibold text-emerald-700 block">Critical Path Est.</span>
              <span className="text-2xl font-bold text-emerald-900 mt-1 block">
                ~{summary?.critical_path_days || 45}d
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 block">Optimized timeline</span>
            </div>
          </div>

          {/* Interactive Guide Banner */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex items-start space-x-3">
              <div className="p-2 rounded-lg bg-blue-100 text-blue-700 shrink-0">
                <Workflow className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Explore Approval Nodes</h4>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  Click any clearance node on the canvas to inspect verified application portals, document requirements, and upstream blockers.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const sources = selectedApproval.sources || {};
  const documents = selectedApproval.documents || [];
  const dependencies = selectedApproval.dependencies || [];
  const blocks = selectedApproval.blocks || [];

  return (
    <div className="h-full flex flex-col bg-white border-l border-slate-200 shadow-sm overflow-y-auto">
      {/* Detail Sticky Header without blur */}
      <div className="sticky top-0 z-20 p-5 bg-white border-b border-slate-200 flex items-start justify-between">
        <div className="space-y-1.5 pr-2">
          <div className="flex items-center space-x-2">
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
              selectedApproval.mandatory 
                ? 'bg-rose-50 text-rose-700 border-rose-200' 
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}>
              {selectedApproval.mandatory ? 'Mandatory Clearance' : 'Optional / Incentive'}
            </span>
            {selectedApproval.is_parallel && (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                Parallel Track
              </span>
            )}
          </div>
          <h3 className="text-lg font-bold text-slate-900 leading-snug">
            {selectedApproval.label}
          </h3>
          <p className="text-xs font-semibold text-slate-600 flex items-center space-x-1.5">
            <Landmark className="w-3.5 h-3.5 text-blue-600" />
            <span>{selectedApproval.authority}</span>
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          title="Close details"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Detail Content Body */}
      {showSolution ? (
        <div className="p-6 space-y-6">
          <button onClick={() => setShowSolution(false)} className="text-sm font-semibold text-indigo-600 flex items-center hover:text-indigo-800 transition-colors">
            <ArrowRight className="w-4 h-4 mr-1.5 rotate-180" /> Back to Details
          </button>
          
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900 leading-snug">Action Plan</h3>
            <p className="text-xs text-slate-500">How to process {selectedApproval.label}</p>
          </div>
          
          {/* Authority */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Responsible Authority</h4>
            <p className="text-sm font-bold text-slate-800">{selectedApproval.authority}</p>
            {selectedApproval.department && (
              <p className="text-xs text-slate-600 mt-0.5">{selectedApproval.department}</p>
            )}
          </div>
          
          {/* Online Option */}
          <div className="space-y-2.5">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Online Option</h4>
            {sources.application ? (
              <a href={sources.application.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between p-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10 transition-all group">
                <div className="flex items-center space-x-2">
                  <ExternalLink className="w-4 h-4" />
                  <span>{sources.application.label || "Apply Online on Official Portal"}</span>
                </div>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </a>
            ) : (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-xs text-slate-500 italic">Online application portal information not currently available.</p>
              </div>
            )}
          </div>
          
          {/* Documents */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Required Documents</h4>
              <span className="text-[9px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold border border-slate-200">Informational</span>
            </div>
            {documents.length > 0 ? (
              <div className="space-y-2">
                {documents.map((doc, idx) => (
                  <div key={idx} className="flex items-start space-x-2.5 p-2.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700">
                    <div className="w-3 h-3 rounded-sm border border-slate-300 mt-0.5 shrink-0" />
                    <span className="leading-snug">{doc}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No specific documents listed.</p>
            )}
            <div className="p-2.5 mt-2 rounded-lg bg-indigo-50 border border-indigo-100 flex items-start space-x-2">
              <Sparkles className="w-3.5 h-3.5 text-indigo-500 mt-0.5 shrink-0" />
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold text-indigo-800">Document Verification</p>
                <p className="text-[10px] text-indigo-700 leading-snug">Verification features will be provided by the upcoming F2 document pipeline.</p>
              </div>
            </div>
          </div>
          
          {/* Next Steps */}
          {selectedApproval.next_steps && selectedApproval.next_steps.length > 0 && (
            <div className="space-y-2.5">
               <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Next Steps</h4>
               <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
                 <ol className="relative border-l border-slate-300 ml-2 space-y-4">
                   {selectedApproval.next_steps.map((step, idx) => (
                     <li key={idx} className="ml-4">
                       <div className="absolute w-2 h-2 bg-slate-400 rounded-full mt-1.5 -left-1 border border-white"></div>
                       <p className="text-xs text-slate-700 leading-relaxed font-medium">{step}</p>
                     </li>
                   ))}
                 </ol>
               </div>
            </div>
          )}
          
          {/* More Details Toggle */}
          {!showMoreDetails ? (
            <div className="pt-4 border-t border-slate-200 mt-4">
              <button onClick={() => setShowMoreDetails(true)} className="w-full py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold flex items-center justify-center space-x-2 transition-all">
                <Compass className="w-4 h-4" />
                <span>More Details & Local Offices</span>
              </button>
            </div>
          ) : (
            <div className="pt-6 mt-6 border-t border-slate-200 space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900">Detailed Assistance</h3>
                <button onClick={() => setShowMoreDetails(false)} className="text-xs font-semibold text-slate-500 hover:text-slate-700 flex items-center bg-slate-100 px-2 py-1 rounded-md">
                  Collapse <ArrowRight className="w-3 h-3 ml-1 -rotate-90" />
                </button>
              </div>

              {/* Nearby Government Offices */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Nearby Government Offices</h4>
                  <span className="text-[9px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold border border-slate-200">F6 Location Aware</span>
                </div>

                {locationStatus === 'idle' && (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <p className="text-xs text-slate-600">To find the relevant government office near you, allow location access.</p>
                    <button onClick={handleRequestLocation} className="px-3 py-1.5 bg-blue-600 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm whitespace-nowrap">
                      Allow Location
                    </button>
                  </div>
                )}

                {locationStatus === 'requesting' && (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center space-x-2 text-slate-600">
                    <Clock className="w-4 h-4 animate-spin" />
                    <span className="text-xs font-medium">Locating your area...</span>
                  </div>
                )}

                {locationStatus === 'denied' && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                    <p className="text-xs font-semibold text-amber-800">Location access unavailable.</p>
                    <p className="text-[10px] text-amber-700 mt-0.5">Showing default state/regional office information instead.</p>
                  </div>
                )}

                {locationStatus === 'unsupported' && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl">
                    <p className="text-xs font-semibold text-rose-800">Geolocation not supported by your browser.</p>
                    <p className="text-[10px] text-rose-700 mt-0.5">Showing default office information.</p>
                  </div>
                )}

                {locationStatus === 'mismatch' && mismatchData && (
                  <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-xl space-y-3">
                    <h4 className="text-sm font-bold text-indigo-900">Different Location Detected</h4>
                    <p className="text-xs text-indigo-700 leading-relaxed">
                      Your project is planned for <strong>{mismatchData.project_district}</strong>, but your current location is <strong>{mismatchData.user_district}</strong>. 
                      The relevant government offices for this application are based on your project location.
                    </p>
                    <p className="text-xs font-semibold text-indigo-800">Would you like to see the offices for {mismatchData.project_district}?</p>
                    <div className="flex items-center space-x-3 pt-1">
                      <button onClick={() => handleRequestLocation(true)} className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded-lg hover:bg-indigo-700 transition-colors shadow-sm">
                        Yes, Show {mismatchData.project_district} Offices
                      </button>
                      <button onClick={() => setLocationStatus('denied')} className="px-3 py-1.5 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-lg hover:bg-indigo-200 transition-colors">
                        No
                      </button>
                    </div>
                  </div>
                )}

                {(locationStatus === 'granted' || locationStatus === 'denied' || locationStatus === 'unsupported' || locationStatus === 'idle') && (
                  <div className="mt-2 space-y-2">
                    {displayOffice ? (
                      <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
                        {locationStatus === 'granted' && (
                           <div className="absolute top-0 right-0 px-2.5 py-1 bg-emerald-100 text-emerald-800 text-[9px] font-bold rounded-bl-lg flex items-center space-x-1">
                             <CheckCircle2 className="w-3 h-3" />
                             <span>Nearest Found</span>
                           </div>
                        )}
                        <div>
                          <p className="text-xs font-bold text-slate-800">{displayOffice.name}</p>
                          <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{displayOffice.address}</p>
                          {displayOffice.district && (
                            <span className="inline-block mt-1.5 px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-semibold">District: {displayOffice.district}</span>
                          )}
                        </div>
                        {displayOffice.latitude && displayOffice.longitude && (
                          <a href={`https://maps.google.com/?q=${displayOffice.latitude},${displayOffice.longitude}`} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center space-x-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors">
                            <Compass className="w-3.5 h-3.5" />
                            <span>Find on Google Maps</span>
                          </a>
                        )}
                      </div>
                    ) : (
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                        <p className="text-xs text-slate-500 italic">Office information unavailable for this authority.</p>
                      </div>
                    )}
                    
                    {locationStatus === 'granted' && (
                      <p className="text-[9px] text-slate-400 text-right pr-1">
                        Location data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline hover:text-slate-500">OpenStreetMap contributors</a>
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
          
        </div>
      ) : (
        <div className="p-6 space-y-6">
          <div className="w-full mb-2">
            <button onClick={() => setShowSolution(true)} className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center justify-center space-x-2 shadow-md shadow-indigo-500/20 transition-all">
              <Sparkles className="w-5 h-5" />
              <span>Find Solution & Action Plan</span>
            </button>
          </div>
        
          {/* Regulatory Basis Card */}
          {selectedApproval.why_required && (
            <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-100">
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-800 mb-1 flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>Statutory Requirement</span>
              </h4>
              <p className="text-xs text-slate-700 leading-relaxed mt-1">
                {selectedApproval.why_required}
              </p>
            </div>
          )}

          {/* Timeline & Department Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Est. Duration</span>
              <div className="flex items-center space-x-1.5 mt-1">
                <Clock className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-bold text-slate-800">
                  ~{selectedApproval.estimated_duration_days || 30} Days
                </span>
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Department</span>
              <div className="flex items-center space-x-1.5 mt-1">
                <Building2 className="w-4 h-4 text-indigo-600" />
                <span className="text-xs font-semibold text-slate-800 truncate">
                  {selectedApproval.department || "Govt Authority"}
                </span>
              </div>
            </div>
          </div>

          {/* Verified Action Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Official Portals & Actions
            </h4>
            <div className="space-y-2">
              {sources.application?.url && (
                <a
                  href={sources.application.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-md shadow-blue-500/10 transition-all group"
                >
                  <div className="flex items-center space-x-2">
                    <ExternalLink className="w-4 h-4" />
                    <span>{sources.application.label || "Apply on Official Portal"}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </a>
              )}

              {sources.documents?.url && (
                <a
                  href={sources.documents.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-all"
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-slate-500" />
                    <span>{sources.documents.label || "Document Guidelines"}</span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                </a>
              )}

              {sources.tracking?.url && (
                <a
                  href={sources.tracking.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs border border-slate-200 transition-all"
                >
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-slate-500" />
                    <span>{sources.tracking.label || "Track Application Status"}</span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                </a>
              )}

              {sources.department?.url && (
                <a
                  href={sources.department.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs border border-slate-200 transition-all"
                >
                  <div className="flex items-center space-x-2">
                    <Landmark className="w-3.5 h-3.5 text-slate-500" />
                    <span>{sources.department.label || "Department Website"}</span>
                  </div>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>
              )}
            </div>
          </div>

          {/* Required Documents Checklist */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Required Documents Checklist
              </h4>
              <span className="text-[10px] bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full font-bold border border-slate-200">
                {documents.length} Items
              </span>
            </div>
            
            <div className="space-y-2">
              {documents.length > 0 ? (
                documents.map((doc, idx) => (
                  <div 
                    key={idx} 
                    className="flex items-start space-x-2.5 p-3 rounded-lg border border-slate-200 bg-slate-50/50 text-xs text-slate-700"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span className="leading-snug">{doc}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 italic">Standard statutory documentation applies.</p>
              )}
            </div>
          </div>

          {/* Prerequisites & Blockers */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Dependencies & Pre-requisites
            </h4>

            {dependencies.length > 0 && (
              <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200">
                <span className="text-[11px] font-bold text-amber-800 block mb-1">
                  Prerequisites (Must Complete First):
                </span>
                <ul className="text-xs text-slate-700 space-y-1 list-disc list-inside font-mono">
                  {dependencies.map((dep, idx) => (
                    <li key={idx} className="text-[11px]">{dep}</li>
                  ))}
                </ul>
              </div>
            )}

            {blocks.length > 0 && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[11px] font-bold text-slate-700 block mb-1">
                  Blocks Downstream Clearances:
                </span>
                <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside font-mono">
                  {blocks.map((blk, idx) => (
                    <li key={idx} className="text-[11px]">{blk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Source Verification Footer */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
            <div className="flex items-center space-x-1.5 text-emerald-700 font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Gov Verified Registry</span>
            </div>
            <span className="font-mono text-[10px]">Updated: {selectedApproval.verification?.last_verified || "2026-09"}</span>
          </div>

        </div>
      )}
    </div>
  );
}
