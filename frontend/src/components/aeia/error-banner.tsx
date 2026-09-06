"use client";

import * as React from "react";
import { AlertCircle, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorBannerProps {
  error: string | null;
  onOpenSettings: () => void;
}

export function ErrorBanner({ error, onOpenSettings }: ErrorBannerProps) {
  if (!error) return null;

  return (
    <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-300 flex items-start justify-between gap-3 animate-in fade-in duration-150">
      <div className="flex items-start gap-2.5">
        <AlertCircle className="size-4 text-rose-400 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-rose-200">Execution Error</p>
          <p className="text-[11px] mt-0.5">{error}</p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onOpenSettings}
        className="h-7 text-xs border-rose-500/40 hover:bg-rose-500/20 text-rose-200 gap-1 shrink-0"
      >
        <Settings className="size-3" />
        <span>Check Settings</span>
      </Button>
    </div>
  );
}

