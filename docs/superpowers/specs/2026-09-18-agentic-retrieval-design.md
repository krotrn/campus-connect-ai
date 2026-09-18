# Agentic Retrieval: Design

- **Date**: 2026-09-18
- **Status**: Approved, pending implementation plan
- **Scope**: `src/retrieval/`, `src/generation/`, `src/agent/`, `src/ingestion/`, `src/mcp/`

## Problem

A query against the deployed system returned `I cannot find sufficient information in the
codebase to answer this question.` while simultaneously displaying five cited sources. An
investigation found three independent causes, only one of which is a defect in the sense the
symptom suggested.

### Cause 1 — the query was out of corpus (not a defect)

The indexed corpus is `campus-connect` (`src/config.py:12-13`: collection `campus_connect`,
852 files). The query concerned Hybrid RAG, which is a feature of AEIA itself — the tool doing
the querying — not of the indexed repository. A corpus-wide grep for `hybrid rag` /
`hybrid retriev` returns zero matches.

The refusal was therefore prompt rule 3 (`src/generation/generator.py:26-28`) behaving exactly
as designed. Correct grounded behaviour, reported confusingly.

### Cause 2 — sources are emitted before the answer exists

`generate_stream` yields the `sources` event before any answer token
(`src/generation/generator.py:344`), and the API forwards it as-is
(`src/api/main.py:405-413`). Nothing reconciles that list against the citations actually
present in the generated answer, so every refusal still renders a full `top_k` source list.

### Cause 3 — retrieval returns one chunk per file, and the reranker never runs

`Retriever.__init__` defaults `rerank=False` (`src/retrieval/retriever.py:38`), and all three
production call sites construct it bare: `src/api/main.py:53`, `src/mcp/server.py:46`,
`src/generation/generator.py:405`. The only `rerank=True` in the repository is the CLI smoke
test at `src/retrieval/retriever.py:324`. The FlashRank cross-encoder is dead code on every
real request.

Because reranking is off, every request falls through to `_deduplicate_files`
(`src/retrieval/retriever.py:87-104`), which returns `chunks_by_file[file_path][0]` — exactly
one chunk per file. `top_k=5` therefore means "five distinct files, one fragment each", never
"the five best chunks". If an answer spans three consecutive chunks of one file, the model sees
only the first.

The ranking key at `src/retrieval/retriever.py:93-103` weights each file's top three chunks at
`(1.0, 0.2, 0.1)` to decide file *order*, then discards chunks two and three. The information
needed to do better is computed and thrown away.

### Why this survived

Every test in `tests/test_retriever.py` is `integration`-marked and skipped unless
`AEIA_TEST_MODE=integration` (`tests/test_retriever.py:5-7`), because `Retriever()` performs a
live Qdrant scroll in `__init__` before any mock can intercept. The fusion and diversity logic
— the broken code — has no offline coverage at all.

## Goals

1. Retrieval can return depth within a file, not just breadth across files.
2. The model can request specific context after seeing initial results, including a named
   function or class definition.
3. Those retrieval primitives are available both to external MCP clients and to AEIA's own
   agent.
4. A refusal states which codebase was searched, and unused sources are distinguishable from
   cited ones.

## Non-goals

- Indexing AEIA's own source as a second corpus. Worth doing, tracked separately; it does not
  belong in this change.
- Re-embedding the corpus. Every step here is designed to avoid it.
- Changing the `top_k` API default. The per-file cap is the fix; callers that want more breadth
  can already ask.

## Constraints

| Constraint | Source | Consequence |
|---|---|---|
| 256MB RAM on the smallest deploy target | `docs/DEPLOYMENT_GUIDE.md:224`, `:352` | A ~130MB cross-encoder cannot load by default |
| Gemini free tier, 429 fallbacks configured | `src/config.py:20-21` | An iterative loop multiplies quota pressure; it must degrade, not fail |
| Embedding cache + deterministic point ids | `src/ingestion/pipeline.py:59-67` | Payload-only migration is possible; re-embedding is not required |
| `sources` streams before tokens | `src/generation/generator.py:344` | Citation reconciliation must happen in a later event, not by delaying sources |

