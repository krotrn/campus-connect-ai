"use client";

import * as React from "react";
import { AlertTriangle, KeyRound, Sparkles, Eye, EyeOff, Check, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredGeminiApiKey, setStoredGeminiApiKey } from "@/lib/settings";

interface QuotaAlertProps {
  onRetry: () => void;
  onOpenSettings?: () => void;
}

export function QuotaAlert({ onRetry, onOpenSettings }: QuotaAlertProps) {
  const [apiKey, setApiKey] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    setApiKey(getStoredGeminiApiKey());
  }, []);

  const handleSaveAndRetry = (e?: React.SubmitEvent) => {
    if (e) e.preventDefault();
    const cleanKey = apiKey.trim();
    if (!cleanKey) return;
    setStoredGeminiApiKey(cleanKey);
    setSaved(true);
    setTimeout(() => {
      onRetry();
    }, 200);
  };

  return (
    <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs text-amber-200 shadow-lg backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-200">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="size-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-amber-100 text-sm flex items-center gap-2">
              <span>Upstream AI Quota Exceeded (HTTP 429)</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Action Required
              </span>
            </h3>
            <p className="text-xs text-amber-300/90 mt-1 leading-relaxed">
              The Gemini generation quota on the server has been reached. Grounded context chunks were retrieved, but synthesis requires an active key. Provide your personal Gemini API key to generate the answer immediately using your own quota.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSaveAndRetry} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 pt-2 border-t border-amber-500/20">
        <div className="relative flex-1">
          <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-amber-400/70" />
          <Input
            type={showPassword ? "text" : "password"}
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              setSaved(false);
            }}
            placeholder="Paste your Gemini API key (e.g. AIzaSy...)"
            className="pl-9 pr-8 bg-slate-950/90 border-amber-500/40 text-xs text-amber-100 placeholder:text-amber-400/40 focus-visible:ring-amber-500/50 h-9"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-amber-400/60 hover:text-amber-200 transition"
            title={showPassword ? "Hide API key" : "Show API key"}
          >
            {showPassword ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
          </button>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            type="submit"
            size="sm"
            disabled={!apiKey.trim()}
            className="h-9 text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold gap-1.5 shadow-sm transition disabled:opacity-50"
          >
            {saved ? (
              <>
                <Check className="size-3.5" />
                <span>Saved & Retrying...</span>
              </>
            ) : (
              <>
                <Sparkles className="size-3.5" />
                <span>Use Key & Regenerate</span>
              </>
            )}
          </Button>

          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noreferrer"
            className="h-9 px-3 text-xs inline-flex items-center gap-1 text-amber-300 hover:text-amber-100 hover:underline transition"
          >
            <span>Get free key</span>
            <ExternalLink className="size-3" />
          </a>
        </div>
      </form>
    </div>
  );
}

