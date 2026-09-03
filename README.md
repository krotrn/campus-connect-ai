# AEIA — AI Engineering Intelligence Assistant

> A grounded RAG system for the [Campus Connect](https://github.com/krotrn/campus-connect) codebase.
> Ask natural-language questions about the code and get cited, line-level answers.

---

## Quick Start

```bash
# 1. Bring up Qdrant
docker compose up -d qdrant

# 2. Ingest the corpus (first run ~24 min, subsequent runs ~30s via cache)
PYTHONPATH=. uv run python -m src.ingestion.pipeline

# 3. Start the API
PYTHONPATH=. uv run uvicorn src.api.main:app --reload

# 4. Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Where is user authentication implemented?"}'
```

---

## Retrieval Benchmark

Evaluated on **20 golden test cases** in [`evals/dataset.json`](evals/dataset.json).

| Version | Strategy | Recall@5 | Recall@10 | MRR | Latency |
|---------|----------|----------|-----------|-----|---------|
| **V1** | Dense vector only (BGE-small) | 70.0% | 85.0% | 0.638 | ~43ms |
| V2 — Rerank | Dense + cross-encoder (ms-marco) | 70.0% | 80.0% | 0.455 | 1453ms |
| V2 — Hybrid | Dense + BM25, equal RRF | 75.0% | 75.0% | 0.464 | 43ms |
| V2 — Weighted RRF | Dense (0.7) + BM25 (0.3) | 75.0% | 80.0% | 0.470 | 44ms |
| **V2 Final** ✅ | Weighted RRF + semantic prefixes | **85.0%** | **95.0%** | **0.588** | **45ms** |

> Run evals yourself: `PYTHONPATH=. uv run python evals/run_eval.py`

### What drove V2 improvements

| Change | Impact |
|--------|--------|
| BM25 + dense vector fusion (Weighted RRF 70/30) | +5% Recall@5 for exact keyword queries |
| Semantic prefix headers on YAML/SQL/env files | +10% Recall@5 — config files now discoverable by natural language |
| Dotfile ingestion (`.env.example`) | Fixed silent corpus gap |
| Content-hash embedding cache | Re-ingestion: 24 min → ~30 seconds |

### Remaining misses (3/20)

| Query | Expected Source | Status | Reason |
|-------|----------------|--------|--------|
| q007 — Redis dependencies | `compose.yml`, `ARCHITECTURE.md` | ⚠️ Rank 8 | TypeScript Redis usage files rank higher semantically |
| q017 — auth integration tests | `auth-helpers.test.ts` | ⚠️ Rank 8 | Query too abstract for file content |
| q018 — object storage | `compose.yml`, `ARCHITECTURE.md` | ❌ Missed | "object storage" / "MinIO" semantic gap still large |

---

## Architecture

```
corpus/ (Campus Connect ~94k LOC)
    ↓ CodeAwareChunker (TS/MD/Prisma/SQL/YAML aware)
    ↓ Semantic prefix enrichment (config files)
    ↓ BGE-small-en-v1.5 embeddings → Qdrant
                        ↓
Query → Dense retrieval + BM25 lexical → Weighted RRF fusion
                        ↓
              Gemini 1.5 Flash generator
                        ↓
         Grounded answer + [file#Lstart-Lend] citations
```

---

## Project Structure

```
src/
  api/          FastAPI server (POST /ask, GET /health)
  ingestion/    Chunker + pipeline (with embedding cache)
  retrieval/    Hybrid retriever (BM25 + dense + RRF)
  generation/   Gemini-powered grounded answer generator
  config.py     Pydantic settings
evals/
  dataset.json  20 golden test cases
  run_eval.py   Recall@5, Recall@10, MRR benchmark
docs/decisions/ 12 Architecture Decision Records (ADRs)
tests/          9 unit + integration tests
```

---

## Running Tests

```bash
uv run pytest
```

---

## ADRs

Key architectural decisions are documented in [`docs/decisions/`](docs/decisions/):

- [0005 — Code-Aware Chunking Strategy](docs/decisions/0005-code-aware-chunking-strategy.md)
- [0010 — Evaluation Dataset and Benchmark](docs/decisions/0010-evaluation-dataset-and-benchmark.md)
- [0012 — V2 Hybrid Retrieval and Semantic Prefixing](docs/decisions/0012-v2-hybrid-retrieval-and-semantic-prefixing.md)
