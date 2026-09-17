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
import { useAeiaHealthStatus } from "@/hooks/queries/use-aeia-health";
import { useMediaQuery } from "@/hooks/use-media-query";

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
  // Polling, retries, and cleanup are handled by React Query.
  const { status: healthStatus, refetch: checkHealth } = useAeiaHealthStatus();
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  if (!open) {
    return null;
  }

  // Below the lg breakpoint the sidebar becomes an overlay drawer (fixed +
  // backdrop) instead of the persistent inline panel used on desktop, since
  // its w-72 width would otherwise crush the chat column on a phone.
  const handleSelectPrompt = (prompt: string) => {
    onSelectPrompt(prompt);
    if (!isDesktop) onToggle();
  };

  const handleNewChat = () => {
    onNewChat();
    if (!isDesktop) onToggle();
  };

  return (
    <>
      {!isDesktop && (
        <div
          className="fixed inset-0 z-40 bg-black/60 animate-in fade-in duration-200"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}
      <aside
        className={`${
          isDesktop ? "relative" : "fixed inset-y-0 left-0 animate-in slide-in-from-left duration-200"
        } w-72 max-w-[85vw] shrink-0 h-full flex flex-col border-r border-white/8 bg-[#070604] text-stone-200 z-50 select-none`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-3 border-b border-white/8">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-lg bg-moss-500/10 border border-moss-500/20 text-moss-400">
              <Zap className="size-4" />
            </div>
            <span className="font-semibold text-sm tracking-tight text-white font-mono">
              AEIA
            </span>
            <span className="text-[10px] font-mono text-moss-400 bg-moss-500/10 px-1.5 py-0.5 rounded border border-moss-500/20">
              v0.4.0
            </span>
          </div>
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg text-stone-400 hover:text-white hover:bg-stone-900 transition"
            title="Close sidebar"
          >
            <PanelLeftClose className="size-4" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Button
            onClick={handleNewChat}
            className="w-full justify-start gap-2 bg-stone-900/80 hover:bg-stone-800 text-stone-200 hover:text-white border border-white/8 rounded-xl h-10 px-3 text-xs font-mono font-medium shadow-sm transition"
          >
            <Plus className="size-4 text-moss-400" />
            <span>New Chat</span>
          </Button>
        </div>

        {/* Presets / Conversation Section */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
          <div>
            <div className="px-2 pb-2 text-[11px] font-medium text-stone-500 flex items-center justify-between font-mono">
              <span>Capabilities</span>
              <Sparkles className="size-3 text-moss-400/80" />
            </div>
            <div className="space-y-1">
              {PRESET_TOPICS.map((topic) => {
                const Icon = topic.icon;
                return (
                  <button
                    key={topic.id}
                    onClick={() => handleSelectPrompt(topic.query)}
                    className="w-full text-left p-2 rounded-lg hover:bg-stone-900/70 transition flex items-start gap-2.5 group"
                  >
                    <Icon className="size-3.5 mt-0.5 text-stone-500 group-hover:text-moss-400 transition-colors shrink-0" />
                    <div className="overflow-hidden">
                      <p className="text-xs text-stone-300 group-hover:text-white truncate font-medium">
                        {topic.title}
                      </p>
                      <p className="text-[10px] text-stone-500 truncate">
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
              <div className="px-2 pb-2 text-[11px] font-medium text-stone-500 flex items-center gap-1.5 font-mono">
                <Layers className="size-3 text-moss-400/80" />
                <span>Current session</span>
              </div>
              <div className="px-2 py-1.5 rounded-lg bg-stone-900/50 border border-white/8 text-xs text-stone-300 flex items-center justify-between font-mono">
                <span className="truncate">Active conversation</span>
                <span className="size-2 rounded-full bg-moss-400 animate-pulse" />
              </div>
            </div>
          )}
        </div>

        {/* Sidebar Footer: Health & Settings */}
        <div className="p-3 border-t border-white/8 bg-[#070604] space-y-2">
          {/* Backend Status Pill */}
          <button
            type="button"
            onClick={checkHealth}
            title="Click to re-check backend health"
            className="w-full cursor-pointer flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-stone-900/60 border border-white/8 hover:bg-stone-900 transition text-xs font-mono"
          >
            <span className="flex items-center gap-2 overflow-hidden">
              {healthStatus.state === "healthy" ? (
                <CheckCircle2 className="size-3.5 text-moss-400 shrink-0" />
              ) : healthStatus.state === "loading" ? (
                <Loader2 className="size-3.5 text-amber-400 animate-spin shrink-0" />
              ) : (
                <AlertCircle className="size-3.5 text-rose-400 shrink-0" />
              )}
              <span className="text-[11px] text-stone-300 truncate">
                {healthStatus.state === "healthy"
                  ? `Qdrant (${healthStatus.points?.toLocaleString() || 0} chunks)`
                  : healthStatus.state === "loading"
                  ? "Connecting..."
                  : "Backend Offline"}
              </span>
            </span>
            <span
              className={`size-2 rounded-full shrink-0 ${
                healthStatus.state === "healthy"
                  ? "bg-moss-400 animate-pulse"
                  : healthStatus.state === "loading"
                  ? "bg-amber-400 animate-pulse"
                  : "bg-rose-500"
              }`}
            />
          </button>

          {/* Settings Trigger */}
          <button
            onClick={onOpenSettings}
            className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs text-stone-400 hover:text-white hover:bg-stone-900 transition font-mono"
          >
            <Settings className="size-4 text-stone-400" />
            <span className="font-medium">Backend & API settings</span>
          </button>
        </div>
      </aside>
    </>
  );
}
