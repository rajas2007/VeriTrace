import React from "react";

export function App() {
  return (
    <div className="flex h-screen w-screen flex-col bg-slate-950 text-slate-100">
      <header className="flex h-12 items-center justify-between border-b border-slate-800 px-4 bg-slate-900/60 backdrop-blur">
        <div className="flex items-center space-x-2">
          <span className="font-bold tracking-wider text-emerald-400">VERITRACE</span>
          <span className="text-xs text-slate-400">Desktop Forensics</span>
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">VeriTrace Investigation Workstation</h1>
          <p className="mt-2 text-sm text-slate-400">Desktop architecture initialized. Ready for Milestone 0 integration.</p>
        </div>
      </main>
    </div>
  );
}

export default App;
