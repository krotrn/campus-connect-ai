"use client";

import * as React from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface QueryInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  loading: boolean;
  disabled?: boolean;
}

export function QueryInput({
  query,
  onQueryChange,
  onSubmit,
  loading,
  disabled,
}: QueryInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  const handleFormSubmit = (e: React.SubmitEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm">
      <form onSubmit={handleFormSubmit} className="flex flex-col gap-3">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={3}
            placeholder="Ask anything about Campus Connect code, architecture, or git history... (Press Enter to submit)"
            className="w-full resize-none rounded-xl border border-border bg-slate-950 px-4 py-3 text-xs sm:text-sm text-slate-100 placeholder-muted-foreground focus:border-emerald-500 focus:outline-none transition disabled:opacity-50"
          />
          <div className="absolute right-3 bottom-3 flex items-center gap-2">
            <span className="hidden sm:inline text-[11px] text-muted-foreground">
              Shift + Enter for new line
            </span>
            <Button
              type="submit"
              size="sm"
              disabled={loading || !query.trim() || disabled}
              className="h-8 px-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs gap-1.5 shadow"
            >
              {loading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <Send className="size-3.5" />
                  <span>Ask</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

