# AEIA — Resume Project Write-Up (Google XYZ Format)

## What is Google XYZ Format?

> **"Accomplished [X] as measured by [Y], by doing [Z]."**
>
> — **X** = What you did (the impact/result)
> — **Y** = How it was measured (quantifiable proof)
> — **Z** = How you did it (the method/tech)

---

## Project Title

**AI Engineering Intelligence Assistant (AEIA)** — *Agentic RAG Code Intelligence System*
**AI Engineering Intelligence Assistant (AEIA)** — *Full-Stack Agentic RAG Code Intelligence System*

### One-liner (for project subtitle)

> Production-grade agentic RAG system that answers natural-language questions about a 94K-LOC TypeScript codebase with verified citations, measured evaluation, and real-time knowledge sync.
> Production-grade full-stack agentic RAG platform that answers natural-language questions about a 94K-LOC TypeScript codebase with verified citations, measured evaluation, real-time SSE streaming, and a modern Next.js console.

---

## XYZ Bullet Points (Pick 4–6 for Your Resume)

### 1. Retrieval Quality (Most Impactful)

> **Achieved 85% Recall@5 and 95% Recall@10** on a 20-query golden benchmark, **by designing a hybrid retrieval pipeline** combining dense semantic search (BGE-small embeddings) with sparse BM25 lexical scoring, fused via Weighted Reciprocal Rank Fusion (70/30), and enriched with semantic prefix headers for non-code files.
> **Achieved 100% Recall@5 and 100% Recall@10 with 0.7917 MRR** on a 20-query golden benchmark, **by designing a file-aware hybrid retrieval pipeline** combining dense semantic search (BGE-small embeddings) with sparse BM25 scoring, fused via Weighted Reciprocal Rank Fusion (70/30), and enriched with semantic prefix headers for non-code files.

### 2. Generation Quality
### 2. Generation Quality & RAG Triad

> **Achieved 100% Faithfulness and 0% hallucination rate** on RAG Triad evaluation (LLM-as-a-Judge benchmark), **by implementing grounded answer generation** with strict citation enforcement across Gemini 2.0 Flash, validated on code_location and config_schema_lookup categories.
> **Achieved 100% Faithfulness and 0% hallucination rate** on RAG Triad evaluation (automated LLM-as-a-Judge benchmark), **by implementing grounded answer generation** with strict citation enforcement across Gemini models, validated on code_location and config_schema_lookup categories.

### 3. Agentic Architecture
### 3. Agentic Architecture & Unified Streaming

> **Built an agentic query routing system that handles 4 distinct tool actions** (code search, git history, commit diff, dependency graph) **with zero manual dispatch**, by implementing an explicit LangGraph state-machine router with regex fast-path and LLM fallback classification.
> **Built an agentic routing and tool execution engine that handles 4 distinct workflows** (code search, git history, commit diff, dependency graph) **with real-time Server-Sent Events (SSE) streaming (<400ms TTFT)**, by implementing an explicit LangGraph state-machine router with regex fast-path and unified streaming event contracts.

### 4. Production Hardening
### 4. Full-Stack Web Console & Quota Resilience

> **Shipped a production-grade API with <45ms P95 retrieval latency and $0.00/query cost**, secured by API key authentication, rate limiting (slowapi), async background ingestion, and full request-lifecycle tracing via Langfuse — **validated by 14 automated test suites** and GitHub Actions CI.
> **Engineered an enterprise-grade web console using Next.js 16, React 19, TypeScript, and Tailwind CSS v4**, featuring an interactive slide-over code inspector for hallucination verification and dynamic client-side Gemini API key injection with animated backoff recovery — **eliminating shared server quota lockouts during recruiter and team demos**.

### 5. Real-Time Knowledge Sync
### 5. Production Hardening & Observability

> **Shipped a production API with <45ms P95 retrieval latency and $0.00/query cost**, secured by API key authentication, rate limiting (slowapi), async background ingestion, and full request-lifecycle tracing via Langfuse — **validated by 16 backend test suites, Vitest component tests, and Playwright E2E automation**.

### 6. Real-Time Knowledge Sync

