"use client";

import * as React from "react";
import { TelemetryData } from "@/types/aeia";
import { Gauge, Clock, Layers, Cpu } from "lucide-react";

interface TelemetryBarProps {
  telemetry: TelemetryData | null;
}

export function TelemetryBar({ telemetry }: TelemetryBarProps) {
  if (!telemetry) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3 animate-in fade-in duration-200">
      <div className="rounded-lg border border-border/60 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
        <Gauge className="size-4 text-emerald-400 shrink-0" />
        <div className="overflow-hidden">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block truncate">
            Route
          </span>
          <span className="text-xs font-semibold text-emerald-400 truncate block">
            {telemetry.route}
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-border/60 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
        <Clock className="size-4 text-blue-400 shrink-0" />
        <div className="overflow-hidden">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block truncate">
            Latency
          </span>
          <span className="text-xs font-semibold text-slate-200 truncate block">
            {telemetry.latency}
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-border/60 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
        <Layers className="size-4 text-indigo-400 shrink-0" />
        <div className="overflow-hidden">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block truncate">
            Citations
          </span>
          <span className="text-xs font-semibold text-slate-200 truncate block">
            {telemetry.chunks} chunks
          </span>
        </div>
      </div>

      <div className="rounded-lg border border-border/60 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
        <Cpu className="size-4 text-amber-400 shrink-0" />
        <div className="overflow-hidden">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block truncate">
            Model
          </span>
          <span className="text-xs font-semibold text-slate-200 truncate block">
            {telemetry.model}
          </span>
        </div>
      </div>
    </div>
  );
}

