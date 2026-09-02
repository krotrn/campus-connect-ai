# ADR 0010: Evaluation Dataset Specification and Automated Retrieval Benchmarking

## Status
Accepted

## Date
2026-09-03

## Context
PRD Goals #2 and #10 mandate proving retrieval and answer quality with measured evaluation metrics tracked over versions. In RAG systems, engineering decisions (chunk size, overlap, embedding model, hybrid search, reranking) should be data-driven rather than speculative.

To evaluate V1 and establish a measurable baseline before adding hybrid search and reranking in V2, we require:
1. A hand-labeled golden evaluation dataset covering all 7 core use cases.
2. Standardized information retrieval metrics (Recall@5, Recall@10, Mean Reciprocal Rank, Search Latency).
3. Automated execution tooling runnable locally and in CI/CD.

## Decision
1. **Dataset (`evals/dataset.json`)**:
   - 20 labeled test cases mapped across:
     - `architecture_navigation` (3 items)
     - `code_location` (4 items)
     - `change_analysis` (2 items)
     - `debugging_assistance` (2 items)
     - `dependency_reasoning` (2 items)
     - `onboarding` (3 items)
     - `config_schema_lookup` (4 items)
   - Schema defines: `id`, `category`, `question`, `expected_sources` (list of matching file paths), `expected_answer_summary`.
2. **Benchmark Runner (`evals/run_eval.py`)**:
   - Queries the active retriever for top-10 chunks.
   - Computes:
     - **Recall@K**: Proportion of queries where at least one expected source is present in the top-$K$ chunks.
     - **Mean Reciprocal Rank (MRR)**: \(\frac{1}{|Q|}\sum \frac{1}{\text{rank}_i}\), rewarding systems that place ground-truth sources at Rank 1.
     - **Latency**: End-to-end vector search latency per query.

## V1 Baseline Results
```
Total Test Cases:       20
Recall@5:               70.0% (14/20)
Recall@10:              85.0% (17/20)
Mean Reciprocal Rank:   0.6384
Average Search Latency: 34.66 ms
```

## Consequences
- **Positive**: Clear empirical baseline established. We can quantitatively measure the impact of adding BM25 (V2.3) and Reranking (V2.4).
- **Positive**: Identified exact failure modes (e.g. config file lookup and specific migration commit queries) that require lexical matching.

