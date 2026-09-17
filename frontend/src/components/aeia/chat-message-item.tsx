"use client";

import * as React from "react";
import {
  Sparkles,
  User,
  Copy,
  Check,
  Loader2,
  FileCode2,
  Cpu,
  Clock,
  Gauge,
  Layers,
} from "lucide-react";
import { ChatMessage, SourceCitation } from "@/types/aeia";
import { MarkdownView } from "./markdown-view";

interface ChatMessageItemProps {
  message: ChatMessage;
  onSelectCitation: (citation: SourceCitation) => void;
}

export function ChatMessageItem({
  message,
  onSelectCitation,
}: ChatMessageItemProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    if (!message.content) return;
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  if (message.role === "user") {
    return (
      <div className="flex justify-end w-full py-2">
        <div className="flex items-start gap-2.5 max-w-[88%] sm:max-w-[75%]">
          <div className="rounded-2xl bg-moss-500/10 border border-moss-500/25 text-stone-100 px-3.5 sm:px-4 py-2.5 text-xs sm:text-sm font-mono shadow-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
          <div className="flex size-7 shrink-0 select-none items-center justify-center rounded-full bg-stone-800 border border-white/10 text-stone-300">
            <User className="size-3.5" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full py-3">
      <div className="flex items-start gap-2.5 sm:gap-3 w-full">
        {/* Assistant Avatar */}
        <div className="flex size-7 shrink-0 select-none items-center justify-center rounded-lg bg-moss-500/10 border border-moss-500/25 text-moss-400 mt-0.5 shadow-sm">
          <Sparkles className="size-3.5" />
        </div>

        {/* Message Content Container */}
        <div className="flex-1 min-w-0 space-y-2.5 font-mono">
          {/* Header */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs font-semibold text-white tracking-tight shrink-0">
                AEIA
              </span>
              {message.telemetry?.route && (
                <span className="text-[10px] text-moss-400 bg-moss-500/10 border border-moss-500/20 px-1.5 py-0.5 rounded truncate">
                  {message.telemetry.route.replace("Autonomous Agent → ", "").replace("Autonomous Engine → ", "")}
                </span>
              )}
            </div>

            {message.content && !message.isStreaming && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] text-stone-400 hover:text-white hover:bg-stone-800 transition shrink-0"
                title="Copy response"
              >
                {copied ? (
                  <>
                    <Check className="size-3 text-moss-400" />
                    <span className="text-moss-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="size-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Expanded Context Query (if query was rewritten) */}
          {message.rewrittenQuery && (
            <div className="border-l-2 border-amber-500/40 bg-amber-500/[0.04] pl-3 py-1.5 text-xs text-amber-200/80 flex items-center gap-2">
              <span className="truncate">
                Expanded query: {message.rewrittenQuery}
              </span>
            </div>
          )}

          {/* Streaming Loading Indicator */}
          {message.isStreaming && !message.content && (
            <div className="flex items-center gap-2 text-xs text-stone-500 py-3 animate-pulse">
              <Loader2 className="size-3.5 animate-spin text-moss-400" />
              <span>Analyzing codebase & synthesizing response...</span>
            </div>
          )}

          {/* Markdown Content */}
          {message.content && (
            <MarkdownView
              content={message.content}
              isStreaming={message.isStreaming}
            />
          )}

          {/* Citations: styled like grep results, grounding the answer in exact source lines */}
          {message.sources && message.sources.length > 0 && (
            <div className="pt-2 border-t border-white/8 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] font-medium text-stone-500">
                <FileCode2 className="size-3 text-moss-400" />
                <span>{message.sources.length} source{message.sources.length === 1 ? "" : "s"} cited</span>
              </div>
              <div className="flex flex-col gap-0.5">
                {message.sources.map((s, idx) => {
                  const fileName = s.file_path.split("/").pop() || s.file_path;
                  const lineInfo =
                    s.start_line && s.end_line
                      ? `:${s.start_line}-${s.end_line}`
                      : "";

                  return (
                    <button
                      key={s.citation || `${s.file_path}:${s.start_line}:${idx}`}
                      type="button"
                      onClick={() => onSelectCitation(s)}
                      className="group flex items-center gap-2 border-l-2 border-stone-700 hover:border-moss-500 bg-stone-900/40 hover:bg-stone-900 pl-2.5 pr-2 py-1 text-[11px] text-stone-400 transition text-left"
                      title={s.file_path}
                    >
                      <span className="text-moss-500/70 group-hover:text-moss-400 shrink-0">❯</span>
                      <span className="truncate max-w-[220px] sm:max-w-sm text-stone-300 group-hover:text-moss-300">
                        {fileName}
                      </span>
                      {lineInfo && (
                        <span className="text-stone-600 shrink-0">
                          {lineInfo}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Subtle Telemetry Footer */}
          {message.telemetry && !message.isStreaming && (
            <div className="pt-1 flex flex-wrap items-center gap-3 text-[10px] text-stone-500">
              <span className="flex items-center gap-1 text-moss-400/90">
                <Gauge className="size-2.5" />
                {message.telemetry.route.replace("Autonomous Agent → ", "").replace("Autonomous Engine → ", "")}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="size-2.5 text-stone-400" />
                {message.telemetry.latency}
              </span>
              <span className="flex items-center gap-1">
                <Layers className="size-2.5 text-stone-400" />
                {message.telemetry.chunks} chunks
              </span>
              <span className="flex items-center gap-1 text-stone-400">
                <Cpu className="size-2.5 text-amber-400" />
                {message.telemetry.model}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
