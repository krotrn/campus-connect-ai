"use client";

import * as React from "react";
import Link from "next/link";
import { siteConfig } from "@/config/site";
import { buttonVariants } from "@/components/ui/button";
import { Zap, Settings, RefreshCw, Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Code } from "lucide-react";
import { aeiaService } from "@/services/aeia.service";
import { SettingsDialog } from "@/components/aeia/settings-dialog";

export function Header() {
interface HeaderProps {
  onResetChat?: () => void;
}

export function Header({ onResetChat }: HeaderProps) {
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [healthStatus, setHealthStatus] = React.useState<{
    state: "loading" | "healthy" | "degraded" | "offline";
    points?: number;
    message?: string;
  }>({ state: "loading" });

  const fetchHealth = React.useCallback(async () => {
    try {
      const res = await aeiaService.checkHealth();
      const points = res.points_indexed ?? res.indexed_points ?? 0;
      setHealthStatus({
        state: "healthy",
        points,
      });
    } catch {
      setHealthStatus({
        state: "offline",
        message: "Backend offline",
      });
    }
  }, []);

  React.useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-extrabold shadow-sm">
              IH
    <>
      <header className="sticky top-0 z-40 w-full border-b border-border/40 bg-slate-950/80 backdrop-blur supports-[backdrop-filter]:bg-slate-950/60">
        <div className="container mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold shadow-sm">
                <Zap className="size-4" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-white">AEIA</span>
                <Badge variant="outline" className="text-[10px] border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono py-0 px-1.5">
                  v0.4.0
                </Badge>
              </div>
            </Link>
            <span className="hidden md:inline text-xs text-muted-foreground border-l border-border pl-3">
              Engineering Intelligence for Campus Connect (~94k LOC)
            </span>
            <span>{siteConfig.name}</span>
          </Link>
          <Badge variant="secondary" className="hidden sm:inline-flex gap-1 items-center font-medium">
            <Sparkles className="size-3 text-amber-500" /> Next.js 16 + shadcn/ui
          </Badge>
          </div>

          {/* Right Action Bar */}
          <div className="flex items-center gap-2.5 text-xs">
            {/* Health Status Indicator */}
            <div
              onClick={fetchHealth}
              title="Click to recheck health"
              className="cursor-pointer flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-border bg-slate-900 text-muted-foreground hover:text-slate-200 transition"
            >
              {healthStatus.state === "healthy" ? (
                <>
                  <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[11px] text-emerald-300 font-medium">
                    Qdrant Healthy ({healthStatus.points?.toLocaleString()} chunks)
                  </span>
                </>
              ) : healthStatus.state === "loading" ? (
                <>
                  <span className="size-2 rounded-full bg-amber-400 animate-pulse" />
                  <span className="text-[11px] text-amber-300">Checking...</span>
                </>
              ) : (
                <>
                  <span className="size-2 rounded-full bg-rose-500" />
                  <span className="text-[11px] text-rose-300">Backend Offline</span>
                </>
              )}
            </div>

            {/* Reset / New Chat */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (onResetChat) {
                  onResetChat();
                } else if (typeof window !== "undefined") {
                  window.dispatchEvent(new CustomEvent("aeia:reset-chat"));
                }
              }}
              className="h-7 px-2.5 text-xs gap-1.5 border-border bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white"
              title="Start a fresh conversation"
            >
              <RefreshCw className="size-3" />
              <span className="hidden sm:inline">New Chat</span>
            </Button>

            {/* Settings Trigger */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSettingsOpen(true)}
              className="h-7 px-2.5 text-xs gap-1.5 border-border bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white"
              title="Backend & API Key Settings"
            >
              <Settings className="size-3.5" />
              <span className="hidden sm:inline">Settings</span>
            </Button>
          </div>
        </div>
      </header>

        <nav className="flex items-center gap-4">
          <Link
            href="#features"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Features
          </Link>
          <Link
            href="#architecture"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Architecture
          </Link>
          <Link
            href="/api/health"
            target="_blank"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Health API
          </Link>
          <a
            href={siteConfig.links.github}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline", size: "sm", className: "flex items-center gap-2" })}
          >
            <Code className="size-4" />
            <span>GitHub</span>
          </a>
        </nav>
      </div>
    </header>
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        onSettingsSaved={fetchHealth}
      />
    </>
  );
}