> **Reduced re-indexing time from full-corpus rebuild to incremental delta-only updates in ~30s**, by implementing content-hash caching, deterministic chunk point IDs, GitHub webhook-triggered sync (HMAC-SHA256 verified), and thread-safe BM25 hot-reload with build-then-swap concurrency.

### 6. MCP Server
### 7. Standards-Compliant MCP Server

> **Exposed codebase intelligence as a standards-compliant MCP Server** with 5+ granular tools (`search_campus_connect`, `explain_codebase_query`, `get_commit_history`, etc.), enabling any MCP-compatible AI client to query the codebase — **following the 2026-07-28 stateless HTTP specification**.
> **Exposed codebase intelligence as an official Model Context Protocol (MCP) Server** with 5+ granular tools (`search_campus_connect`, `explain_codebase_query`, `get_commit_history`, etc.), enabling IDEs, Cursor, and Claude Desktop to query the codebase — **following the 2026-07-28 stateless HTTP specification**.

### 7. Code-Aware Chunking
### 8. Multi-Format Syntax-Aware Chunking

> **Improved retrieval precision for config and schema files by 15 percentage points** (Recall@5: 70% → 85%), by building multi-format syntax-aware chunkers: Tree-Sitter AST parsing for TypeScript/TSX, structural block parsing for Prisma schemas, YAML service slicing for Docker Compose, and heading-hierarchy preservation for Markdown.
> **Eliminated boundary-split hallucinations across code and configuration files**, by building multi-format syntax-aware chunkers: Tree-Sitter AST parsing for TypeScript/TSX (preserving functions, classes, interfaces, and JSDoc blocks), structural block parsing for Prisma schemas, YAML service slicing for Docker Compose, and heading-hierarchy preservation for Markdown.

### 8. Engineering Documentation
### 9. Engineering Documentation & ADRs

> **Authored 25 Architectural Decision Records (ADRs)**, a 5-part developer onboarding curriculum (~145KB), and failure postmortem case studies — demonstrating systematic technical decision-making and knowledge transfer at a professional engineering standard.
> **Authored 31 Architectural Decision Records (ADRs)**, a 5-part developer onboarding curriculum (~150KB), and failure postmortem case studies — demonstrating systematic technical decision-making and knowledge transfer at a professional engineering standard.

---

## Copy-Paste Resume Blocks

### Compact Version (Space-Constrained Resumes)

```
AI Engineering Intelligence Assistant (AEIA)        Python | FastAPI | LangGraph | Qdrant | Gemini
───────────────────────────────────────────────────────────────────────────────────────────────────
• Achieved 85% Recall@5 and 95% Recall@10 on a 20-query golden benchmark by designing a hybrid
  retrieval pipeline (dense BGE-small + sparse BM25) fused via Weighted Reciprocal Rank Fusion
  with semantic prefixes. 100% Faithfulness on RAG Triad evaluation (0% hallucination).
```text
AI Engineering Intelligence Assistant (AEIA)    Python | FastAPI | Next.js 16 | LangGraph | Qdrant | Gemini
───────────────────────────────────────────────────────────────────────────────────────────────────────────
• Achieved 100% Recall@5 and 100% Recall@10 (0.7917 MRR) on 20 golden queries via file-aware hybrid
  retrieval (dense BGE-small + BM25 70/30 RRF) and semantic prefixes; 100% Faithfulness on RAG Triad.

• Built an agentic LangGraph state-machine router dispatching queries across 4 tools (code search,
  git history, commit diff, dependency graph) with regex fast-path and LLM fallback.
  git log, commit diff, dependency graph) with unified Server-Sent Events (SSE) token streaming (TTFT <400ms).

• Shipped production-grade API with <45ms retrieval latency, $0.00/query cost, API key auth,
  rate limiting, async ingestion, full Langfuse tracing, and 14 automated test suites.
• Engineered a decoupled Next.js 16 / React 19 web console with interactive visual citation inspector,
  dynamic client-side Gemini API key injection, and automated quota recovery alerts.

• Exposed codebase intelligence as a standards-compliant MCP Server (2026-07-28 spec) with 5+
  granular tools. Deployed live on Render with auto-sleep free tier.
• Shipped production API with <45ms retrieval, $0.00/query cost, API key auth, rate limiting, async ingestion,
  full Langfuse tracing, and comprehensive CI coverage (16 pytest suites + Vitest + Playwright).

