"use client";

import * as React from "react";
import { Check, Loader2, Server, KeyRound, AlertCircle, X, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getCustomApiKey,
  getCustomBackendUrl,
  getStoredGeminiApiKey,
  setCustomApiKey,
  setCustomBackendUrl,
  setStoredGeminiApiKey,
} from "@/lib/settings";
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
  // The form is a separate component mounted only while the dialog is open, so
  // its state initializes from storage on mount instead of being reset by an
  // effect on every `open` change.
  if (!open) return null;

  return (
    <SettingsDialogForm onOpenChange={onOpenChange} onSettingsSaved={onSettingsSaved} />
  );
}

function SettingsDialogForm({
  onOpenChange,
  onSettingsSaved,
}: Omit<SettingsDialogProps, "open">) {
  const [url, setUrl] = React.useState(() => getCustomBackendUrl());
  const [key, setKey] = React.useState(() => getCustomApiKey());
  const [geminiKey, setGeminiKey] = React.useState(() => getStoredGeminiApiKey());
  const [testing, setTesting] = React.useState(false);
  const [testResult, setTestResult] = React.useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await aeiaService.checkHealth(url, key);
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
    setCustomBackendUrl(url);
    setCustomApiKey(key);
    setStoredGeminiApiKey(geminiKey);
    onSettingsSaved?.();
    onOpenChange(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="flex flex-col w-full h-full sm:h-auto sm:max-w-md max-h-dvh sm:max-h-[90vh] rounded-none sm:rounded-xl border-0 sm:border border-border bg-[#0e0d0b] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 bg-[#0b0a08] px-4 sm:px-5 py-4 shrink-0">
          <div className="flex items-center gap-2">
            <Server className="size-4 text-moss-400" />
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
        <div className="p-4 sm:p-5 space-y-4 text-xs overflow-y-auto">
          <div>
            <label className="block font-medium text-stone-300 mb-1.5 flex items-center gap-1.5">
              <Server className="size-3.5 text-muted-foreground" />
              <span>FastAPI Backend URL</span>
            </label>
            <Input
              type="text"
              placeholder="Leave empty to use this app's configured backend"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="bg-[#0b0a08] border-border text-xs"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Optional. Leave empty and requests go through this app&apos;s server, which
              holds the backend key. Set a URL to call your own AEIA deployment
              directly from the browser — you must then supply its key below.
            </p>
          </div>

          <div>
            <label className="block font-medium text-stone-300 mb-1.5 flex items-center gap-1.5">
              <KeyRound className="size-3.5 text-muted-foreground" />
              <span>AEIA API Key (for a custom backend)</span>
            </label>
            <Input
              type="password"
              placeholder="Only needed with a custom backend URL"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              disabled={!url.trim()}
              className="bg-[#0b0a08] border-border text-xs disabled:opacity-50"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Only used with a custom backend URL, and sent only to that host. The
              default backend&apos;s key stays on this app&apos;s server and never
              reaches your browser.
            </p>
          </div>

          <div>
            <label className="block font-medium text-stone-300 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-amber-400" />
                <span>Google Gemini API Key (Client Quota Override)</span>
              </span>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-amber-400 hover:underline"
              >
                Get free key ↗
              </a>
            </label>
            <Input
              type="password"
              placeholder="e.g. AIzaSy..."
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="bg-[#0b0a08] border-border text-xs"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Optional. Used directly for answer synthesis whenever the backend quota is exhausted (HTTP 429).
            </p>
          </div>

          {testResult && (
            <div
              className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                testResult.success
                  ? "bg-moss-500/10 border-moss-500/30 text-moss-300"
                  : "bg-rose-500/10 border-rose-500/30 text-rose-300"
              }`}
            >
              {testResult.success ? (
                <Check className="size-4 shrink-0 text-moss-400 mt-0.5" />
              ) : (
                <AlertCircle className="size-4 shrink-0 text-rose-400 mt-0.5" />
              )}
              <span>{testResult.message}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border/60 bg-[#0b0a08]/60 px-4 sm:px-5 py-3 text-xs shrink-0 gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={testing}
            onClick={handleTestConnection}
            className="h-8 text-xs flex items-center gap-1.5 border-border hover:bg-stone-800"
          >
            {testing && <Loader2 className="size-3 animate-spin" />}
            <span>Test connection</span>
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
              className="h-8 text-xs bg-moss-500 hover:bg-moss-400 text-stone-950 font-semibold"
            >
              Save changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

