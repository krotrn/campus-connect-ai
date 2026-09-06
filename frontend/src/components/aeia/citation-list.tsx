"use client";

import * as React from "react";
import { Code2 } from "lucide-react";
import { SourceCitation } from "@/types/aeia";

interface CitationListProps {
  sources: SourceCitation[];
  onSelectCitation: (citation: SourceCitation) => void;
}

export function CitationList({ sources, onSelectCitation }: CitationListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-auto pt-4 border-t border-border/60">
      <h4 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
        <Code2 className="size-3.5 text-emerald-400" />
        <span>Verified Source Citations ({sources.length})</span>
      </h4>
      <div className="flex flex-wrap gap-2">
        {sources.map((s, idx) => {
          const range =
            s.start_line && s.end_line
              ? `#L${s.start_line}-L${s.end_line}`
              : "";
          return (
            <button
              key={s.chunk_id || idx}
              type="button"
              onClick={() => onSelectCitation(s)}
              className="flex items-center gap-1.5 rounded-md border border-border bg-slate-950 px-2.5 py-1 font-mono text-xs text-slate-300 hover:border-emerald-500/60 hover:bg-slate-800 transition"
              title="Click to view code snippet"
            >
              <span className="text-[10px] text-emerald-400 font-bold">
                #{idx + 1}
              </span>
              <span className="truncate max-w-xs">{s.file_path}</span>
              {range && (
                <span className="text-[10px] text-muted-foreground">
                  {range}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

