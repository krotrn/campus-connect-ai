"use client";

import * as React from "react";
import {
  PanelLeft,
  Plus,
  Settings,
  Zap,
} from "lucide-react";
import { ChatMessage, SourceCitation, TelemetryData } from "@/types/aeia";
import { aeiaService } from "@/services/aeia.service";
import { ChatSidebar } from "@/components/aeia/chat-sidebar";
import { ChatMessageItem } from "@/components/aeia/chat-message-item";
import { QueryInput } from "@/components/aeia/query-input";
import { EmptyConsole } from "@/components/aeia/empty-console";
import { CodeModal } from "@/components/aeia/code-modal";
import { SettingsDialog } from "@/components/aeia/settings-dialog";
import { QuotaAlert } from "@/components/aeia/quota-alert";
import { ErrorBanner } from "@/components/aeia/error-banner";

export default function HomePage() {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [query, setQuery] = React.useState("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Modals
  const [activeCitation, setActiveCitation] = React.useState<SourceCitation | null>(null);
  const [settingsOpen, setSettingsOpen] = React.useState(false);

  const abortControllerRef = React.useRef<AbortController | null>(null);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = React.useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleNewChat = React.useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setMessages([]);
    setQuery("");
    setSessionId(null);
    setLoading(false);
    setError(null);
  }, []);

  React.useEffect(() => {
    const onReset = () => handleNewChat();
    window.addEventListener("aeia:reset-chat", onReset);
    return () => window.removeEventListener("aeia:reset-chat", onReset);
  }, [handleNewChat]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setLoading(false);
      setMessages((prev) => {
        if (prev.length === 0) return prev;
        const last = prev[prev.length - 1];
        if (last.role === "assistant" && last.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, isStreaming: false },
          ];
        }
        return prev;
      });
    }
  };

  const handleSubmit = async (overrideQuery?: string) => {
    const targetQuery = (overrideQuery ?? query).trim();
    if (!targetQuery || loading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setError(null);
    setQuery("");

    // Create user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: targetQuery,
      timestamp: Date.now(),
    };

    // Create placeholder assistant message
    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    abortControllerRef.current = new AbortController();

    try {
      let currentSources: SourceCitation[] = [];
      let resolvedRoute = "direct_rag";

      await aeiaService.askStream(
        targetQuery,
        sessionId,
        {
          onSources: (incomingSources, incomingSessionId, rewritten, route) => {
            currentSources = incomingSources;
            if (incomingSessionId) setSessionId(incomingSessionId);
            if (route) resolvedRoute = route;

            const routeLabel =
              resolvedRoute === "git_commit"
                ? "Autonomous Agent → Git Commit Audit"
                : resolvedRoute === "git_history"
                ? "Autonomous Agent → Git History"
                : resolvedRoute === "file_dependents"
                ? "Autonomous Agent → Dependency Mapping"
                : "Autonomous Engine → Hybrid RAG";

            const telemetryData: TelemetryData = {
              route: routeLabel,
              latency: "streaming...",
              chunks: incomingSources.length,
              model: "gemini-3.6-flash",
            };

            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      sources: incomingSources,
                      rewrittenQuery: rewritten || m.rewrittenQuery,
                      telemetry: telemetryData,
                    }
                  : m
              )
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onDone: (latencyMs, route) => {
            const totalSec = (latencyMs / 1000).toFixed(2);
            const finalRoute = route || resolvedRoute;
            const routeLabel =
              finalRoute === "git_commit"
                ? "Autonomous Agent → Git Commit Audit"
                : finalRoute === "git_history"
                ? "Autonomous Agent → Git History"
                : finalRoute === "file_dependents"
                ? "Autonomous Agent → Dependency Mapping"
                : "Autonomous Engine → Hybrid RAG";

            const finalTelemetry: TelemetryData = {
              route: routeLabel,
              latency: `${totalSec}s`,
              chunks: currentSources.length,
              model: "gemini-3.6-flash",
            };

            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      isStreaming: false,
                      telemetry: finalTelemetry,
                      sources: currentSources,
                    }
                  : m
              )
            );
            setLoading(false);
          },
          onError: (err) => {
            setError(err);
            setLoading(false);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      isStreaming: false,
                      content:
                        m.content ||
                        "An error occurred while generating the response. Please check your backend connection.",
                    }
                  : m
              )
            );
          },
        },
        abortControllerRef.current.signal
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError(err instanceof Error ? err.message : "Failed to execute query");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  isStreaming: false,
                  content:
                    m.content ||
                    "Failed to communicate with backend server. Check your network or API keys.",
                }
              : m
          )
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const isQuotaExceeded = Boolean(
    error &&
      (error.includes("429") ||
        error.includes("Quota Exceeded") ||
        error.includes("RESOURCE_EXHAUSTED") ||
        error.includes("LLM_QUOTA_EXHAUSTED"))
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#09090b] text-zinc-100 font-mono">
      {/* ChatGPT Collapsible Sidebar */}
      <ChatSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectPrompt={(p) => handleSubmit(p)}
        onOpenSettings={() => setSettingsOpen(true)}
        hasMessages={messages.length > 0}
      />

      {/* Main Chat Viewport */}
      <div className="flex flex-1 flex-col h-full min-w-0 overflow-hidden bg-[#09090b]">
        {/* Top App Bar */}
        <header className="h-12 border-b border-white/8 px-3.5 flex items-center justify-between shrink-0 bg-[#09090b]/85 backdrop-blur z-20">
          <div className="flex items-center gap-2.5">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
                title="Open sidebar"
              >
                <PanelLeft className="size-4" />
              </button>
            )}

            <div className="flex items-center gap-2">
              <div className="flex size-6 items-center justify-center rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold">
                <Zap className="size-3.5" />
              </div>
              <span className="font-semibold text-xs tracking-tight text-white font-mono">
                AEIA
              </span>
              <span className="text-[11px] text-zinc-500 hidden sm:inline border-l border-white/8 pl-2">
                Campus Connect (~94k LOC)
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-900 transition text-xs font-mono font-medium border border-white/6"
              title="Start new conversation"
            >
              <Plus className="size-3.5 text-emerald-400" />
              <span className="hidden sm:inline">New Chat</span>
            </button>

            <button
              onClick={() => setSettingsOpen(true)}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
              title="Settings"
            >
              <Settings className="size-4" />
            </button>
          </div>
        </header>

        {/* Scrollable Conversation Stream */}
        <div className="flex-1 overflow-y-auto px-4 py-4 scroll-smooth">
          <div className="max-w-3xl mx-auto w-full min-h-full flex flex-col justify-between">
            {messages.length === 0 ? (
              <EmptyConsole onSelectPrompt={(p) => handleSubmit(p)} />
            ) : (
              <div className="space-y-4 pb-4">
                {isQuotaExceeded && (
                  <QuotaAlert
                    onRetry={() => {
                      const lastUser = [...messages]
                        .reverse()
                        .find((m) => m.role === "user");
                      if (lastUser) handleSubmit(lastUser.content);
                    }}
                    onOpenSettings={() => setSettingsOpen(true)}
                  />
                )}

                {error && !isQuotaExceeded && (
                  <ErrorBanner
                    error={error}
                    onOpenSettings={() => setSettingsOpen(true)}
                  />
                )}

                {messages.map((m) => (
                  <ChatMessageItem
                    key={m.id}
                    message={m}
                    onSelectCitation={setActiveCitation}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Docked Bottom Input (ChatGPT Style) */}
        <div className="shrink-0 bg-gradient-to-t from-[#09090b] via-[#09090b]/95 to-transparent pt-2">
          <QueryInput
            query={query}
            onQueryChange={setQuery}
            onSubmit={() => handleSubmit()}
            onStop={handleStop}
            loading={loading}
          />
        </div>
      </div>

      {/* Code Viewer Modal */}
      <CodeModal
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </div>
  );
}
