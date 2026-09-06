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
        <div className="flex items-start gap-2.5 max-w-[85%] sm:max-w-[75%]">
          <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/25 text-zinc-100 px-4 py-2.5 text-xs sm:text-sm font-mono shadow-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
          <div className="flex size-7 shrink-0 select-none items-center justify-center rounded-full bg-zinc-800 border border-white/10 text-zinc-300">
            <User className="size-3.5" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full py-3">
      <div className="flex items-start gap-3 w-full">
        {/* Assistant Avatar */}
        <div className="flex size-7 shrink-0 select-none items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 mt-0.5 shadow-sm">
          <Sparkles className="size-3.5" />
        </div>

        {/* Message Content Container */}
        <div className="flex-1 min-w-0 space-y-2.5 font-mono">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white tracking-tight">
                AEIA
              </span>
              {message.telemetry?.route && (
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                  {message.telemetry.route.replace("Autonomous Agent → ", "").replace("Autonomous Engine → ", "")}
                </span>
              )}
            </div>

            {message.content && !message.isStreaming && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
                title="Copy response"
              >
                {copied ? (
                  <>
                    <Check className="size-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
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
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-xs text-emerald-300/90 flex items-center gap-2">
              <Sparkles className="size-3 text-emerald-400 shrink-0" />
              <span className="truncate">
                <b>Expanded Query:</b> {message.rewrittenQuery}
              </span>
            </div>
          )}

          {/* Streaming Loading Indicator */}
          {message.isStreaming && !message.content && (
            <div className="flex items-center gap-2 text-xs text-zinc-500 py-3 animate-pulse">
              <Loader2 className="size-3.5 animate-spin text-emerald-400" />
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

          {/* Citations Chips */}
          {message.sources && message.sources.length > 0 && (
            <div className="pt-2 border-t border-white/8 space-y-1.5">
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                <FileCode2 className="size-3 text-emerald-400" />
                <span>Sources ({message.sources.length})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {message.sources.map((s, idx) => {
                  const fileName = s.file_path.split("/").pop() || s.file_path;
                  const lineInfo =
                    s.start_line && s.end_line
                      ? `:${s.start_line}-${s.end_line}`
                      : "";

                  return (
                    <button
                      key={s.chunk_id || idx}
                      type="button"
                      onClick={() => onSelectCitation(s)}
                      className="group flex items-center gap-1.5 rounded-lg border border-white/8 bg-zinc-900/90 px-2 py-1 text-[11px] text-zinc-300 hover:border-emerald-500/40 hover:bg-zinc-800 transition"
                      title={s.file_path}
                    >
                      <span className="text-[10px] text-emerald-400 font-bold">
                        #{idx + 1}
                      </span>
                      <span className="truncate max-w-[180px] sm:max-w-xs text-zinc-200 group-hover:text-emerald-300">
                        {fileName}
                      </span>
                      {lineInfo && (
                        <span className="text-[10px] text-zinc-500">
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
            <div className="pt-1 flex flex-wrap items-center gap-3 text-[10px] text-zinc-500">
              <span className="flex items-center gap-1 text-emerald-400/90">
                <Gauge className="size-2.5" />
                {message.telemetry.route.replace("Autonomous Agent → ", "").replace("Autonomous Engine → ", "")}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="size-2.5 text-blue-400" />
                {message.telemetry.latency}
              </span>
              <span className="flex items-center gap-1">
                <Layers className="size-2.5 text-indigo-400" />
                {message.telemetry.chunks} chunks
              </span>
              <span className="flex items-center gap-1 text-zinc-400">
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
