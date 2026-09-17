"use client";

import * as React from "react";
import { Check, Copy, X } from "lucide-react";
import { SourceCitation } from "@/types/aeia";
import { Button } from "@/components/ui/button";

interface CodeModalProps {
  citation: SourceCitation | null;
  onClose: () => void;
}

export function CodeModal({ citation, onClose }: CodeModalProps) {
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!citation) return null;

  // content and score are optional on the wire: agent-generated sources and
  // degraded responses can omit them, so never dereference them directly.
  const content = citation.content ?? "";
  const hasScore = typeof citation.score === "number";

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  const lineRange =
    citation.start_line && citation.end_line
      ? `#L${citation.start_line}-L${citation.end_line}`
      : "";

  // Split lines for line numbers
  const lines = content ? content.split("\n") : [];
  const startNum = citation.start_line || 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="flex flex-col w-full h-full sm:h-auto sm:max-w-4xl max-h-dvh sm:max-h-[85vh] rounded-none sm:rounded-xl border-0 sm:border border-border bg-[#0e0d0b] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 bg-[#0b0a08] px-4 sm:px-5 py-3 sm:py-3.5 gap-3">
          <div className="flex items-center gap-2 font-mono text-xs sm:text-sm min-w-0">
            <span className="font-semibold text-moss-400 truncate">{citation.file_path}</span>
            {lineRange && (
              <span className="rounded bg-stone-800 px-2 py-0.5 text-xs text-stone-400 shrink-0">
                {lineRange}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-stone-400 hover:bg-stone-800 hover:text-white transition shrink-0"
            title="Close modal"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Code Content with Line Numbers */}
        <div className="flex-1 overflow-y-auto bg-[#0b0a08] p-3 sm:p-4 font-mono text-[11px] sm:text-xs">
          {lines.length === 0 ? (
            <p className="text-stone-500">
              No source content was returned for this citation.
            </p>
          ) : (
          <div className="flex">
            {/* Line numbers column */}
            <div className="select-none pr-3 sm:pr-4 text-right text-stone-600">
              {lines.map((_, idx) => (
                <div key={idx}>{startNum + idx}</div>
              ))}
            </div>
            {/* Code content */}
            <pre className="flex-1 overflow-x-auto text-stone-200">
              <code>
                {lines.map((line, idx) => (
                  <div key={idx}>{line || " "}</div>
                ))}
              </code>
            </pre>
          </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border/60 bg-[#0e0d0b] px-4 sm:px-5 py-2.5 text-xs text-muted-foreground gap-3">
          <span className="truncate">
            {hasScore
              ? `Relevance score: ${citation.score!.toFixed(4)}`
              : "Relevance score unavailable"}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
            disabled={!content}
            className="flex items-center gap-1.5 h-8 text-xs bg-stone-800 border-stone-700 hover:bg-stone-700 text-stone-200 disabled:opacity-50 shrink-0"
          >
            {copied ? (
              <>
                <Check className="size-3 text-moss-400" />
                <span className="text-moss-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="size-3" />
                <span className="hidden sm:inline">Copy snippet</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

