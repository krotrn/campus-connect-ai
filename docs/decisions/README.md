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
