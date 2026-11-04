import { useState, useEffect } from 'react';

// Phrase sets per workflow phase. Each phase corresponds to a blocking
// backend call in App.jsx (start / clarify / resume / validate).
const PHASES = {
  start: [
    'Parsing facility profile...',
    'Decoding plot, power & emissions data...',
    'Cross-referencing MPCB / MIDC regulations...',
    'Mapping PSI 2019 subsidy eligibility...',
  ],
  clarify: [
    'Re-checking facility profile...',
    'Resolving hazard-critical fields...',
    'Rebuilding compliance matrix...',
  ],
  resume: [
    'Building chronological execution roadmap...',
    'Resolving parallel dependency paths...',
    'Fetching relevant portal links...',
    'Generating swimlane visualization...',
  ],
  validate: [
    'Scanning document text...',
    'Checking for missing signatures & seals...',
    'Screening mandatory fields with Vision AI...',
  ],
};

export default function AgentThinkingStatus({ phase, intervalMs = 1800 }) {
  const [index, setIndex] = useState(0);
  const messages = phase ? PHASES[phase] : null;

  useEffect(() => {
    setIndex(0);
    if (!messages) return;
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % messages.length);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [phase, intervalMs]);

  if (!messages) return null;

  return (
    <div className="flex items-center gap-3 mb-3 px-1 text-sm text-slate-500">
      <span className="agent-wave" aria-hidden="true">
        <span></span><span></span><span></span><span></span><span></span>
      </span>
      <span key={index} className="agent-thinking-fade">
        {messages[index]}
      </span>
    </div>
  );
}