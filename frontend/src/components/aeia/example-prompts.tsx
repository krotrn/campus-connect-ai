"use client";

import * as React from "react";
import { Key, GitCommit, Share2, History } from "lucide-react";
import { ExecutionMode } from "@/types/aeia";

export interface ExamplePrompt {
  id: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  query: string;
  mode: ExecutionMode;
}

const EXAMPLE_PROMPTS: ExamplePrompt[] = [
  {
    id: "auth",
    icon: <Key className="size-4 text-emerald-400" />,
    title: "Authentication Flow",
    subtitle: "NextAuth & session middleware",
    query: "Where is user authentication and session management implemented?",
    mode: "rag",
  },
  {
    id: "git-commit",
    icon: <GitCommit className="size-4 text-indigo-400" />,
    title: "Git Commit Audit",
    subtitle: "Inspects commit hash diff",
    query: "Which files changed in commit 6e19f61 and what was updated?",
    mode: "agent",
  },
  {
    id: "dependencies",
    icon: <Share2 className="size-4 text-amber-400" />,
    title: "Dependency Mapping",
    subtitle: "Scans compose & import links",
    query: "What application services depend on Redis?",
    mode: "agent",
  },
  {
    id: "recent-commits",
    icon: <History className="size-4 text-cyan-400" />,
    title: "Recent Commits",
    subtitle: "Queries git repository log",
    query: "Show me the recent 5 git commits on this codebase.",
    mode: "agent",
  },
];

interface ExamplePromptsProps {
  onSelect: (query: string, mode?: ExecutionMode) => void;
  disabled?: boolean;
}

export function ExamplePrompts({ onSelect, disabled }: ExamplePromptsProps) {
  return (
    <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm flex-1">
      <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        Example Queries
      </h3>
      <div className="space-y-2">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(p.query, p.mode)}
            className={`w-full text-left p-2.5 rounded-lg bg-slate-950 border border-border/60 hover:border-emerald-500/50 hover:bg-slate-800/40 transition flex items-start gap-2.5 group ${
              disabled ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <div className="mt-0.5 shrink-0 group-hover:scale-110 transition-transform">
              {p.icon}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-medium text-slate-200 group-hover:text-white truncate">
                {p.title}
              </p>
              <p className="text-[11px] text-muted-foreground truncate">{p.subtitle}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

