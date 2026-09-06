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
  Code2,
  Boxes,
  Terminal,
  ArrowRight,
  Database,
  RefreshCw,
} from "lucide-react";

export default function Home() {
  const [searchTerm, setSearchTerm] = React.useState("");
  const debouncedSearch = useDebounce(searchTerm, 300);
  const [isCopied, setIsCopied] = React.useState(false);

  const { data: healthData, isPending: isHealthLoading, isFetching: isHealthFetching, refetch: refetchHealth } = useHealthQuery();

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

  const candidates = [
    { id: 1, name: "Alex Morgan", role: "Senior Fullstack Engineer", experience: "6 yrs", tag: "React, Node" },
    { id: 2, name: "Sarah Chen", role: "Lead Frontend Architect", experience: "8 yrs", tag: "Next.js, TypeScript" },
    { id: 3, name: "David Kim", role: "DevOps & Cloud Engineer", experience: "5 yrs", tag: "Kubernetes, AWS" },
    { id: 4, name: "Emily Watson", role: "Product Designer", experience: "4 yrs", tag: "Figma, UI Systems" },
  ];

  const filteredCandidates = candidates.filter(
    (c) =>
      c.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      c.role.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
      c.tag.toLowerCase().includes(debouncedSearch.toLowerCase())
  );

  const copyCommand = () => {
    navigator.clipboard.writeText("pnpm run test && pnpm run build");
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
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

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
            Next.js 16 + TanStack Query{" "}
            <span className="bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 bg-clip-text text-transparent">
              Production Architecture
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-base text-muted-foreground sm:text-lg">
            A production-ready foundation with strict TypeScript, clean folder
            architecture, TanStack Query v5, shadcn/ui components, Vitest unit testing, Playwright
            E2E, and automated CI pipelines.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <a
              href="#demo"
              className={buttonVariants({ size: "lg", className: "gap-2" })}
            >
              <span>Try Live Interactive Demo</span>
              <ArrowRight className="size-4" />
            </a>
            <Button
              variant="outline"
              size="lg"
              onClick={copyCommand}
              className="gap-2 font-mono text-xs"
            >
              <Terminal className="size-4" />
              <span>{isCopied ? "Copied to clipboard!" : "pnpm run test"}</span>
            </Button>
          </div>
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
          </div>

          <Tabs defaultValue="query" className="w-full">
            <div className="flex justify-center mb-6">
              <TabsList>
                <TabsTrigger value="query">TanStack Query Demo</TabsTrigger>
                <TabsTrigger value="candidates">Candidate Search Demo</TabsTrigger>
                <TabsTrigger value="architecture">Directory Specs</TabsTrigger>
              </TabsList>
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
      </section>

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
    </div>
  );
}
