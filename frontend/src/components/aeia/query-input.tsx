"use client";

import * as React from "react";
import { ArrowUp, Square } from "lucide-react";

interface QueryInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  loading: boolean;
  disabled?: boolean;
}

export function QueryInput({
  query,
  onQueryChange,
  onSubmit,
  onStop,
  loading,
  disabled,
}: QueryInputProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  React.useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && query.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) {
      onStop?.();
    } else if (query.trim() && !disabled) {
      onSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      <form
        onSubmit={handleFormSubmit}
        className="relative flex flex-col rounded-2xl border border-white/8 bg-[#0e0e12] shadow-2xl focus-within:border-emerald-500/60 transition-colors backdrop-blur font-mono"
      >
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Ask anything about Campus Connect code, architecture, or git history..."
          className="w-full resize-none bg-transparent px-4 pt-3.5 pb-10 text-xs sm:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none max-h-48 min-h-[44px] font-mono leading-relaxed"
        />

        <div className="absolute right-2.5 bottom-2.5 flex items-center gap-2 font-mono">
          <span className="hidden sm:inline text-[10px] text-zinc-500 select-none">
            {loading ? "click to stop" : "enter to send"}
          </span>

          {loading ? (
            <button
              type="button"
              onClick={onStop}
              className="flex size-7 items-center justify-center rounded-full bg-rose-500 hover:bg-rose-600 text-white transition shadow"
              title="Stop generation"
            >
              <Square className="size-3 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!query.trim() || disabled}
              className="flex size-7 items-center justify-center rounded-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-20 disabled:hover:bg-emerald-500 text-zinc-950 transition shadow"
              title="Send message"
            >
              <ArrowUp className="size-4 stroke-[2.5]" />
            </button>
          )}
        </div>
      </form>

      <p className="mt-2 text-center text-[10px] text-zinc-500 select-none font-mono">
        AEIA synthesizes grounded code intelligence across Campus Connect (~94k LOC). Responses cite verified sources.
      </p>
    </div>
  );
}
