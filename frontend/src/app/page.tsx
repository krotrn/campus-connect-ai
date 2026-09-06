"use client";

import * as React from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useDebounce } from "@/hooks/use-debounce";
import { useHealthQuery } from "@/hooks/queries/use-health";
import {
  Sparkles,
  CheckCircle2,
  Zap,
  ShieldCheck,
  Search,
  Send,
  Loader2,
  Key,
  GitCommit,
  Share2,
  History,
  AlertCircle,
  Copy,
  Check,
  Code2,
  Boxes,
  Terminal,
  ArrowRight,
  Database,
  RefreshCw,
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExecutionMode, SourceCitation, TelemetryData } from "@/types/aeia";
import { aeiaService } from "@/services/aeia.service";
import { MarkdownView } from "@/components/aeia/markdown-view";
import { CodeModal } from "@/components/aeia/code-modal";
import { TelemetryBar } from "@/components/aeia/telemetry-bar";
import { SettingsDialog } from "@/components/aeia/settings-dialog";

export default function Home() {
  const [searchTerm, setSearchTerm] = React.useState("");
  const debouncedSearch = useDebounce(searchTerm, 300);
  const [isCopied, setIsCopied] = React.useState(false);
interface ExamplePrompt {
  id: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  query: string;
  mode: ExecutionMode;
}

  const { data: healthData, isPending: isHealthLoading, isFetching: isHealthFetching, refetch: refetchHealth } = useHealthQuery();
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

  const features = [
    {
      title: "Next.js 16 App Router",
      description:
        "Engineered with React 19 Server Components, streaming metadata, and modern layouts under src/app.",
      icon: <Zap className="size-6 text-blue-500" />,
      badge: "Core",
    },
    {
      title: "TanStack Query v5",
      description:
        "Declarative server-state management with automatic caching, background refetching, and SSR hydration.",
      icon: <Database className="size-6 text-cyan-500" />,
      badge: "Data Fetching",
    },
    {
      title: "TypeScript Strict Mode",
      description:
        "Full end-to-end type safety, path aliases (@/*), zod schema validation, and strict compiler options.",
      icon: <Code2 className="size-6 text-emerald-500" />,
      badge: "Types",
    },
    {
      title: "shadcn/ui & Tailwind v4",
      description:
        "Accessible, themeable component primitives powered by Tailwind CSS v4 and modern Base UI.",
      icon: <Boxes className="size-6 text-purple-500" />,
      badge: "UI / UX",
    },
    {
      title: "Vitest & Testing Library",
      description:
        "Blazing fast unit and component tests with jsdom, coverage reporting, and React Testing Library.",
      icon: <CheckCircle2 className="size-6 text-amber-500" />,
      badge: "Testing",
    },
    {
      title: "Playwright E2E",
      description:
        "Reliable cross-browser end-to-end testing suite validating routes, user flows, and APIs.",
      icon: <ShieldCheck className="size-6 text-rose-500" />,
      badge: "E2E",
    },
  ];
export default function HomePage() {
  const [mode, setMode] = React.useState<ExecutionMode>("rag");
  const [query, setQuery] = React.useState("");
  const [submittedQuery, setSubmittedQuery] = React.useState("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const candidates = [
    { id: 1, name: "Alex Morgan", role: "Senior Fullstack Engineer", experience: "6 yrs", tag: "React, Node" },
    { id: 2, name: "Sarah Chen", role: "Lead Frontend Architect", experience: "8 yrs", tag: "Next.js, TypeScript" },
    { id: 3, name: "David Kim", role: "DevOps & Cloud Engineer", experience: "5 yrs", tag: "Kubernetes, AWS" },
    { id: 4, name: "Emily Watson", role: "Product Designer", experience: "4 yrs", tag: "Figma, UI Systems" },
  ];
  // Response state
  const [accumulatedAnswer, setAccumulatedAnswer] = React.useState("");
  const [sources, setSources] = React.useState<SourceCitation[]>([]);
  const [rewrittenQuery, setRewrittenQuery] = React.useState<string | null>(null);
  const [telemetry, setTelemetry] = React.useState<TelemetryData | null>(null);

  const filteredCandidates = candidates.filter(
    (c) =>
      c.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      c.role.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      c.tag.toLowerCase().includes(debouncedSearch.toLowerCase())
  );
  // Modals
  const [activeCitation, setActiveCitation] = React.useState<SourceCitation | null>(null);
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [copiedAnswer, setCopiedAnswer] = React.useState(false);

  const copyCommand = () => {
    navigator.clipboard.writeText("pnpm run test && pnpm run build");
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  // Abort controller for streaming
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
  }, []);

  React.useEffect(() => {
    const handleReset = () => resetSession();
    window.addEventListener("aeia:reset-chat", handleReset);
    return () => window.removeEventListener("aeia:reset-chat", handleReset);
  }, [resetSession]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const q = query.trim();
    if (!q || loading) return;

    // Reset previous response states
    setError(null);
    setSubmittedQuery(q);
    setAccumulatedAnswer("");
    setSources([]);
    setRewrittenQuery(null);
    setLoading(true);

    const startTime = performance.now();
    abortControllerRef.current = new AbortController();

    if (mode === "rag") {
      // Streamed Hybrid RAG mode
      try {
        let currentSources: SourceCitation[] = [];
        await aeiaService.askStream(
          q,
          sessionId,
          {
            onSources: (incomingSources, incomingSessionId, rewritten) => {
              currentSources = incomingSources;
              setSources(incomingSources);
              if (incomingSessionId) setSessionId(incomingSessionId);
              if (rewritten) setRewrittenQuery(rewritten);

              setTelemetry({
                route: "Direct Hybrid RAG (Dense + BM25)",
                latency: "streaming...",
                chunks: incomingSources.length,
                model: "gemini-3.6-flash",
              });
            },
            onToken: (token) => {
              setAccumulatedAnswer((prev) => prev + token);
            },
            onDone: (latencyMs) => {
              const totalSec = (latencyMs / 1000).toFixed(2);
              setTelemetry((prev) =>
                prev
                  ? { ...prev, latency: `${totalSec}s` }
                  : {
                      route: "Direct Hybrid RAG (Dense + BM25)",
                      latency: `${totalSec}s`,
                      chunks: currentSources.length,
                      model: "gemini-3.6-flash",
                    }
              );
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
          setError(err instanceof Error ? err.message : "Failed to execute RAG query");
        }
      } finally {
        setLoading(false);
      }
    } else {
      // LangGraph Agent mode
      try {
        setTelemetry({
          route: "LangGraph State Graph Router",
          latency: "processing multi-step graph...",
          chunks: 0,
          model: "gemini-3.6-flash",
        });

        const res = await aeiaService.askAgent(q, sessionId, abortControllerRef.current.signal);
        const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

        setAccumulatedAnswer(res.answer);
        if (res.session_id) setSessionId(res.session_id);
        if (res.sources && res.sources.length > 0) {
          setSources(res.sources);
        }

        setTelemetry({
          route: `Agent (${res.route_taken || "Multi-Step"})`,
          latency: `${elapsed}s`,
          chunks: res.sources ? res.sources.length : 0,
          model: "gemini-3.6-flash",
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError(err instanceof Error ? err.message : "Agent execution failed");
        }
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="flex flex-col items-center justify-center">
      {/* Hero Section */}
      <section className="relative w-full overflow-hidden py-20 md:py-28">
        <div className="container mx-auto flex max-w-5xl flex-col items-center px-4 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-muted/50 px-3.5 py-1.5 text-xs font-medium backdrop-blur">
            <Sparkles className="size-3.5 text-amber-500" />
            <span>Production Grade Template Ready</span>
            <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
              v1.0.0
            </Badge>
          </div>
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
            Next.js 16 + TanStack Query{" "}
            <span className="bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 bg-clip-text text-transparent">
              Production Architecture
            </span>
          </h1>
  const handleCopyAnswer = async () => {
    if (!accumulatedAnswer) return;
    try {
      await navigator.clipboard.writeText(accumulatedAnswer);
      setCopiedAnswer(true);
      setTimeout(() => setCopiedAnswer(false), 1500);
    } catch {
      // ignore
    }
  };

          <p className="mt-6 max-w-2xl text-base text-muted-foreground sm:text-lg">
            A production-ready foundation with strict TypeScript, clean folder
            architecture, TanStack Query v5, shadcn/ui components, Vitest unit testing, Playwright
            E2E, and automated CI pipelines.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <a
              href="#demo"
              className={buttonVariants({ size: "lg", className: "gap-2" })}
  return (
    <div className="container mx-auto flex max-w-7xl flex-1 flex-col lg:flex-row gap-6 p-4 lg:p-6">
      {/* Sidebar Controls */}
      <aside className="lg:w-80 flex flex-col gap-4">
        {/* Mode Selector */}
        <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm">
          <label className="block text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2.5">
            Execution Mode
          </label>
          <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-slate-950 p-1">
            <button
              onClick={() => setMode("rag")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                mode === "rag"
                  ? "bg-emerald-500 text-slate-950 font-semibold shadow-sm"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              <span>Try Live Interactive Demo</span>
              <ArrowRight className="size-4" />
            </a>
            <Button
              variant="outline"
              size="lg"
              onClick={copyCommand}
              className="gap-2 font-mono text-xs"
              Hybrid RAG
            </button>
            <button
              onClick={() => setMode("agent")}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                mode === "agent"
                  ? "bg-indigo-500 text-white font-semibold shadow-sm"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              <Terminal className="size-4" />
              <span>{isCopied ? "Copied to clipboard!" : "pnpm run test"}</span>
            </Button>
              LangGraph Agent
            </button>
          </div>
          <p className="mt-2.5 text-[11px] text-muted-foreground leading-relaxed">
            {mode === "rag"
              ? "Direct 70/30 Dense (FastEmbed) + BM25Okapi RRF search fused with Gemini streaming."
              : "LangGraph State Graph routing dynamically across Git history, diffs, dependency scans, and RAG."}
          </p>
        </div>
      </section>

      {/* Interactive Demo Section */}
      <section id="demo" className="w-full bg-muted/40 py-16">
        <div className="container mx-auto max-w-5xl px-4">
          <div className="mb-8 text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Interactive Component & State Demo
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Demonstrating TanStack Query, shadcn/ui components, and custom hooks.
            </p>
        {/* Example Queries */}
        <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm flex-1">
          <h3 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Example Queries
          </h3>
          <div className="space-y-2">
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setQuery(p.query);
                  setMode(p.mode);
                }}
                className="w-full text-left p-2.5 rounded-lg bg-slate-950 border border-border/60 hover:border-emerald-500/50 hover:bg-slate-800/40 transition flex items-start gap-2.5 group"
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

          <Tabs defaultValue="query" className="w-full">
            <div className="flex justify-center mb-6">
              <TabsList>
                <TabsTrigger value="query">TanStack Query Demo</TabsTrigger>
                <TabsTrigger value="candidates">Candidate Search Demo</TabsTrigger>
                <TabsTrigger value="architecture">Directory Specs</TabsTrigger>
              </TabsList>
        {/* Architecture Note */}
        <div className="rounded-lg border border-border/40 bg-slate-950/40 p-3 text-center text-[11px] text-muted-foreground font-mono">
          BGE-small (384d) • BM25Okapi • Qdrant • Gemini 3.6 Flash
        </div>
      </aside>

      {/* Main Console */}
      <main className="flex-1 flex flex-col gap-4">
        {/* Input Form */}
        <div className="rounded-xl border border-border/70 bg-slate-900/80 p-4 shadow-sm">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="relative">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={3}
                placeholder="Ask anything about Campus Connect code, architecture, or git history... (Press Enter to submit)"
                className="w-full resize-none rounded-xl border border-border bg-slate-950 px-4 py-3 text-xs sm:text-sm text-slate-100 placeholder-muted-foreground focus:border-emerald-500 focus:outline-none transition"
              />
              <div className="absolute right-3 bottom-3 flex items-center gap-2">
                <span className="hidden sm:inline text-[11px] text-muted-foreground">
                  Shift + Enter for new line
                </span>
                <Button
                  type="submit"
                  size="sm"
                  disabled={loading || !query.trim()}
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

            <TabsContent value="query">
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Database className="size-5 text-cyan-600" />
                      <span>Live Server State (TanStack Query)</span>
                    </span>
                    <Badge variant={healthData?.data?.status === "healthy" ? "success" : "secondary"}>
                      {isHealthLoading ? "Loading..." : healthData?.data?.status || "Ready"}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Demonstrating automatic caching, query invalidation, and background state synchronization.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                          Health Check Endpoint
                        </p>
                        <p className="text-sm font-mono text-foreground mt-0.5">
                          GET /api/health
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchHealth()}
                        disabled={isHealthFetching}
                        className="gap-2"
                      >
                        <RefreshCw className={`size-3.5 ${isHealthFetching ? "animate-spin text-primary" : ""}`} />
                        <span>{isHealthFetching ? "Fetching..." : "Refetch Query"}</span>
                      </Button>
                    </div>
        {/* Response Container */}
        <div className="flex-1 rounded-xl border border-border/70 bg-slate-900/80 p-5 shadow-sm min-h-[420px] flex flex-col">
          {/* Error Banner */}
          {error && (
            <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-300 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="size-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-rose-200">Execution Error</p>
                  <p className="text-[11px] mt-0.5">{error}</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSettingsOpen(true)}
                className="h-7 text-xs border-rose-500/40 hover:bg-rose-500/20 text-rose-200 gap-1 shrink-0"
              >
                <Settings className="size-3" />
                <span>Check Settings</span>
              </Button>
            </div>
          )}

                    <div className="mt-4 rounded-md bg-muted p-3 font-mono text-xs text-muted-foreground">
                      {isHealthLoading ? (
                        <p>Querying server endpoint...</p>
                      ) : (
                        <pre className="overflow-x-auto text-foreground">
                          {JSON.stringify(healthData, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between border-t border-border/40 pt-4 text-xs text-muted-foreground">
                  <span>Query Cache: Stale Time (30s) • GC Time (5m)</span>
                  <span>React Query Devtools Enabled</span>
                </CardFooter>
              </Card>
            </TabsContent>
          {/* Empty State */}
          {!submittedQuery && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-muted-foreground">
              <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-3 shadow-inner">
                <Sparkles className="size-7" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200 mb-1">
                AEIA Engineering Intelligence Console
              </h3>
              <p className="text-xs max-w-md leading-relaxed">
                Type an engineering question above or pick one of the example queries to inspect real grounded code citations, dependency linkages, or git diffs.
              </p>
            </div>
          )}

            <TabsContent value="candidates">
              <Card className="shadow-md">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center justify-between">
                    <span>Talent Pool Explorer</span>
                    <Badge variant="outline">Live Hook Demo</Badge>
                  </CardTitle>
                  <CardDescription>
                    Search across candidates in real-time with debounced input filtering.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by candidate name, role, or technology..."
                      className="pl-9"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
          {/* Answer Section */}
          {submittedQuery && (
            <div className="flex-1 flex flex-col">
              {/* Question Header */}
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/60">
                <div className="overflow-hidden pr-3">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">
                    Question
                  </span>
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {submittedQuery}
                  </p>
                </div>
                {accumulatedAnswer && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyAnswer}
                    className="h-7 text-xs text-muted-foreground hover:text-white gap-1.5 shrink-0"
                  >
                    {copiedAnswer ? (
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

              {/* Rewritten Question / Expanded Context Notice */}
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

              {/* Answer Content */}
              <div className="flex-1 py-2">
                {loading && !accumulatedAnswer && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground py-6 animate-pulse">
                    <Loader2 className="size-4 animate-spin text-emerald-400" />
                    <span>Analyzing codebase & synthesizing grounded response...</span>
                  </div>
                )}
                {accumulatedAnswer && (
                  <MarkdownView content={accumulatedAnswer} isStreaming={loading} />
                )}
              </div>

                  {debouncedSearch && (
                    <div className="text-xs text-muted-foreground">
                      Debounced Query: <span className="font-semibold text-foreground">&quot;{debouncedSearch}&quot;</span>
                    </div>
                  )}

                  <div className="grid gap-3 sm:grid-cols-2">
                    {filteredCandidates.length > 0 ? (
                      filteredCandidates.map((candidate) => (
                        <div
                          key={candidate.id}
                          className="flex items-center justify-between rounded-lg border border-border p-3.5 transition-colors hover:bg-muted/50"
              {/* Verified Source Citations */}
              {sources.length > 0 && (
                <div className="mt-auto pt-4 border-t border-border/60">
                  <h4 className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                    <Code2 className="size-3.5 text-emerald-400" />
                    <span>Verified Source Citations ({sources.length})</span>
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {sources.map((s, idx) => {
                      const range =
                        s.start_line && s.end_line
                          ? `#L${s.start_line}-L${s.end_line}`
                          : "";
                      return (
                        <button
                          key={s.chunk_id || idx}
                          onClick={() => setActiveCitation(s)}
                          className="flex items-center gap-1.5 rounded-md border border-border bg-slate-950 px-2.5 py-1 font-mono text-xs text-slate-300 hover:border-emerald-500/60 hover:bg-slate-800 transition"
                          title="Click to view code snippet"
                        >
                          <div className="flex items-center gap-3">
                            <Avatar>
                              <AvatarFallback className="bg-primary/10 text-primary font-bold">
                                {candidate.name.slice(0, 2).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-sm leading-none">
                                {candidate.name}
                              </p>
                              <p className="text-xs text-muted-foreground mt-1">
                                {candidate.role}
                              </p>
                            </div>
                          </div>
                          <Badge variant="secondary" className="text-xs">
                            {candidate.experience}
                          </Badge>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-2 py-8 text-center text-sm text-muted-foreground">
                        No candidates found matching &quot;{debouncedSearch}&quot;
                      </div>
                    )}
                          <span className="text-[10px] text-emerald-400 font-bold">
                            #{idx + 1}
                          </span>
                          <span className="truncate max-w-xs">{s.file_path}</span>
                          {range && (
                            <span className="text-[10px] text-muted-foreground">
                              {range}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between border-t border-border/40 pt-4 text-xs text-muted-foreground">
                  <span>Showing {filteredCandidates.length} of {candidates.length} candidates</span>
                  <span>Tested with Vitest & React Testing Library</span>
                </CardFooter>
              </Card>
            </TabsContent>

            <TabsContent value="architecture">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Scalable Architecture Overview</CardTitle>
                  <CardDescription>
                    Modular separation of concerns structured under <code>src/</code>.
                  </CardDescription>
                </CardHeader>
                <CardContent className="font-mono text-xs leading-relaxed space-y-2 text-muted-foreground">
                  <p><strong className="text-foreground">src/app/</strong>: App Router layouts, routes, loading, error, and health check API.</p>
                  <p><strong className="text-foreground">src/providers/</strong>: TanStack Query Provider with ReactQueryDevtools and SSR hydration.</p>
                  <p><strong className="text-foreground">src/components/ui/</strong>: shadcn/ui design tokens and primitives.</p>
                  <p><strong className="text-foreground">src/components/common/</strong>: Shared layout elements (Header, Footer, Nav).</p>
                  <p><strong className="text-foreground">src/config/</strong>: Type-safe Zod schema environment validation & site metadata.</p>
                  <p><strong className="text-foreground">src/hooks/queries/</strong>: Typed TanStack Query hooks.</p>
                  <p><strong className="text-foreground">src/services/</strong>: Business logic & API request definitions.</p>
                  <p><strong className="text-foreground">src/lib/</strong>: Core utilities (`cn`, `fetcher`, `query-client`).</p>
                  <p><strong className="text-foreground">tests/ & e2e/</strong>: Vitest unit test suite and Playwright multi-browser E2E suite.</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
      </main>

      {/* Features Grid */}
      <section id="features" className="w-full py-20">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold tracking-tight">
              Engineered for Production Excellence
            </h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-xl mx-auto">
              Everything required to scale an enterprise-level Next.js web application from day one.
            </p>
          </div>
      {/* Code Inspection Modal */}
      <CodeModal
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, idx) => (
              <Card key={idx} className="transition-all hover:shadow-md">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    {feature.icon}
                    <Badge variant="outline">{feature.badge}</Badge>
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
      />
    </div>
  );
}
