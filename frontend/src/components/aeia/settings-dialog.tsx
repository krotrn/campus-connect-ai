"use client";

import * as React from "react";
import { Check, Loader2, Server, KeyRound, AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredApiKey, getStoredBackendUrl, setStoredApiKey, setStoredBackendUrl } from "@/lib/settings";
import { aeiaService } from "@/services/aeia.service";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSettingsSaved?: () => void;
}

export function SettingsDialog({
  open,
  onOpenChange,
  onSettingsSaved,
}: SettingsDialogProps) {
  const [url, setUrl] = React.useState("");
  const [key, setKey] = React.useState("");
  const [testing, setTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState<{
    success: boolean;
    message: string;
  } | null>(null);

  React.useEffect(() => {
    if (open) {
      setUrl(getStoredBackendUrl());
      setKey(getStoredApiKey());
      setTestResult(null);
    }
  }, [open]);

  if (!open) return null;

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await aeiaService.checkHealth(url);
      setTestResult({
        success: true,
        message: `Connected! Qdrant status: ${res.status} (${res.points_indexed ?? res.indexed_points ?? 0} points indexed)`,
      });
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "Failed to connect to backend",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    setStoredBackendUrl(url);
    setStoredApiKey(key);
    onSettingsSaved?.();
    onOpenChange(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="flex flex-col w-full max-w-md rounded-xl border border-border bg-slate-900 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 bg-slate-950 px-5 py-4">
          <div className="flex items-center gap-2">
            <Server className="size-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-foreground">Backend Configuration</h2>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="rounded p-1 text-muted-foreground hover:text-foreground transition"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-5 space-y-4 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Server className="size-3.5 text-muted-foreground" />
              <span>FastAPI Backend URL</span>
            </label>
            <Input
              type="text"
              placeholder="e.g. https://aeia-api.up.railway.app or http://localhost:8000"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="bg-slate-950 border-border text-xs"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Your deployed AEIA FastAPI backend URL (on Railway, Render, Fly, or local).
            </p>
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
              <KeyRound className="size-3.5 text-muted-foreground" />
              <span>AEIA API Key (`X-API-Key`)</span>
            </label>
            <Input
              type="password"
              placeholder="e.g. dev-key-change-me"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="bg-slate-950 border-border text-xs"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Must match the `API_KEY` configured on your backend server.
            </p>
          </div>

          {testResult && (
            <div
              className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                testResult.success
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-300"
              }`}
            >
              {testResult.success ? (
                <Check className="size-4 shrink-0 text-emerald-400 mt-0.5" />
              ) : (
                <AlertCircle className="size-4 shrink-0 text-rose-400 mt-0.5" />
              )}
              <span>{testResult.message}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border/60 bg-slate-950/60 px-5 py-3 text-xs">
          <Button
            size="sm"
            variant="outline"
            disabled={testing || !url}
            onClick={handleTestConnection}
            className="h-8 text-xs flex items-center gap-1.5 border-border hover:bg-slate-800"
          >
            {testing && <Loader2 className="size-3 animate-spin" />}
            <span>Test Connection</span>
          </Button>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="h-8 text-xs text-muted-foreground"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              className="h-8 text-xs bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold"
            >
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