## Stage 1 — Fix retrieval

Ships first. No new LLM calls, no migration, no dependency changes.

### 1.1 Per-file cap replaces one-per-file

Replace `_deduplicate_files` with `_diversify_by_file(candidates, top_k, per_file_cap=3)`.

Keep the existing file-ranking score — the `(1.0, 0.2, 0.1)` weighting is sound and stays as
is. Change only the emission: round-robin across ranked files, taking each file's chunks in
descending score order, up to `per_file_cap` per file, until `top_k` is filled.

Round-robin rather than depth-first is deliberate: every ranked file still contributes its best
chunk before any file contributes a second, so file diversity is preserved while depth becomes
reachable. With `top_k=5, per_file_cap=3` a query whose answer lives in one file yields three
chunks from it plus two neighbours, instead of five disconnected fragments.

Apply the same diversity pass *after* reranking. The rerank path currently bypasses file
diversity entirely (`src/retrieval/retriever.py:79-82`), so the two paths behave inconsistently
today.

### 1.2 Reranker becomes configurable, default off

Add `enable_rerank: bool = False` to `Settings` and wire it into the three bare call sites.

Default off, decided against both alternatives: defaulting on risks the OOM the deployment
guide already warns about on 256MB tiers, and deleting the reranker discards a cheap fallback
for a dependency that is already installed. Off-by-default stops it being dead code — it
becomes a documented switch — without making the smallest deploy target unbootable.

### 1.3 Honest refusals

**Corpus identity.** `SYSTEM_PROMPT` hardcodes "Campus Connect"
(`src/generation/generator.py:17`). Derive the name from settings (`corpus_name`, defaulting
from `corpus_path`) so the prompt does not lie when AEIA is pointed at another repository, and
have the refusal in rule 3 name the codebase it searched.

**Citation reconciliation.** Keep emitting `sources` up front — streaming needs it. Add a
`cited` field to the `done` event listing the `[path#Lstart-Lend]` citations actually present in
the answer text. The frontend dims or labels sources absent from that list. This keeps the
existing event ordering intact and requires no new round trip.

## Stage 2 — Retrieval primitives

New module `src/retrieval/lookup.py`. `retriever.py` is already 331 lines of hybrid search and
should not absorb symbol lookup and file I/O.

| Function | Behaviour |
|---|---|
| `get_file_outline(path)` | Symbols and line ranges within a file — structure before bodies |
| `get_symbol(name, path=None)` | Symbol lookup by Qdrant payload filter. No embedding call |
| `get_file_slice(path, start, end)` | Exact line range from the corpus checkout, byte-capped |
| `search_code(query, top_k, path=None, file_type=None)` | Existing hybrid retrieve, plus optional scoping filters |

`get_symbol` is the primitive that answers "show me this function's definition" — the capability
the current one-shot pipeline cannot express.

### 2.1 Symbol payload migration

`AstChunk` already carries `symbol_name` and `node_type` (`src/ingestion/ast_chunker.py:28-29`),
but `CodeChunk` drops both (`src/ingestion/chunker.py:19-25`) and the indexed payload never
stores them (`src/ingestion/pipeline.py:260-267`). There is no symbol index to query today.

Three parts:

1. `CodeChunk` gains `symbol_name` and `node_type`, propagated from `AstChunk`. Non-AST formats
   (Prisma, YAML, Markdown) pass empty strings — the field is present and empty, not absent.
2. The pipeline payload includes both fields going forward.
3. A one-shot `backfill_symbols` command re-chunks the corpus to parse symbols, recomputes the
   deterministic ids via `_point_id` (`src/ingestion/pipeline.py:59-67`), and applies
   `set_payload` in batches.

The backfill re-parses but does not re-embed: no Gemini calls, no FastEmbed passes, no cache
invalidation. Add a Qdrant payload index on `symbol_name` so filtered lookups stay fast.

### 2.2 Security