• Implemented incremental delta-only re-indexing (~30s) with GitHub webhook triggers,
  content-hash caching, and thread-safe BM25 hot-reload using build-then-swap concurrency.
• Exposed codebase intelligence as a standards-compliant MCP Server (2026-07-28 spec) and built
  incremental delta-only re-indexing (~30s) triggered via cryptographically verified GitHub webhooks.
```

### Extended Version (Portfolio / Detailed Resumes)

```
```text
AI Engineering Intelligence Assistant (AEIA)
Production-grade agentic RAG system for codebase intelligence                     [GitHub] [Live Demo]
Production-grade full-stack agentic RAG platform for codebase intelligence        [GitHub] [Vercel Demo]

Tech Stack: Python, FastAPI, LangGraph, Qdrant, Gemini 2.0 Flash, BGE-small,
            MCP, Langfuse, Tree-Sitter, Docker, GitHub Actions
Tech Stack: Python 3.12+, FastAPI, Next.js 16, React 19, TypeScript, Tailwind CSS v4,
            LangGraph, Qdrant, Google Gemini, BGE-small, MCP, Langfuse, Tree-Sitter, Docker

• Achieved 85% Recall@5 and 95% Recall@10 on 20 golden test queries by designing
  hybrid retrieval (dense + BM25 via Weighted RRF 70/30) with semantic prefixes —
  a 21% improvement over baseline dense-only search.
• Achieved 100% Recall@5, 100% Recall@10, and 0.7917 MRR on a 20-query golden benchmark by designing
  file-aware hybrid retrieval (dense + lexical BM25 fused via Weighted RRF 70/30) with semantic prefixes.

• Achieved 100% Faithfulness and 0% hallucination rate on automated RAG Triad
  evaluation (Faithfulness, Answer Relevance, Context Precision) via LLM-as-a-Judge.
• Achieved 100% Faithfulness and 0% hallucination rate on automated RAG Triad evaluation
  (Faithfulness, Answer Relevance, Context Precision) using LLM-as-a-Judge benchmarking.

• Built agentic LangGraph state-machine routing queries across 4 tool actions
  (code search, git log, commit diff, dependency graph) with zero manual dispatch.
• Built an agentic LangGraph router and unified Server-Sent Events (SSE) streaming engine delivering
  sub-400ms TTFT across RAG search and deterministic tools (commit inspection, git history, dependency graph).

• Shipped production API: <45ms P95 retrieval, $0.00/query cost, API key auth,
  rate limiting, async background ingestion, and full request-lifecycle Langfuse tracing.
• Engineered a responsive Next.js 16 web console (App Router, Tailwind v4, shadcn/ui) featuring a slide-over
  code inspector for line-level grounding verification and client-side Gemini API key injection for quota resilience.

• Implemented real-time knowledge sync: GitHub webhook-triggered incremental
  delta-only re-indexing (~30s), content-hash caching, and thread-safe BM25
  hot-reload with build-then-swap concurrency.
• Shipped production-grade infrastructure: <45ms retrieval, $0.00/query cost, API key security, rate limiting,
  async background ingestion, Langfuse request tracing, and automated testing (16 backend suites + Vitest + Playwright).

• Exposed intelligence as MCP Server (2026-07-28 spec) with 5+ granular tools.
  Deployed live on Render free tier.
• Built real-time knowledge sync: incremental delta-only re-indexing (~30s) with deterministic point IDs,
  content-hash caching, HMAC-SHA256 GitHub push webhooks, and thread-safe BM25 hot-reload.

• Built multi-format syntax-aware chunkers: Tree-Sitter AST for TS/TSX, structural
  block parsing for Prisma, YAML service slicing, and Markdown hierarchy preservation.
• Exposed intelligence as a standards-compliant MCP Server (2026-07-28 stateless HTTP spec) with 5+ tools.

• Authored 25 ADRs, a 5-part developer onboarding curriculum (~145KB), and failure
  postmortem case studies documenting systematic engineering decisions.
• Authored 31 Architectural Decision Records (ADRs) and a 5-part developer curriculum (~150KB).
```

---

## Interview Talking Points

When asked "Tell me about this project," hit these in order:

