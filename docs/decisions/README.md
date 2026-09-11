# Architectural Decision Records (ADRs)

This directory documents the key architectural and technical decisions made for the AI Engineering Intelligence Assistant (AEIA).

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-target-corpus.md) | Selection of Target Corpus (`campus-connect`) | Accepted | 2026-09-02 |
| [0002](0002-zero-cost-embedding-and-vector-db.md) | Vector Database and Local Embedding Model Selection | Accepted | 2026-09-02 |
| [0003](0003-llm-provider-gemini.md) | LLM Provider for V1 Answer Generation | Accepted | 2026-09-02 |
| [0004](0004-python-toolchain-uv.md) | Python Toolchain and Environment Management | Accepted | 2026-09-02 |
| [0005](0005-code-aware-chunking-strategy.md) | Code-Aware Chunking Strategy with Exact Line Citations | Accepted | 2026-09-02 |
| [0006](0006-gpu-acceleration-for-embeddings.md) | Local Ingestion Embedding Execution: CPU vs. GPU Trade-Off | Accepted | 2026-09-03 |
| [0007](0007-grounded-retrieval-and-citations.md) | Grounded Retrieval and Source Citation Architecture | Accepted | 2026-09-03 |
| [0008](0008-fastapi-service-interface.md) | FastAPI Service Interface and Latency Instrumentation | Accepted | 2026-09-03 |
| [0009](0009-docker-containerization.md) | Containerization and Multi-Service Topology | Accepted | 2026-09-03 |
| [0010](0010-evaluation-dataset-and-benchmark.md) | Evaluation Dataset Specification and Automated Retrieval Benchmarking | Accepted | 2026-09-03 |
| [0011](0011-automated-testing-strategy.md) | Automated Testing Architecture (Unit, Integration, and Regression) | Accepted | 2026-09-03 |
| [0012](0012-v2-hybrid-retrieval-and-semantic-prefixing.md) | V2 Hybrid Retrieval (BM25 + Dense RRF) and Semantic Prefixing | Accepted | 2026-09-04 |
| [0013](0013-v3-production-hardening.md) | V3 Production Hardening (Auth, Rate Limiting, CORS, CI) | Accepted | 2026-09-04 |
| [0014](0014-v4-observability-langfuse-tracing.md) | V4 Observability & Evaluation with Langfuse Tracing | Accepted | 2026-09-04 |
| [0015](0015-v5-agentic-router-langgraph.md) | V5 Agentic Query Router & Non-RAG State Graph | Accepted | 2026-09-04 |
| [0016](0016-v6-model-context-protocol-server.md) | V6 Model Context Protocol (MCP) Server (2026-07-28 Spec) | Accepted | 2026-09-05 |
| [0017](0017-error-handling-and-upstream-degradation.md) | Error Handling Hierarchy and Upstream Graceful Degradation | Accepted | 2026-09-05 |
| [0018](0018-bm25-thread-safe-hot-reload.md) | Thread-Safe BM25 In-Memory Index Hot-Reload | Accepted | 2026-09-06 |
| [0019](0019-git-corpus-sync-and-diff-tracking.md) | Automated Git Synchronization and Diff Tracking | Accepted | 2026-09-06 |
| [0020](0020-incremental-delta-only-ingestion.md) | Incremental Delta-Only Ingestion with Deterministic Point IDs | Accepted | 2026-09-06 |
| [0021](0021-github-push-webhook-automation.md) | GitHub Push Webhook Automation with HMAC-SHA256 Authentication | Accepted | 2026-09-06 |
| [0022](0022-interactive-web-playground-ui.md) | Interactive Web UI Playground & Visual Citation Inspector | Superseded | 2026-09-06 |
| [0023](0023-multi-format-syntax-aware-chunking.md) | Multi-Format Syntax-Aware Chunking (Tree-Sitter AST & Structural Block Parsers) | Accepted | 2026-09-06 |
| [0024](0024-rag-triad-generation-evaluation.md) | Automated RAG Triad Generation Evaluation Suite | Accepted | 2026-09-06 |
| [0025](0025-conversational-memory-and-coreference-rewriter.md) | Multi-Turn Conversational Memory & Coreference Query Rewriting | Accepted | 2026-09-06 |
| [0026](0026-real-time-sse-token-streaming-and-chat-sdk.md) | Real-Time Server-Sent Events (SSE) Token Streaming & Chat SDK Alignment | Accepted | 2026-09-06 |
| [0027](0027-file-aware-hybrid-retrieval-ranking.md) | File-Aware Hybrid Retrieval Ranking | Accepted | 2026-09-06 |
| [0028](0028-decoupled-nextjs-frontend-console.md) | Decoupled Next.js Frontend Console & Retirement of Static Single-File UI | Accepted | 2026-09-07 |
| [0029](0029-client-side-api-key-injection-and-quota-resilience.md) | Client-Side Dynamic API Key Injection & LLM Quota Resilience | Accepted | 2026-09-07 |
| [0030](0030-unified-sse-streaming-protocol-for-rag-and-agent.md) | Unified Server-Sent Events (SSE) Streaming Protocol for RAG & Agentic Routing | Accepted | 2026-09-07 |
| [0031](0031-codebase-type-modernization-and-ingestion-telemetry.md) | Modernized Python 3.12+ Type Annotation Standard & Ingestion Progress Instrumentation | Accepted | 2026-09-07 |
| [0032](0032-production-hardening-credential-boundary-and-async-correctness.md) | Production Hardening: Credential Boundary, Async Correctness & Offline Test Strategy | Accepted | 2026-09-11 |
