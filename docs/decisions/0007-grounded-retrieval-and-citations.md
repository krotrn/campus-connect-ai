# ADR 0007: Grounded Retrieval and Source Citation Architecture

## Status
Accepted

## Date
2026-09-03

## Context
A major failure mode in developer assistants is hallucinating non-existent APIs, files, or functions. PRD Functional Requirement FR1.3 mandates that all LLM answers must be strictly grounded in retrieved code/docs chunks with clickable source citations referencing file paths and exact line numbers (`[src/lib/auth.ts#L10-L45]`).

To satisfy this, the generation subsystem must:
1. Retrieve the top-$K$ most semantically relevant chunks from Qdrant using the same embedding space (`BAAI/bge-small-en-v1.5`).
2. Format retrieved chunks into an unambiguous context block where each chunk is labeled with its citation tag `[file_path#Lstart-Lend]`.
3. Provide a strict grounding prompt instructing the LLM:
   - To rely solely on the provided context.
   - To cite every factual claim with its source tag.
   - To explicitly state when the requested information is absent from the corpus, preventing hallucinations.

## Decision
1. **Retriever (`src/retrieval/retriever.py`)**:
   - Embeds user queries using `FastEmbed(model_name="BAAI/bge-small-en-v1.5")`.
   - Queries Qdrant collection `campus_connect` using cosine similarity, returning top-$K$ (default $K=5$) chunks with metadata (`file_path`, `start_line`, `end_line`, `file_type`, `score`).
2. **Grounded Generation (`src/generation/generator.py`)**:
   - Uses Google Gemini (`gemini-2.0-flash`) via the `google-genai` SDK.
   - Enforces structured JSON output schema returning:
     - `answer`: Natural language explanation answering the question with inline citations.
     - `sources`: List of distinct source objects `{ "file_path": str, "start_line": int, "end_line": int }`.

## Consequences
- **Positive**: High faithfulness; all assertions are backed by concrete file paths and line ranges.
- **Positive**: Zero hallucinations on out-of-scope questions (model admits absence of evidence).
- **Negative**: If relevant code is not captured in the top-$K$ retrieved chunks, the answer may be incomplete (addressed in V2 via hybrid retrieval and reranking).