1. **Problem** — "Developers waste hours grepping across code, docs, git history, and configs. I built a system that answers those questions in natural language with citations."
1. **Problem** — "Developers waste hours grepping across code, docs, git history, and configs. I built a full-stack system that answers those questions in natural language with verified line citations."
2. **Scale** — "It indexes a 94K-LOC TypeScript monorepo — 808 files across code, Prisma schemas, Docker configs, and Markdown docs."
3. **Measured Quality** — "I built a 20-query golden benchmark and iterated retrieval from 70% to 85% Recall@5 across 7 versions, with before/after numbers for every change. Generation quality is 100% Faithful with 0% hallucination."
4. **Production Engineering** — "It's not a notebook. It has API auth, rate limiting, async ingestion, observability tracing, incremental re-indexing, 14 test suites, and it's deployed live."
5. **Agentic Design** — "I built a LangGraph state machine that routes between RAG search, git tools, and dependency analysis — not an ad-hoc loop."
6. **Staying Current** — "I exposed it as an MCP Server following the 2026 spec, so any MCP-compatible client can use it as a tool."
7. **Zero Cost** — "The entire system runs on free-tier components: local BGE-small embeddings, Gemini free tier, self-hosted Qdrant, deployed on Render free tier."
3. **Measured Quality** — "I built a 20-query golden benchmark and iterated retrieval from 70% to 100% Recall@5 and 100% Recall@10 (0.7917 MRR) across versions. Generation quality is evaluated at 100% Faithful with 0% hallucination using the RAG Triad framework."
4. **Full-Stack & UX** — "I built a modern Next.js 16 console with real-time SSE token streaming, a slide-over code inspector to verify grounding, and client-side API key injection so demo visitors never hit shared quota lockouts."
5. **Agentic Design** — "I used a LangGraph state machine that routes between RAG search, git tools, and dependency analysis under a unified streaming protocol — not an ad-hoc loop."
6. **Standards & Protocol** — "I exposed it as an official Model Context Protocol (MCP) Server following the 2026 spec, so any MCP client like Cursor or Claude Desktop can use it."
7. **Production Engineering** — "It has API auth, rate limiting, async queue ingestion, distributed Langfuse tracing, incremental delta updates in ~30s, 16 backend test suites, and runs entirely on free-tier components (\$0.00/query cost)."

---

## Tech Stack Summary (for Skills Section)

| Category | Technologies |
|----------|-------------|
| Language | Python 3.14 |
| Framework | FastAPI, Pydantic |
| AI/ML | Google Gemini 2.0 Flash, BGE-small-en-v1.5 (FastEmbed), LangGraph |
| Retrieval | Qdrant (vector DB), BM25 (rank-bm25), Reciprocal Rank Fusion, FlashRank |
| Parsing | Tree-Sitter (AST), LangChain Text Splitters |
| Protocols | Model Context Protocol (MCP) 2026-07-28 spec |
| Observability | Langfuse (tracing), structured logging |
| Infrastructure | Docker, Docker Compose, Render (deployment) |
| Testing | pytest, pytest-asyncio |
| CI/CD | GitHub Actions |
| :--- | :--- |
| **Backend & API** | Python 3.12+, FastAPI, Uvicorn, Pydantic V2, slowapi |
| **Frontend & UI** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query |
| **AI / Agentic** | Google Gemini (2.0 Flash / 3.6 Flash), LangGraph (StateGraph), Google GenAI SDK |
| **Retrieval & Embeddings** | Qdrant (HNSW vector DB), BM25 (rank-bm25), BGE-small-en-v1.5 (FastEmbed), Weighted RRF |
| **Code Parsing** | Tree-Sitter AST (TypeScript/TSX), Structural Block Parsers (Prisma, YAML, SQL, Markdown) |
| **Protocols & Standards** | Model Context Protocol (MCP) 2026-07-28 spec, Server-Sent Events (SSE) |
| **Observability** | Langfuse (distributed tracing & spans), structured JSON telemetry |
| **Testing & CI** | pytest, pytest-asyncio, Vitest, React Testing Library, Playwright, GitHub Actions |
| **Deployment & Cloud** | Docker, Docker Compose, Vercel (Edge Frontend), Render / Railway, Qdrant Cloud |
