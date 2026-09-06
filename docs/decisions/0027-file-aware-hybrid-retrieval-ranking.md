# ADR 0027: File-Aware Hybrid Retrieval Ranking

## Status

Accepted

## Date

2026-09-06

## Context

The V2 retriever fused dense and BM25 chunk rankings with weighted reciprocal rank fusion. That produced strong chunk-level rankings, but the evaluation measures relevance by source file. A file with several nearby matching chunks could occupy several top-k positions and crowd out other relevant files. This was especially visible for schema, migration, compose, and integration-test queries.

The benchmark also contains repository-specific abbreviations such as `authz`, while users generally ask for "authorization". The existing tokenizer split code identifiers but did not normalize these equivalent terms.

## Decision

1. **Widen the candidate pool** from 20 to 40 candidates for the default top-five retrieval path. This gives file-level aggregation enough evidence when the best chunk from a relevant file is not among the first few chunk results.
2. **Aggregate scores at file level** before selecting the final results. The strongest chunk contributes its full fused score; the second and third strongest chunks contribute bounded weights of 0.2 and 0.1. This rewards files with multiple relevant sections without allowing large files to dominate.
3. **Return one representative chunk per file** in the final result set. The representative is the highest-scoring chunk and retains its exact line citation.
4. **Normalize common authorization abbreviations** in the BM25 tokenizer: `authz` expands to `authorization`, and `authorization` expands to `authz` and `auth`. This improves matching between natural-language questions and repository paths.
5. **Keep the cross-encoder disabled by default.** The existing web-trained MS MARCO reranker remains available but is not part of the default path because previous measurements showed lower retrieval quality and much higher latency on source code.

## Consequences

The final result list is file-diverse and better aligned with the benchmark's file-level ground truth. Retrieval still returns chunk content and exact citations, but repeated chunks from one file no longer consume the user's top-k context window.

On the 20-case retrieval suite, the measured result after this change was:

| Metric | Result |
|---|---:|
| Recall@5 | **100.0% (20/20)** |
| Recall@10 | **100.0% (20/20)** |
| Mean Reciprocal Rank | **0.7917** |
| Average search latency | **46.34 ms** |

The result depends on the current Qdrant corpus and local runtime; rerun `uv run python evals/run_eval.py` after changing ingestion, embeddings, or ranking logic.

## Validation

- `uv run python evals/run_eval.py`
- `uv run pytest tests/test_retriever.py -q`
- `uv run python -m compileall -q src/retrieval/retriever.py`
