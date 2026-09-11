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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="flex flex-col w-full max-w-4xl max-h-[85vh] rounded-xl border border-border bg-slate-900 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/60 bg-slate-950 px-5 py-3.5">
          <div className="flex items-center gap-2 font-mono text-sm">
            <span className="font-semibold text-emerald-400">{citation.file_path}</span>
            {lineRange && (
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                {lineRange}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition"
            title="Close modal"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Code Content with Line Numbers */}
        <div className="flex-1 overflow-y-auto bg-slate-950 p-4 font-mono text-xs">
          {lines.length === 0 ? (
            <p className="text-slate-500">
              No source content was returned for this citation.
            </p>
          ) : (
          <div className="flex">
            {/* Line numbers column */}
            <div className="select-none pr-4 text-right text-slate-600">
              {lines.map((_, idx) => (
                <div key={idx}>{startNum + idx}</div>
              ))}
            </div>
            {/* Code content */}
            <pre className="flex-1 overflow-x-auto text-slate-200">
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
        <div className="flex items-center justify-between border-t border-border/60 bg-slate-900 px-5 py-2.5 text-xs text-muted-foreground">
          <span>
            {hasScore
              ? `Relevance Score: ${citation.score!.toFixed(4)}`
              : "Relevance score unavailable"}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
            disabled={!content}
            className="flex items-center gap-1.5 h-8 text-xs bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-200 disabled:opacity-50"
          >
            {copied ? (
              <>
                <Check className="size-3 text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="size-3" />
                <span>Copy Snippet</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

