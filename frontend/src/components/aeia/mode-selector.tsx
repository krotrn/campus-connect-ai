"use client";

import * as React from "react";

interface ModeSelectorProps {
  activeRoute?: string;
}

export function ModeSelector({ activeRoute }: ModeSelectorProps) {
  return (
    <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2.5">
        <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          Execution Engine
        </label>
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Autonomous
        </span>
      </div>

      <div className="rounded-lg border border-border bg-slate-950 p-2.5 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-medium flex items-center gap-1.5">
            <span>⚡</span> Hybrid RAG
          </span>
          <span className="text-[10px] text-muted-foreground">Dense + BM25</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-medium flex items-center gap-1.5">
            <span>📜</span> Git Commit & History
          </span>
          <span className="text-[10px] text-muted-foreground">Live Diffs</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-medium flex items-center gap-1.5">
            <span>🔗</span> Dependency Mapping
          </span>
          <span className="text-[10px] text-muted-foreground">Reverse Scans</span>
        </div>
      </div>

      <p className="mt-2.5 text-[11px] text-muted-foreground leading-relaxed">
        {activeRoute
          ? `Current Route: ${activeRoute}`
          : "Queries are autonomously classified and routed with real-time streaming."}
      </p>
    </div>
  );
}
