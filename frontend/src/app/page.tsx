"use client";

import * as React from "react";
import { SourceCitation, TelemetryData } from "@/types/aeia";
import { aeiaService } from "@/services/aeia.service";
import { ModeSelector } from "@/components/aeia/mode-selector";
import { ExamplePrompts } from "@/components/aeia/example-prompts";
import { QueryInput } from "@/components/aeia/query-input";
import { EmptyConsole } from "@/components/aeia/empty-console";
import { ErrorBanner } from "@/components/aeia/error-banner";
import { QuotaAlert } from "@/components/aeia/quota-alert";
import { AnswerCard } from "@/components/aeia/answer-card";
import { CodeModal } from "@/components/aeia/code-modal";
import { SettingsDialog } from "@/components/aeia/settings-dialog";

export default function HomePage() {
  const [activeRoute, setActiveRoute] = React.useState<string | undefined>();
  const [query, setQuery] = React.useState("");
  const [submittedQuery, setSubmittedQuery] = React.useState("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Response state
  const [accumulatedAnswer, setAccumulatedAnswer] = React.useState("");
  const [sources, setSources] = React.useState<SourceCitation[]>([]);
  const [rewrittenQuery, setRewrittenQuery] = React.useState<string | null>(null);
  const [telemetry, setTelemetry] = React.useState<TelemetryData | null>(null);

  // Modals
  const [activeCitation, setActiveCitation] = React.useState<SourceCitation | null>(null);
  const [settingsOpen, setSettingsOpen] = React.useState(false);

  const abortControllerRef = React.useRef<AbortController | null>(null);

  const resetSession = React.useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setQuery("");
    setSubmittedQuery("");
    setSessionId(null);
    setLoading(false);
    setError(null);
    setAccumulatedAnswer("");
    setSources([]);
    setRewrittenQuery(null);
    setTelemetry(null);
    setActiveRoute(undefined);
  }, []);

  React.useEffect(() => {
    const handleReset = () => resetSession();
    window.addEventListener("aeia:reset-chat", handleReset);
    return () => window.removeEventListener("aeia:reset-chat", handleReset);
  }, [resetSession]);

  const handleSubmit = async (overrideQuery?: string) => {
    const targetQuery = (overrideQuery ?? query).trim();
    if (!targetQuery || loading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setError(null);
    setSubmittedQuery(targetQuery);
    setAccumulatedAnswer("");
    setSources([]);
    setRewrittenQuery(null);
    setLoading(true);

    const startTime = performance.now();
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
            setSources(incomingSources);
            if (incomingSessionId) setSessionId(incomingSessionId);
            if (rewritten) setRewrittenQuery(rewritten);
            if (route) {
              resolvedRoute = route;
              setActiveRoute(route);
            }

            const routeLabel =
              resolvedRoute === "git_commit"
                ? "Autonomous Agent → Git Commit Audit"
                : resolvedRoute === "git_history"
                ? "Autonomous Agent → Git History"
                : resolvedRoute === "file_dependents"
                ? "Autonomous Agent → Dependency Mapping"
                : "Autonomous Engine → Hybrid RAG";

            setTelemetry({
              route: routeLabel,
              latency: "streaming...",
              chunks: incomingSources.length,
              model: "gemini-3.6-flash",
            });
          },
          onToken: (token) => {
            setAccumulatedAnswer((prev) => prev + token);
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

            setTelemetry({
              route: routeLabel,
              latency: `${totalSec}s`,
              chunks: currentSources.length,
              model: "gemini-3.6-flash",
            });
            setLoading(false);
          },
          onError: (err) => {
            setError(err);
            setLoading(false);
          },
        },
        abortControllerRef.current.signal
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError(err instanceof Error ? err.message : "Failed to execute query");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExample = (exampleQuery: string) => {
    setQuery(exampleQuery);
    handleSubmit(exampleQuery);
  };

  const isQuotaExceeded =
    accumulatedAnswer.includes("Upstream AI Quota Exceeded") ||
    accumulatedAnswer.includes("Gemini generation quota has been temporarily reached") ||
    Boolean(
      error &&
        (error.includes("429") ||
          error.includes("Quota Exceeded") ||
          error.includes("RESOURCE_EXHAUSTED") ||
          error.includes("LLM_QUOTA_EXHAUSTED"))
    );

  return (
    <div className="container mx-auto flex max-w-7xl flex-1 flex-col lg:flex-row gap-6 p-4 lg:p-6">
      {/* Sidebar Controls */}
      <aside className="lg:w-80 flex flex-col gap-4">
        <ModeSelector activeRoute={activeRoute} />
        <ExamplePrompts onSelect={handleSelectExample} disabled={loading} />
        <div className="rounded-lg border border-border/40 bg-slate-950/40 p-3 text-center text-[11px] text-muted-foreground font-mono">
          BGE-small (384d) • BM25Okapi • Qdrant • Gemini 3.6 Flash
        </div>
      </aside>

      {/* Main Console */}
      <main className="flex-1 flex flex-col gap-4">
        <QueryInput
          query={query}
          onQueryChange={setQuery}
          onSubmit={() => handleSubmit()}
          loading={loading}
        />

        <div className="flex-1 rounded-xl border border-border/70 bg-slate-900/80 p-5 shadow-sm min-h-[420px] flex flex-col">
          {isQuotaExceeded && (
            <QuotaAlert
              onRetry={() => handleSubmit(submittedQuery)}
              onOpenSettings={() => setSettingsOpen(true)}
            />
          )}

          {!isQuotaExceeded && (
            <ErrorBanner error={error} onOpenSettings={() => setSettingsOpen(true)} />
          )}

          {!submittedQuery && !loading ? (
            <EmptyConsole />
          ) : (
            <AnswerCard
              question={submittedQuery}
              answer={accumulatedAnswer}
              rewrittenQuery={rewrittenQuery}
              loading={loading}
              telemetry={telemetry}
              sources={sources}
              onSelectCitation={setActiveCitation}
            />
          )}
        </div>
      </main>

      <CodeModal citation={activeCitation} onClose={() => setActiveCitation(null)} />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
