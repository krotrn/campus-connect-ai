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

### One-liner (for project subtitle)

> Production-grade agentic RAG system that answers natural-language questions about a 94K-LOC TypeScript codebase with verified citations, measured evaluation, and real-time knowledge sync.

---

## XYZ Bullet Points (Pick 4–6 for Your Resume)

### 1. Retrieval Quality (Most Impactful)

> **Achieved 85% Recall@5 and 95% Recall@10** on a 20-query golden benchmark, **by designing a hybrid retrieval pipeline** combining dense semantic search (BGE-small embeddings) with sparse BM25 lexical scoring, fused via Weighted Reciprocal Rank Fusion (70/30), and enriched with semantic prefix headers for non-code files.

### 2. Generation Quality

> **Achieved 100% Faithfulness and 0% hallucination rate** on RAG Triad evaluation (LLM-as-a-Judge benchmark), **by implementing grounded answer generation** with strict citation enforcement across Gemini 2.0 Flash, validated on code_location and config_schema_lookup categories.

### 3. Agentic Architecture

> **Built an agentic query routing system that handles 4 distinct tool actions** (code search, git history, commit diff, dependency graph) **with zero manual dispatch**, by implementing an explicit LangGraph state-machine router with regex fast-path and LLM fallback classification.

### 4. Production Hardening

> **Shipped a production-grade API with <45ms P95 retrieval latency and $0.00/query cost**, secured by API key authentication, rate limiting (slowapi), async background ingestion, and full request-lifecycle tracing via Langfuse — **validated by 14 automated test suites** and GitHub Actions CI.

### 5. Real-Time Knowledge Sync

> **Reduced re-indexing time from full-corpus rebuild to incremental delta-only updates in ~30s**, by implementing content-hash caching, deterministic chunk point IDs, GitHub webhook-triggered sync (HMAC-SHA256 verified), and thread-safe BM25 hot-reload with build-then-swap concurrency.

### 6. MCP Server

> **Exposed codebase intelligence as a standards-compliant MCP Server** with 5+ granular tools (`search_campus_connect`, `explain_codebase_query`, `get_commit_history`, etc.), enabling any MCP-compatible AI client to query the codebase — **following the 2026-07-28 stateless HTTP specification**.

### 7. Code-Aware Chunking

> **Improved retrieval precision for config and schema files by 15 percentage points** (Recall@5: 70% → 85%), by building multi-format syntax-aware chunkers: Tree-Sitter AST parsing for TypeScript/TSX, structural block parsing for Prisma schemas, YAML service slicing for Docker Compose, and heading-hierarchy preservation for Markdown.

### 8. Engineering Documentation

> **Authored 25 Architectural Decision Records (ADRs)**, a 5-part developer onboarding curriculum (~145KB), and failure postmortem case studies — demonstrating systematic technical decision-making and knowledge transfer at a professional engineering standard.

---

## Copy-Paste Resume Blocks

### Compact Version (Space-Constrained Resumes)

```
AI Engineering Intelligence Assistant (AEIA)        Python | FastAPI | LangGraph | Qdrant | Gemini
───────────────────────────────────────────────────────────────────────────────────────────────────
• Achieved 85% Recall@5 and 95% Recall@10 on a 20-query golden benchmark by designing a hybrid
  retrieval pipeline (dense BGE-small + sparse BM25) fused via Weighted Reciprocal Rank Fusion
  with semantic prefixes. 100% Faithfulness on RAG Triad evaluation (0% hallucination).

• Built an agentic LangGraph state-machine router dispatching queries across 4 tools (code search,
  git history, commit diff, dependency graph) with regex fast-path and LLM fallback.

• Shipped production-grade API with <45ms retrieval latency, $0.00/query cost, API key auth,
  rate limiting, async ingestion, full Langfuse tracing, and 14 automated test suites.

• Exposed codebase intelligence as a standards-compliant MCP Server (2026-07-28 spec) with 5+
  granular tools. Deployed live on Render with auto-sleep free tier.

• Implemented incremental delta-only re-indexing (~30s) with GitHub webhook triggers,
  content-hash caching, and thread-safe BM25 hot-reload using build-then-swap concurrency.
```

### Extended Version (Portfolio / Detailed Resumes)

```
AI Engineering Intelligence Assistant (AEIA)
Production-grade agentic RAG system for codebase intelligence                     [GitHub] [Live Demo]

Tech Stack: Python, FastAPI, LangGraph, Qdrant, Gemini 2.0 Flash, BGE-small,
            MCP, Langfuse, Tree-Sitter, Docker, GitHub Actions

• Achieved 85% Recall@5 and 95% Recall@10 on 20 golden test queries by designing
  hybrid retrieval (dense + BM25 via Weighted RRF 70/30) with semantic prefixes —
  a 21% improvement over baseline dense-only search.

• Achieved 100% Faithfulness and 0% hallucination rate on automated RAG Triad
  evaluation (Faithfulness, Answer Relevance, Context Precision) via LLM-as-a-Judge.

• Built agentic LangGraph state-machine routing queries across 4 tool actions
  (code search, git log, commit diff, dependency graph) with zero manual dispatch.

• Shipped production API: <45ms P95 retrieval, $0.00/query cost, API key auth,
  rate limiting, async background ingestion, and full request-lifecycle Langfuse tracing.

• Implemented real-time knowledge sync: GitHub webhook-triggered incremental
  delta-only re-indexing (~30s), content-hash caching, and thread-safe BM25
  hot-reload with build-then-swap concurrency.

• Exposed intelligence as MCP Server (2026-07-28 spec) with 5+ granular tools.
  Deployed live on Render free tier.

• Built multi-format syntax-aware chunkers: Tree-Sitter AST for TS/TSX, structural
  block parsing for Prisma, YAML service slicing, and Markdown hierarchy preservation.

• Authored 25 ADRs, a 5-part developer onboarding curriculum (~145KB), and failure
  postmortem case studies documenting systematic engineering decisions.
```

---

## Interview Talking Points

When asked "Tell me about this project," hit these in order:

1. **Problem** — "Developers waste hours grepping across code, docs, git history, and configs. I built a system that answers those questions in natural language with citations."
2. **Scale** — "It indexes a 94K-LOC TypeScript monorepo — 808 files across code, Prisma schemas, Docker configs, and Markdown docs."
3. **Measured Quality** — "I built a 20-query golden benchmark and iterated retrieval from 70% to 85% Recall@5 across 7 versions, with before/after numbers for every change. Generation quality is 100% Faithful with 0% hallucination."
4. **Production Engineering** — "It's not a notebook. It has API auth, rate limiting, async ingestion, observability tracing, incremental re-indexing, 14 test suites, and it's deployed live."
5. **Agentic Design** — "I built a LangGraph state machine that routes between RAG search, git tools, and dependency analysis — not an ad-hoc loop."
6. **Staying Current** — "I exposed it as an MCP Server following the 2026 spec, so any MCP-compatible client can use it as a tool."
7. **Zero Cost** — "The entire system runs on free-tier components: local BGE-small embeddings, Gemini free tier, self-hosted Qdrant, deployed on Render free tier."

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
