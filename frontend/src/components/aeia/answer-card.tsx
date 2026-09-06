"use client";

import * as React from "react";
import { Sparkles, Copy, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceCitation, TelemetryData } from "@/types/aeia";
import { MarkdownView } from "./markdown-view";
import { TelemetryBar } from "./telemetry-bar";
import { CitationList } from "./citation-list";

interface AnswerCardProps {
  question: string;
  answer: string;
  rewrittenQuery?: string | null;
  loading: boolean;
  telemetry: TelemetryData | null;
  sources: SourceCitation[];
  onSelectCitation: (citation: SourceCitation) => void;
}

export function AnswerCard({
  question,
  answer,
  rewrittenQuery,
  loading,
  telemetry,
  sources,
  onSelectCitation,
}: AnswerCardProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    if (!answer) return;
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* Question Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/60">
        <div className="overflow-hidden pr-3">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
            Question
          </span>
          <p className="text-xs font-semibold text-slate-200 truncate">
            {question}
          </p>
        </div>
        {answer && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 text-xs text-muted-foreground hover:text-white gap-1.5 shrink-0"
          >
            {copied ? (
              <>
                <Check className="size-3 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="size-3" />
                <span>Copy Markdown</span>
              </>
            )}
          </Button>
        )}
      </div>

      {/* Rewritten Question Banner */}
      {rewrittenQuery && (
        <div className="mb-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300 flex items-center gap-2">
          <Sparkles className="size-3.5 text-emerald-400 shrink-0" />
          <span>
            <b>Expanded Context Query:</b> {rewrittenQuery}
          </span>
        </div>
      )}

      {/* Telemetry Bar */}
      <TelemetryBar telemetry={telemetry} />

      {/* Answer Body */}
      <div className="flex-1 py-2">
        {loading && !answer && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground py-6 animate-pulse">
            <Loader2 className="size-4 animate-spin text-emerald-400" />
            <span>Analyzing codebase & synthesizing grounded response...</span>
          </div>
        )}
        {answer && <MarkdownView content={answer} isStreaming={loading} />}
      </div>

      {/* Source Citations */}
      <CitationList sources={sources} onSelectCitation={onSelectCitation} />
    </div>
  );
}

