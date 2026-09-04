# ADR 0014: V4 Observability — Langfuse Tracing and Failure Post-Mortems

## Status
Accepted

## Date
2026-09-05

## Context

After V3 hardened the API (auth, rate limiting, CI), the system lacked visibility into production behavior. Key unknowns:
- How much time is spent in retrieval vs. generation per query?
- What are the retrieval scores and which files surface most often?
- What does the Gemini model cost per query?
- Why do certain queries fail, and how do we document and learn from failures?

Without observability, debugging retrieval quality issues (like the schema.prisma semantic bias discovered in V2) required ad-hoc scripts and manual analysis.

## Decision

### 1. Langfuse Integration (FR4.1 & FR4.2)

Integrate the Langfuse Python SDK to capture structured traces for every `/ask` request.

**Architecture**: A dedicated `src/observability/` module wraps the RAG pipeline with Langfuse spans:

```
Trace: rag-ask
├── Span: retrieval
│   ├── input: query, top_k
│   ├── output: num_chunks, top_files, top_scores
│   └── metadata: latency_ms
└── Generation: gemini-generate
    ├── input: question, context_chunks count
    ├── model: gemini-2.5-flash-lite
    ├── output: answer (trimmed)
    └── metadata: latency_ms, answer_length
```

**Graceful degradation**: If `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are not set in `.env`, all tracing is silently skipped. The `traced_ask()` function falls back to direct execution with zero overhead. This means:
- Local development works without a Langfuse account
- Tests pass without Langfuse configuration
- Production enables tracing by adding 3 env vars

**Why Langfuse over alternatives**:
- **vs. custom logging**: Langfuse provides a structured trace UI, cost tracking, and evaluation tools out of the box.
- **vs. LangSmith**: Langfuse is open-source, self-hostable, and has a generous free tier. LangSmith is LangChain-specific and proprietary.
- **vs. OpenTelemetry directly**: Langfuse is purpose-built for LLM observability with first-class support for generations, retrieval spans, and token usage. Generic OTel would require custom instrumentation for all of these.

### 2. Traced Data Points

Each trace captures:

| Data Point | Where | Purpose |
|-----------|-------|---------|
| Query text + top_k | Trace input | Replay and debug queries |
| Retrieval latency (ms) | Retrieval span | Identify slow searches |
| Top 5 file paths | Retrieval span output | See which files surface most |
| Top 5 retrieval scores | Retrieval span output | Detect low-confidence retrievals |
| Generation model name | Generation span | Track model versions |
| Generation latency (ms) | Generation span | Isolate LLM bottlenecks |
| Answer length | Generation metadata | Detect truncated or empty responses |
| Total latency (ms) | Trace metadata | End-to-end SLA tracking |

### 3. Documented Failure Investigation (FR4.3)

Write a structured post-mortem for the V2 semantic bias issue as a documented case study in `docs/postmortems/`. The post-mortem follows a standard format:
- Timeline of events
- Root cause analysis with code examples
- Embedding space visualization (conceptual)
- Quantified impact (before/after metrics)
- Lessons learned

This creates an institutional knowledge base for future debugging.

## Files Changed

| File | Change |
|------|--------|
| `src/config.py` | Added `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host` settings |
| `src/observability/__init__.py` | **New** — Langfuse client init, `traced_ask()` with retrieval + generation spans |
| `src/api/main.py` | Wired `init_langfuse()` into lifespan, `/ask` now uses `traced_ask()` |
| `pyproject.toml` | Added `langfuse` dependency |
| `docs/postmortems/001-semantic-bias-config-retrieval.md` | **New** — V2 failure investigation case study |

## Consequences

### Positive
- Every `/ask` request is automatically traced with retrieval and generation metrics.
- Langfuse dashboard provides real-time visibility into query performance, cost, and retrieval quality.
- Zero-config local development — tracing is disabled unless Langfuse keys are set.
- Post-mortem document captures institutional knowledge about embedding model limitations.
- Trace data can feed back into evaluation pipeline to identify new failure modes.

### Negative / Open Items
- Langfuse adds a network dependency for trace submission (async, non-blocking, but still external).
- Free Langfuse Cloud tier has retention limits — self-hosting may be needed for long-term data.
- Token usage tracking requires Gemini API to return usage metadata — currently not captured (future improvement).
- No automated alerting on degraded retrieval scores — manual dashboard monitoring for now.
