"use client";

import * as React from "react";
import {
  Plus,
  PanelLeftClose,
  Key,
  GitCommit,
  Share2,
  History,
  Settings,
  Zap,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { HealthResponse } from "@/types/aeia";
import { aeiaService } from "@/services/aeia.service";

interface ChatSidebarProps {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectPrompt: (prompt: string) => void;
  onOpenSettings: () => void;
  hasMessages?: boolean;
}

const PRESET_TOPICS = [
  {
    id: "auth",
    icon: Key,
    title: "Authentication Flow",
    description: "NextAuth & session middleware",
    query: "Where is user authentication and session management implemented?",
  },
  {
    id: "git-commit",
    icon: GitCommit,
    title: "Git Commit Audit",
    description: "Inspect commit diffs",
    query: "Which files changed in commit 6e19f61 and what was updated?",
  },
  {
    id: "dependencies",
    icon: Share2,
    title: "Dependency Mapping",
    description: "Reverse scan compose & imports",
    query: "What application services depend on Redis?",
  },
  {
    id: "recent-commits",
    icon: History,
    title: "Recent Commits",
    description: "Queries git repository log",
    query: "Show me the recent 5 git commits on this codebase.",
  },
];

export function ChatSidebar({
  open,
  onToggle,
  onNewChat,
  onSelectPrompt,
  onOpenSettings,
  hasMessages,
}: ChatSidebarProps) {
  const [healthStatus, setHealthStatus] = React.useState<{
    state: "loading" | "healthy" | "offline";
    points?: number;
  }>({ state: "loading" });

  const checkHealth = React.useCallback(async () => {
    try {
      const res: HealthResponse = await aeiaService.checkHealth();
      const points = res.points_indexed ?? res.indexed_points ?? 0;
      setHealthStatus({ state: "healthy", points });
    } catch {
      setHealthStatus({ state: "offline" });
    }
  }, []);

  React.useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, [checkHealth]);

  if (!open) {
    return null;
  }

  return (
    <aside className="w-72 shrink-0 h-full flex flex-col border-r border-white/8 bg-[#070709] text-zinc-200 z-30 transition-all duration-200 select-none">
      {/* Sidebar Header */}
      <div className="flex items-center justify-between p-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Zap className="size-4" />
          </div>
          <span className="font-semibold text-sm tracking-tight text-white font-mono">
            AEIA
          </span>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
            v0.4.0
          </span>
        </div>
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
          title="Close sidebar"
        >
          <PanelLeftClose className="size-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <Button
          onClick={onNewChat}
          className="w-full justify-start gap-2 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-200 hover:text-white border border-white/8 rounded-xl h-10 px-3 text-xs font-mono font-medium shadow-sm transition"
        >
          <Plus className="size-4 text-emerald-400" />
          <span>New Chat</span>
        </Button>
      </div>

      {/* Presets / Conversation Section */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
        <div>
          <div className="px-2 pb-2 text-[11px] font-medium text-zinc-500 uppercase tracking-wider flex items-center justify-between font-mono">
            <span>Capabilities</span>
            <Sparkles className="size-3 text-emerald-400/80" />
          </div>
          <div className="space-y-1">
            {PRESET_TOPICS.map((topic) => {
              const Icon = topic.icon;
              return (
                <button
                  key={topic.id}
                  onClick={() => onSelectPrompt(topic.query)}
                  className="w-full text-left p-2 rounded-lg hover:bg-zinc-900/70 transition flex items-start gap-2.5 group"
                >
                  <Icon className="size-3.5 mt-0.5 text-zinc-500 group-hover:text-emerald-400 transition-colors shrink-0" />
                  <div className="overflow-hidden">
                    <p className="text-xs text-zinc-300 group-hover:text-white truncate font-medium">
                      {topic.title}
                    </p>
                    <p className="text-[10px] text-zinc-500 truncate">
                      {topic.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {hasMessages && (
          <div className="pt-2 border-t border-white/8">
            <div className="px-2 pb-2 text-[11px] font-medium text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <Layers className="size-3 text-emerald-400/80" />
              <span>Current Session</span>
            </div>
            <div className="px-2 py-1.5 rounded-lg bg-zinc-900/50 border border-white/8 text-xs text-zinc-300 flex items-center justify-between font-mono">
              <span className="truncate">Active Conversation</span>
              <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Footer: Health & Settings */}
      <div className="p-3 border-t border-white/8 bg-[#070709] space-y-2">
        {/* Backend Status Pill */}
        <div
          onClick={checkHealth}
          title="Click to re-check backend health"
          className="cursor-pointer flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-zinc-900/60 border border-white/8 hover:bg-zinc-900 transition text-xs font-mono"
        >
          <div className="flex items-center gap-2 overflow-hidden">
            {healthStatus.state === "healthy" ? (
              <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0" />
            ) : healthStatus.state === "loading" ? (
              <Loader2 className="size-3.5 text-amber-400 animate-spin shrink-0" />
            ) : (
              <AlertCircle className="size-3.5 text-rose-400 shrink-0" />
            )}
            <span className="text-[11px] text-zinc-300 truncate">
              {healthStatus.state === "healthy"
                ? `Qdrant (${healthStatus.points?.toLocaleString() || 0} chunks)`
                : healthStatus.state === "loading"
                ? "Connecting..."
                : "Backend Offline"}
            </span>
          </div>
          <span
            className={`size-2 rounded-full shrink-0 ${
              healthStatus.state === "healthy"
                ? "bg-emerald-400 animate-pulse"
                : healthStatus.state === "loading"
                ? "bg-amber-400 animate-pulse"
                : "bg-rose-500"
            }`}
          />
        </div>

        {/* Settings Trigger */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs text-zinc-400 hover:text-white hover:bg-zinc-900 transition font-mono"
        >
          <Settings className="size-4 text-zinc-400" />
          <span className="font-medium">Backend & API Settings</span>
        </button>
      </div>
    </aside>
  );
}
