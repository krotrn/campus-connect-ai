"use client";

import * as React from "react";
import { Sparkles, Key, GitCommit, Share2, History } from "lucide-react";

interface EmptyConsoleProps {
  onSelectPrompt?: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    icon: Key,
    title: "Authentication Flow",
    description: "NextAuth & session middleware",
    query: "Where is user authentication and session management implemented?",
  },
  {
    icon: GitCommit,
    title: "Git Commit Audit",
    description: "Inspects commit hash diff",
    query: "Which files changed in commit 6e19f61 and what was updated?",
  },
  {
    icon: Share2,
    title: "Dependency Mapping",
    description: "Reverse scans compose & import links",
    query: "What application services depend on Redis?",
  },
  {
    icon: History,
    title: "Recent Commits",
    description: "Queries git repository log",
    query: "Show me the recent 5 git commits on this codebase.",
  },
];

export function EmptyConsole({ onSelectPrompt }: EmptyConsoleProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-8 max-w-2xl mx-auto my-auto select-none font-mono animate-in fade-in duration-300">
      {/* Brand Hero */}
      <div className="flex size-12 items-center justify-center rounded-2xl bg-moss-500/10 border border-moss-500/25 text-moss-400 mb-4 shadow-lg shadow-moss-500/5">
        <Sparkles className="size-6" />
      </div>
      <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white mb-2 px-2">
        What would you like to explore in Campus Connect?
      </h2>
      <p className="text-xs text-stone-400 max-w-md mb-8 leading-relaxed px-2">
        Agentic RAG and code intelligence across 94k lines of code, git commits, and service dependencies.
      </p>

      {/* 2x2 Suggestion Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
        {SUGGESTIONS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.title}
              type="button"
              onClick={() => onSelectPrompt?.(item.query)}
              className="group flex items-start gap-3 p-3 text-left rounded-xl border border-white/8 bg-[#131110] hover:bg-stone-900/80 hover:border-moss-500/30 transition shadow-sm"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-stone-800/60 border border-white/6 text-stone-400 group-hover:text-moss-400 group-hover:border-moss-500/30 transition">
                <Icon className="size-3.5" />
              </div>
              <div className="overflow-hidden">
                <div className="text-xs font-medium text-stone-200 group-hover:text-white truncate">
                  {item.title}
                </div>
                <div className="text-[11px] text-stone-500 truncate mt-0.5">
                  {item.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