`get_file_slice` reads from the filesystem, which the retrieval layer has not done before. It
resolves the requested path against the corpus root and rejects anything escaping it, mirroring
the existing `_get_corpus_dir` and flag-sanitising patterns in `src/agent/tools.py:16-21` and
`:41-44`. Returned content is byte-capped so a single call cannot exhaust the response budget or
the model's context.

### 2.3 MCP exposure

Register all four primitives in `src/mcp/server.py` alongside the existing
`search_campus_connect` and `explain_codebase_query`, with the same `top_k` clamping discipline
already used there (`src/mcp/server.py:89`, `:114`).

This is what makes "primitives first" worthwhile: an external agent exercises and validates the
tools before AEIA's own loop depends on them.

## Stage 3 — Internal agent loop

The graph is currently acyclic: router to exactly one branch to synthesizer to END
(`src/agent/graph.py:204-228`). The model never gets a second look. Stage 3 adds the cycle.

An `agent_loop` node receives the four primitives as Gemini function declarations. Route
`direct_rag` to `agent_loop`, with a conditional edge looping back while the model requests
tools and proceeding to `synthesizer` when it stops. Note that
`automatic_function_calling` is deliberately disabled for routing
(`src/agent/router.py:96`); it is enabled in the loop node only, never globally.

### 3.1 Error handling

This is the crux of the stage, given the quota constraint.

- `max_iterations = 4`, enforced as a hard cap.
- On a quota error (`is_quota_error`, `src/generation/generator.py:62`), break out of the loop
  and synthesise an answer from whatever context was gathered. A quota ceiling degrades the
  answer; it does not fail the request.
- Accumulate chunks across iterations into `context_chunks`, deduplicated by
  `(file_path, start_line)` — the same key already used by RRF
  (`src/retrieval/retriever.py:206-211`).
- Record each tool call in `steps_taken`, which already exists in `AgentState`
  (`src/agent/state.py:24`) and feeds the UI trace.

### 3.2 Deferred decision

Whether streaming emits an incremental `sources` event per iteration (frontend appends) or
defers sources to `done` is a frontend contract decision. It is deliberately left open until
Stage 3 is implemented with the UI in view. Stage 1's `cited` field in the `done` event is
forward-compatible with either choice.

## Testing strategy

Test-driven throughout, offline by default.

**The first test is the regression for Cause 3.** `_diversify_by_file` is a pure function over
hand-built chunks — no Qdrant, no embedding model, no `Retriever` instance. Construct candidates
where three chunks of one file outrank everything else, assert more than one survives. This test
fails against `_deduplicate_files` and passes after the change.

Its existence is as important as the fix: it converts the untested surface identified above into
a covered one, using the same staticmethod boundary that already exists.

- **Stage 1**: offline unit tests for `_diversify_by_file` (per-file cap, round-robin ordering,
  `top_k` exactness, fewer-candidates-than-`top_k`), for `_reciprocal_rank_fusion`, and for
  citation extraction feeding the `cited` field.
- **Stage 2**: `lookup.py` tested against `FakeQdrantClient` (`tests/conftest.py:59`), extended
  with symbol-bearing payloads. Path-traversal rejection gets explicit negative tests. The
  migration gets a test asserting id stability against `_point_id`.
- **Stage 3**: loop termination tested with a stub model — iteration cap reached, quota error
  mid-loop, model stopping voluntarily on the first pass.

Integration-marked tests continue to require live infrastructure; nothing in this design adds to
that set.

## Risks

| Risk | Mitigation |
|---|---|
| Per-file cap reduces breadth for "what depends on X" queries | Round-robin emission means every ranked file contributes its best chunk before any file contributes a second |
| Backfill leaves payloads partially migrated | `set_payload` is idempotent and keyed by deterministic id; the command is safe to re-run |
| Stage 3 loop multiplies latency (~9.9s per pass observed) | Hard iteration cap; Stages 1 and 2 deliver value without the loop, so Stage 3 can be dropped if latency proves unacceptable |
| Loop increases 429 exposure on the free tier | Quota errors degrade to synthesis from gathered context rather than failing |
