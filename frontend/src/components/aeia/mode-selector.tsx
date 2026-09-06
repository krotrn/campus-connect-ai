"use client";

import * as React from "react";
import { ExecutionMode } from "@/types/aeia";

interface ModeSelectorProps {
  mode: ExecutionMode;
  onChange: (mode: ExecutionMode) => void;
  disabled?: boolean;
}

export function ModeSelector({ mode, onChange, disabled }: ModeSelectorProps) {
  return (
    <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm">
      <label className="block text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
        Execution Mode
      </label>
      <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-slate-950 p-1">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange("rag")}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
            mode === "rag"
              ? "bg-emerald-500 text-slate-950 font-semibold shadow-sm"
              : "text-muted-foreground hover:text-white"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          Hybrid RAG
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange("agent")}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
            mode === "agent"
              ? "bg-indigo-500 text-white font-semibold shadow-sm"
              : "text-muted-foreground hover:text-white"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          LangGraph Agent
        </button>
      </div>
      <p className="mt-2.5 text-[11px] text-muted-foreground leading-relaxed">
        {mode === "rag"
          ? "Direct 70/30 Dense (FastEmbed) + BM25Okapi RRF search fused with Gemini streaming."
          : "LangGraph State Graph routing dynamically across Git history, diffs, dependency scans, and RAG."}
      </p>
    </div>
  );
}

