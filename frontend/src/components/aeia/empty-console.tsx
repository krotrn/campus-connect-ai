"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";

export function EmptyConsole() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-muted-foreground">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-3 shadow-inner">
        <Sparkles className="size-7" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200 mb-1">
        AEIA Engineering Intelligence Console
      </h3>
      <p className="text-xs max-w-md leading-relaxed">
        Type an engineering question above or pick one of the example queries to inspect real grounded code citations, dependency linkages, or git diffs.
      </p>
    </div>
  );
}

