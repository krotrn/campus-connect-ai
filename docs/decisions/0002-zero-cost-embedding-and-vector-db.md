# ADR 0002: Vector Database and Local Embedding Model Selection

## Status
Accepted

## Date
2026-09-02

## Context
Ingesting a repository of ~94k LOC creates thousands of code and documentation chunks. Commercial embedding APIs (OpenAI `text-embedding-3-small`, etc.) introduce API costs, network latency, and strict rate limits during batch ingestion runs. Furthermore, early iterations of chunking strategies require re-indexing the corpus multiple times, which amplifies cost.

We need an embedding and storage layer that:
1. Incurs zero dollar cost ($0).
2. Has no rate limits or network dependencies during local development.
3. Provides production-grade vector similarity search with rich metadata filtering (filtering by filepath, extension, module).

## Decision
1. **Embedding Engine**: **FastEmbed** (`BAAI/bge-small-en-v1.5`)
   - Uses ONNX Runtime under the hood for optimized local CPU/GPU execution.
   - Generates 384-dimensional dense vectors.
   - 100% free and offline; zero rate limits.
2. **Vector Database**: **Qdrant**
   - Run as an official Docker container (`qdrant/qdrant:latest`) exposing REST (6333) and gRPC (6334).
   - Stores vectors and JSON payload metadata with payload indexing for file-level filtering.

## Consequences
- **Positive**: Zero cost, high batch throughput on local CPU, repeatable re-indexing without cost anxiety.
- **Positive**: Qdrant provides a built-in web dashboard at `http://localhost:6333/dashboard` for visual inspection of embeddings and payloads.
- **Negative**: 384-dim embeddings have slightly lower semantic capacity than 1536-dim or 3072-dim models, which will be addressed in V2 via hybrid retrieval (BM25 + vector) and reranking.

