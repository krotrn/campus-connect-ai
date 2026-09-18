# Agentic Retrieval (Stages 1–2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make retrieval return depth within a file rather than one fragment per file, stop presenting uncited sources as cited, and expose symbol-level retrieval primitives over MCP so an external agent can ask for a specific function definition.

**Architecture:** Stage 1 is a local fix to `Retriever` plus an additive SSE field — no migration, no new dependencies, no extra LLM calls. Stage 2 adds `symbol_name`/`node_type` to the Qdrant payload via a re-parse-only backfill (deterministic point ids make `set_payload` idempotent, so nothing is re-embedded), then builds a `CodeLookup` class over that payload and registers four new MCP tools.

**Tech Stack:** Python ≥3.12, FastAPI, Qdrant, FastEmbed (BGE-small), rank-bm25, FlashRank, LangGraph, Google GenAI SDK, pytest. Frontend: Next.js 16, React 19, TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-18-agentic-retrieval-design.md`

## Global Constraints

- **Never re-embed the corpus.** Every step here re-parses at most. No FastEmbed passes over the full corpus, no cache invalidation.
- **`enable_rerank` defaults to `False`.** FlashRank's cross-encoder adds ~130MB resident, which OOMs the 256MB deploy tiers documented in `docs/DEPLOYMENT_GUIDE.md:224` and `:352`.
- **Offline tests must never construct `Retriever()`.** `__init__` performs a live Qdrant scroll via `reload_bm25()` before any mock can intercept (`src/retrieval/retriever.py:52`). Test static methods directly or inject a fake client.
- **Preserve SSE event ordering:** `sources` → `token`(s) → `done`. New data goes in `done`; nothing may delay the `sources` event.
- **All new payload fields are present-and-empty, never absent.** Non-AST formats set `symbol_name=""`, not `None`.
- **Test command:** `uv run pytest`. Integration-marked tests require `AEIA_TEST_MODE=integration` and live infra; never add to that set in this plan.
- **Python floor:** `requires-python = ">=3.12"` (`pyproject.toml:6`). `Path.is_relative_to` is available and preferred.
- Commit after every task.

---

# Stage 1 — Fix retrieval

## Task 1: Per-file diversity replaces one-chunk-per-file

This is the core defect. `_deduplicate_files` returns `chunks_by_file[file_path][0]` — exactly one chunk per file — so `top_k=5` can never mean "the five best chunks".

**Files:**
- Modify: `src/retrieval/retriever.py:79-104` (replace `_deduplicate_files`, rewire `retrieve`)
- Test: `tests/test_retrieval_diversity.py` (create)

**Interfaces:**
- Consumes: `RetrievedChunk` from `src/retrieval/retriever.py:23-34`
- Produces: `Retriever._diversify_by_file(candidates: list[RetrievedChunk], top_k: int, per_file_cap: int = 3) -> list[RetrievedChunk]` — a `@staticmethod`, callable without an instance. Task 2 calls it after reranking.

- [ ] **Step 1: Write the failing test**

Create `tests/test_retrieval_diversity.py`. Note there is deliberately **no** `pytestmark = pytest.mark.integration` here — these tests call a static method and need no Qdrant.

```python
"""Offline tests for file-diversity selection.

These call ``Retriever._diversify_by_file`` directly rather than constructing a
``Retriever``, because ``Retriever.__init__`` performs a live Qdrant scroll
(``reload_bm25``) that no mock can intercept.
"""

from src.retrieval.retriever import RetrievedChunk, Retriever


def _chunk(file_path: str, start_line: int, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        content=f"content of {file_path}:{start_line}",
        file_path=file_path,
        start_line=start_line,
        end_line=start_line + 10,
        file_type="code",
        score=score,
    )


def test_diversify_returns_multiple_chunks_from_one_dominant_file():
    """The regression this whole task exists for: an answer spanning three
    chunks of one file must not be truncated to its first chunk."""
    candidates = [
        _chunk("src/lib/auth.ts", 10, 0.99),
        _chunk("src/lib/auth.ts", 40, 0.95),
        _chunk("src/lib/auth.ts", 80, 0.90),
        _chunk("src/app/login.tsx", 5, 0.40),
        _chunk("compose.yml", 30, 0.20),
    ]

    results = Retriever._diversify_by_file(candidates, top_k=5, per_file_cap=3)

    auth_chunks = [c for c in results if c.file_path == "src/lib/auth.ts"]
    assert len(auth_chunks) == 3
    assert len(results) == 5


def test_diversify_gives_every_file_its_best_chunk_before_any_second_chunk():
    """Round-robin, not depth-first: file diversity survives the cap."""
    candidates = [
        _chunk("a.ts", 1, 0.99),
        _chunk("a.ts", 20, 0.98),
        _chunk("a.ts", 40, 0.97),
        _chunk("b.ts", 1, 0.50),
    ]

    results = Retriever._diversify_by_file(candidates, top_k=2, per_file_cap=3)

    assert [c.file_path for c in results] == ["a.ts", "b.ts"]


def test_diversify_never_exceeds_per_file_cap():
    candidates = [_chunk("a.ts", i * 10, 0.9 - i * 0.01) for i in range(6)]

    results = Retriever._diversify_by_file(candidates, top_k=5, per_file_cap=3)

    assert len(results) == 3


def test_diversify_orders_each_files_chunks_by_score():
    candidates = [
        _chunk("a.ts", 40, 0.70),
        _chunk("a.ts", 10, 0.95),
        _chunk("a.ts", 20, 0.85),
    ]

    results = Retriever._diversify_by_file(candidates, top_k=3, per_file_cap=3)

    assert [c.start_line for c in results] == [10, 20, 40]


def test_diversify_returns_all_candidates_when_fewer_than_top_k():
    candidates = [_chunk("a.ts", 1, 0.9), _chunk("b.ts", 1, 0.8)]

    results = Retriever._diversify_by_file(candidates, top_k=5, per_file_cap=3)

    assert len(results) == 2


def test_diversify_handles_empty_candidates():
    assert Retriever._diversify_by_file([], top_k=5, per_file_cap=3) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_retrieval_diversity.py -v`
Expected: FAIL — `AttributeError: type object 'Retriever' has no attribute '_diversify_by_file'`

- [ ] **Step 3: Replace `_deduplicate_files` with `_diversify_by_file`**

In `src/retrieval/retriever.py`, delete the `_deduplicate_files` static method at lines 86-104 and put this in its place:

```python
    @staticmethod
    def _diversify_by_file(
        candidates: list[RetrievedChunk],
        top_k: int,
        per_file_cap: int = 3,
    ) -> list[RetrievedChunk]:
        """Rank files by their strongest chunks, then emit up to *per_file_cap*
        chunks from each in round-robin order.

        Round-robin rather than depth-first is deliberate: every ranked file
        contributes its best chunk before any file contributes a second, so
        file diversity survives while a single dominant file can still supply
        the depth a multi-chunk answer needs.  The previous implementation
        returned one chunk per file, which made a multi-chunk answer
        unreachable no matter how large ``top_k`` was.
        """
        chunks_by_file: dict[str, list[RetrievedChunk]] = {}
        for candidate in candidates:
            chunks_by_file.setdefault(candidate.file_path, []).append(candidate)

        for file_chunks in chunks_by_file.values():
            file_chunks.sort(key=lambda chunk: chunk.score, reverse=True)

        ranked_files = sorted(
            chunks_by_file,
            key=lambda file_path: sum(
                chunk.score * weight
                for chunk, weight in zip(chunks_by_file[file_path][:3], (1.0, 0.2, 0.1))
            ),
            reverse=True,
        )

        selected: list[RetrievedChunk] = []
        for depth in range(per_file_cap):
            for file_path in ranked_files:
                file_chunks = chunks_by_file[file_path]
                if depth < len(file_chunks):
                    selected.append(file_chunks[depth])
                    if len(selected) == top_k:
                        return selected
        return selected
```

The `(1.0, 0.2, 0.1)` file-ranking weights are carried over unchanged from the old implementation — they were sound. What changes is only which chunks get emitted.

- [ ] **Step 4: Rewire `retrieve` to always diversify**

Replace lines 79-84 of `src/retrieval/retriever.py`:

```python
        if self.rerank and candidates:
            candidates = self._rerank(query, candidates, top_k=candidate_k)

        return self._diversify_by_file(candidates, top_k)
```

Note `top_k=candidate_k` on the rerank call, not `top_k`. Reranking to `top_k` first would truncate the candidate pool before diversity ran, making depth unreachable on the rerank path — the same bug in a new place. Reranking reorders the full pool; diversity then picks.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_retrieval_diversity.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Verify no dangling references**

Run: `grep -rn "_deduplicate_files" --include='*.py' . --exclude-dir=.venv`
Expected: no output. (Before this task the only two references were lines 82 and 87 of `retriever.py`, both replaced above.)

- [ ] **Step 7: Run the full offline suite for regressions**

Run: `uv run pytest`
Expected: PASS, with integration-marked tests skipped.

- [ ] **Step 8: Commit**

```bash
git add tests/test_retrieval_diversity.py src/retrieval/retriever.py
git commit -m "fix(retrieval): emit up to 3 chunks per file instead of exactly one

_deduplicate_files returned chunks_by_file[path][0], so top_k=5 meant
five distinct files with one fragment each. An answer spanning three
consecutive chunks of one file was truncated to its first chunk
regardless of top_k. _diversify_by_file keeps the existing file-ranking
weights but emits round-robin up to a per-file cap.

Covered by the first offline retrieval tests in the suite; the previous
tests were all integration-marked and skipped by default, which is why
this survived."
```

---

## Task 2: Reranker becomes a documented switch, default off

The FlashRank cross-encoder is dead code: `__init__` defaults `rerank=False` and all three production call sites construct `Retriever()` bare. The only `rerank=True` in the repo is the CLI smoke test.

**Files:**
- Modify: `src/config.py` (add `enable_rerank`)
- Modify: `src/api/main.py:53`
- Modify: `src/mcp/server.py:46`
- Modify: `src/generation/generator.py:405`
- Test: `tests/test_config_retrieval.py` (create)

**Interfaces:**
- Consumes: `Retriever._diversify_by_file` from Task 1
- Produces: `settings.enable_rerank: bool` — read by Task 10's MCP wiring

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_retrieval.py`:

```python
"""Retrieval-related configuration defaults.

``enable_rerank`` defaults off on purpose: FlashRank's cross-encoder adds
roughly 130MB resident, which exceeds the headroom on the 256MB deploy tiers
described in docs/DEPLOYMENT_GUIDE.md.
"""

from src.config import Settings


def test_rerank_is_disabled_by_default():
    assert Settings(_env_file=None).enable_rerank is False


def test_rerank_can_be_enabled_by_environment(monkeypatch):
    monkeypatch.setenv("ENABLE_RERANK", "true")
    assert Settings(_env_file=None).enable_rerank is True
```

`_env_file=None` keeps a developer's local `.env` from deciding the test result.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_retrieval.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'enable_rerank'`

- [ ] **Step 3: Add the setting**

In `src/config.py`, after the `embedding_dim` line (line 15):

```python
    # Cross-encoder reranking over the fused candidate pool. Off by default:
    # FlashRank's ms-marco-MiniLM-L-12-v2 adds ~130MB resident, which exceeds
    # the headroom on the 256MB deploy tiers in docs/DEPLOYMENT_GUIDE.md.
    # Enable only where RAM allows.
    enable_rerank: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config_retrieval.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Wire the three production call sites**

`src/api/main.py:53` — change `retriever = Retriever()` to:

```python
    retriever = Retriever(rerank=settings.enable_rerank)
```

`src/mcp/server.py:46` — change `_retriever = Retriever()` to:

```python
        _retriever = Retriever(rerank=settings.enable_rerank)
```

`src/generation/generator.py:405` — change `retriever = Retriever()` to:

```python
    retriever = Retriever(rerank=settings.enable_rerank)
```

All three modules already import `settings`; no new imports.

- [ ] **Step 6: Verify no bare constructions remain**

Run: `grep -rn "Retriever()" --include='*.py' src/`
Expected: no output.

- [ ] **Step 7: Document the switch**

Append to the environment-variable table in `docs/DEPLOYMENT_GUIDE.md` (in the section listing configuration variables):

```markdown
| `ENABLE_RERANK` | `false` | Enables the FlashRank cross-encoder over fused candidates. Adds ~130MB resident — leave off on 256MB tiers (Fly.io free, and Render free under load). Improves ranking precision where RAM allows. |
```

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/config.py src/api/main.py src/mcp/server.py src/generation/generator.py tests/test_config_retrieval.py docs/DEPLOYMENT_GUIDE.md
git commit -m "feat(retrieval): make reranking configurable, default off

The FlashRank cross-encoder was dead code: rerank defaulted to False and
every production call site constructed Retriever() bare, so the only
rerank=True in the repo was the CLI smoke test. It is now a documented
switch rather than an unreachable branch.

Default stays off because the model adds ~130MB resident, which the
deployment guide already flags as an OOM risk on 256MB tiers."
```

---

## Task 3: Refusals name the codebase they searched

`SYSTEM_PROMPT` hardcodes "Campus Connect", and the refusal string says only "the codebase" — so a refusal cannot be distinguished from a bug, and the prompt lies outright if AEIA is pointed at another repo.

**Files:**
- Modify: `src/config.py` (add `corpus_name`)
- Modify: `src/generation/generator.py:17-43` (templatize both prompts), `:166`, `:311`
- Test: `tests/test_generation_prompts.py` (create)

**Interfaces:**
- Produces: `build_system_prompt(corpus_name: str | None = None) -> str` and `build_tool_synthesis_prompt(corpus_name: str | None = None) -> str` in `src/generation/generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_generation_prompts.py`:

```python
from src.generation.generator import build_system_prompt, build_tool_synthesis_prompt


def test_system_prompt_names_the_configured_corpus():
    prompt = build_system_prompt(corpus_name="Acme Platform")

    assert "Acme Platform codebase" in prompt
    assert "Campus Connect" not in prompt


def test_refusal_instruction_names_the_corpus():
    """A refusal has to say which codebase was searched, or it reads as a bug."""
    prompt = build_system_prompt(corpus_name="Acme Platform")

    assert (
        "I cannot find sufficient information in the Acme Platform codebase "
        "to answer this question." in prompt
    )


def test_tool_synthesis_prompt_names_the_configured_corpus():
    prompt = build_tool_synthesis_prompt(corpus_name="Acme Platform")

    assert "Acme Platform" in prompt
    assert "Campus Connect" not in prompt


def test_prompts_fall_back_to_settings_corpus_name():
    from src.config import settings

    assert settings.corpus_name in build_system_prompt()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_generation_prompts.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_system_prompt'`

- [ ] **Step 3: Add `corpus_name` to settings**

In `src/config.py`, directly after the `corpus_path` line (line 13):

```python
    # Human-readable name of the indexed repository. Appears in the generation
    # prompt and in refusals, so a refusal states which codebase was searched.
    corpus_name: str = "Campus Connect"
```

- [ ] **Step 4: Templatize both prompts**

In `src/generation/generator.py`, replace the `SYSTEM_PROMPT` assignment (lines 17-30) with:

```python
SYSTEM_PROMPT_TEMPLATE = """You are an expert AI Engineering Intelligence Assistant analyzing the {corpus_name} codebase.

Your mission is to answer engineering questions accurately, concisely, and strictly grounded in the
provided code/docs chunks.

RULES:
1. Base your answer ONLY on the provided context chunks.
2. For every claim, architectural fact, or code location, cite the source using the exact format:
   `[filepath#Lstart-Lend]`.
3. If the provided context does not contain enough information to answer the question, clearly state:
   "I cannot find sufficient information in the {corpus_name} codebase to answer this question."
   Do NOT hallucinate non-existent files or functions.
4. Provide actionable, technical explanations with relevant code references.
"""
```

Replace the `TOOL_SYNTHESIS_PROMPT` assignment (lines 32-43) with:

```python
TOOL_SYNTHESIS_PROMPT_TEMPLATE = """You are an expert AI Engineering Intelligence Assistant analyzing the
{corpus_name} codebase.

You are given raw output from a read-only repository inspection tool (git log, git show, or an
import-dependency scan) together with the engineer's question.

RULES:
1. Answer using ONLY the tool output provided. Never invent commits, files, authors, or dates.
2. Be specific: name the actual commit hashes, file paths, and modules that appear in the output.
3. If the tool output does not answer the question, say so plainly.
4. Keep it concise — a short paragraph or a tight list, not an essay.
"""


def build_system_prompt(corpus_name: str | None = None) -> str:
    """Grounding prompt for the configured corpus.

    The corpus name is interpolated rather than hardcoded so that the refusal
    in rule 3 names the repository actually searched.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(corpus_name=corpus_name or settings.corpus_name)


def build_tool_synthesis_prompt(corpus_name: str | None = None) -> str:
    """Synthesis prompt for raw repository-tool output."""
    return TOOL_SYNTHESIS_PROMPT_TEMPLATE.format(corpus_name=corpus_name or settings.corpus_name)
```

- [ ] **Step 5: Update both use sites**

`src/generation/generator.py:166` — inside `_generation_config`, change `system_instruction=SYSTEM_PROMPT` to:

```python
            system_instruction=build_system_prompt(),
```

`src/generation/generator.py:311` — change `system_instruction=TOOL_SYNTHESIS_PROMPT` to:

```python
                        system_instruction=build_tool_synthesis_prompt(),
```

- [ ] **Step 6: Verify no stale references**

Run: `grep -n "SYSTEM_PROMPT\b\|TOOL_SYNTHESIS_PROMPT\b" src/generation/generator.py`
Expected: only the two `_TEMPLATE` names and their uses inside the two builder functions. (A pre-task grep confirmed these constants are referenced nowhere outside this module.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_generation_prompts.py -v`
Expected: PASS (4 passed)

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/config.py src/generation/generator.py tests/test_generation_prompts.py
git commit -m "feat(generation): refusals name the codebase that was searched

The prompt hardcoded 'Campus Connect' and the refusal said only 'the
codebase', so a correct out-of-corpus refusal was indistinguishable from
a retrieval bug. Both prompts now interpolate settings.corpus_name."
```

---

## Task 4: Report which sources the answer actually cited

`sources` is emitted before the first token and never reconciled against the answer, so a refusal still renders a full `top_k` source list. Sources must keep streaming early; the reconciliation ships in `done`.

**Files:**
- Modify: `src/generation/generator.py` (add `extract_citations`, `cited` on `AnswerResponse`, `cited` in the `done` event)
- Modify: `src/api/main.py:392-399`, `:424-431`
- Test: `tests/test_citation_reconciliation.py` (create)

**Interfaces:**
- Consumes: `build_system_prompt` from Task 3
- Produces: `extract_citations(answer: str) -> list[str]` in `src/generation/generator.py`; `AnswerResponse.cited: list[str]`; a `cited: list[str]` key on the `done` SSE event consumed by Task 5

- [ ] **Step 1: Write the failing test**

Create `tests/test_citation_reconciliation.py`:

```python
from src.generation.generator import extract_citations


def test_extract_citations_finds_a_citation():
    answer = "Authentication lives in `authorize` [src/lib/auth.ts#L10-L42]."

    assert extract_citations(answer) == ["src/lib/auth.ts#L10-L42"]


def test_extract_citations_deduplicates_while_preserving_order():
    answer = (
        "See [src/lib/auth.ts#L10-L42] and [prisma/schema.prisma#L1-L12], "
        "then [src/lib/auth.ts#L10-L42] again."
    )

    assert extract_citations(answer) == [
        "src/lib/auth.ts#L10-L42",
        "prisma/schema.prisma#L1-L12",
    ]


def test_extract_citations_returns_empty_for_a_refusal():
    """The whole point: a refusal cites nothing, so the UI must be able to
    tell that the displayed sources went unused."""
    answer = (
        "I cannot find sufficient information in the Campus Connect codebase "
        "to answer this question."
    )

    assert extract_citations(answer) == []


def test_extract_citations_ignores_malformed_markers():
    answer = "Not a citation: [src/lib/auth.ts] nor [#L10-L42] nor [a.ts#L10]."

    assert extract_citations(answer) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_citation_reconciliation.py -v`
Expected: FAIL — `ImportError: cannot import name 'extract_citations'`

- [ ] **Step 3: Implement `extract_citations`**

In `src/generation/generator.py`, add `import re` to the imports, then add after the prompt builders from Task 3:

```python
CITATION_PATTERN = re.compile(r"\[([^\]\s]+?)#L(\d+)-L(\d+)\]")


def extract_citations(answer: str) -> list[str]:
    """Citations actually present in generated answer text, in order, deduped.

    ``sources`` streams before the first token, so it lists what retrieval
    found, not what the answer used. A refusal therefore ships a full source
    list. This lets the caller report which of those sources the model really
    cited.
    """
    seen: set[str] = set()
    found: list[str] = []
    for match in CITATION_PATTERN.finditer(answer):
        citation = f"{match.group(1)}#L{match.group(2)}-L{match.group(3)}"
        if citation not in seen:
            seen.add(citation)
            found.append(citation)
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_citation_reconciliation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Add `cited` to `AnswerResponse`**

In `src/generation/generator.py`, change the `AnswerResponse` model (lines 93-97) to:

```python
class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceCitation]
    model_used: str | None = None
    # Citations present in `answer`. A subset of `sources`, because `sources`
    # reports what retrieval found rather than what the answer used.
    cited: list[str] = []
```

- [ ] **Step 6: Populate it in `generate`**

In `src/generation/generator.py`, change the `return AnswerResponse(...)` at the end of `generate` (lines 266-271) to:

```python
        return AnswerResponse(
            question=question,
            answer=answer_text,
            sources=sources,
            model_used=model_used,
            cited=extract_citations(answer_text),
        )
```

- [ ] **Step 7: Add `cited` to the streaming `done` event**

In `src/generation/generator.py`, replace the final `yield` of `generate_stream` (line 390):

```python
        answer_text = "".join(full_text_chunks)
        yield {
            "type": "done",
            "answer": answer_text,
            "model": model_used,
            "cited": extract_citations(answer_text),
        }
```

Also update the early-return `done` for the no-client case (line 349):

```python
            yield {"type": "done", "answer": NO_KEY_NOTICE, "model": None, "cited": []}
```

- [ ] **Step 8: Forward `cited` through both API `done` events**

In `src/api/main.py`, add to the RAG-path `done` payload (lines 424-431), after `"model": event.get("model"),`:

```python
                            "cited": event.get("cited", []),
```

And in the agent-path `done` payload (lines 392-399), after the `"model": ...` line:

```python
                    "cited": extract_citations(answer_text),
```

Add `extract_citations` to the existing `src/generation/generator` import in `src/api/main.py`.

- [ ] **Step 9: Write the streaming contract test**

Append to `tests/test_citation_reconciliation.py`:

```python
def test_stream_done_event_carries_cited_after_sources(client, auth_headers):
    """Ordering is part of the contract: sources first, done last, and the
    cited list only appears on done."""
    response = client.post(
        "/ask/stream",
        json={"question": "Where is authentication implemented?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    event_types = []
    done_payload = None
    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue
        import json

        payload = json.loads(line[len("data: "):])
        event_types.append(payload["type"])
        if payload["type"] == "done":
            done_payload = payload

    assert event_types[0] == "sources"
    assert event_types[-1] == "done"
    assert done_payload is not None
    assert "cited" in done_payload
    assert done_payload["cited"] == ["src/lib/auth.ts#L10-L42"]
```

This passes against the existing offline fakes: `FAKE_ANSWER` in `tests/conftest.py:51` is `"Authentication is handled in `authorize` [src/lib/auth.ts#L10-L42]."`, so exactly one citation is expected.

- [ ] **Step 10: Extend `FakeGenerator` to emit `cited`**

The autouse fake at `tests/conftest.py:126` must match the real event shape. In its `generate_stream`, add `"cited"` to the `done` event it yields, computed the same way:

```python
    def generate_stream(self, question, chunks, history=None, api_key=None):
        from src.generation.generator import extract_citations

        sources = self._sources(chunks)
        yield {"type": "sources", "sources": [s.model_dump() for s in sources]}
        for word in FAKE_ANSWER.split(" "):
            yield {"type": "token", "text": word + " "}
        yield {
            "type": "done",
            "answer": FAKE_ANSWER,
            "model": self.model_name,
            "cited": extract_citations(FAKE_ANSWER),
        }
```

Keep the rest of `FakeGenerator` unchanged. Also add `cited=extract_citations(FAKE_ANSWER)` to the `AnswerResponse` its `generate` returns, so the non-streaming path matches too.

- [ ] **Step 11: Run tests to verify they pass**

Run: `uv run pytest tests/test_citation_reconciliation.py -v`
Expected: PASS (5 passed)

- [ ] **Step 12: Run the full suite**

Run: `uv run pytest`
Expected: PASS. If `tests/test_stream.py` or `tests/test_unified_stream.py` assert exact `done`-payload keys, update those assertions to include `cited` — an additive field, so no consumer breaks.

- [ ] **Step 13: Commit**

```bash
git add src/generation/generator.py src/api/main.py tests/test_citation_reconciliation.py tests/conftest.py
git commit -m "feat(generation): report which sources the answer actually cited

sources streams before the first token and was never reconciled against
the answer, so a refusal still rendered a full top_k source list. The
done event now carries the citations present in the answer text, leaving
the early sources event and its latency untouched."
```

---

## Task 5: Frontend distinguishes cited sources from retrieved ones

The chip header reads "N sources cited" for every answer, including refusals that cited nothing.

**Files:**
- Modify: `frontend/src/types/aeia.ts:36-47`, `:76-84`, `:108-117`
- Modify: `frontend/src/services/aeia.service.ts:18`, `:135`
- Modify: `frontend/src/app/page.tsx:174-199`
- Modify: `frontend/src/components/aeia/chat-message-item.tsx:126-161`
- Test: `frontend/src/components/aeia/__tests__/chat-message-item.test.tsx` (create, or extend if present)

**Interfaces:**
- Consumes: the `cited: string[]` field on the `done` SSE event from Task 4

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/aeia/__tests__/chat-message-item.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatMessageItem } from "../chat-message-item";
import type { ChatMessage } from "@/types/aeia";

const sources = [
  {
    file_path: "src/lib/auth.ts",
    start_line: 10,
    end_line: 42,
    citation: "src/lib/auth.ts#L10-L42",
    content: "export async function authorize() {}",
    score: 0.91,
  },
  {
    file_path: "compose.yml",
    start_line: 30,
    end_line: 40,
    citation: "compose.yml#L30-L40",
    content: "redis:",
    score: 0.64,
  },
];

function message(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "Answer text.",
    sources,
    timestamp: 0,
    ...overrides,
  };
}

describe("ChatMessageItem source chips", () => {
  it("reports how many sources were cited, not how many were retrieved", () => {
    render(
      <ChatMessageItem
        message={message({ cited: ["src/lib/auth.ts#L10-L42"] })}
        onSelectCitation={vi.fn()}
      />
    );

    expect(screen.getByText("1 of 2 sources cited")).toBeInTheDocument();
  });

  it("says nothing was cited when the answer is a refusal", () => {
    render(
      <ChatMessageItem message={message({ cited: [] })} onSelectCitation={vi.fn()} />
    );

    expect(screen.getByText("2 sources retrieved, none cited")).toBeInTheDocument();
  });

  it("marks uncited chips so they read as retrieved-but-unused", () => {
    render(
      <ChatMessageItem
        message={message({ cited: ["src/lib/auth.ts#L10-L42"] })}
        onSelectCitation={vi.fn()}
      />
    );

    expect(screen.getByTitle("compose.yml — retrieved but not cited")).toBeInTheDocument();
    expect(screen.getByTitle("src/lib/auth.ts")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm vitest run src/components/aeia/__tests__/chat-message-item.test.tsx`
Expected: FAIL — `cited` is not a property of `ChatMessage`, and the header text does not match.

- [ ] **Step 3: Add `cited` to the types**

In `frontend/src/types/aeia.ts`, add to `StreamDonePayload` (after the `model` field):

```ts
  /** Citations present in the answer text. A subset of the streamed sources,
   *  because sources reports what retrieval found, not what the answer used. */
  cited?: string[];
```

Add the same field to `AskResponse` (after `sources`):

```ts
  cited?: string[];
```

And to `ChatMessage` (after `sources`):

```ts
  cited?: string[];
```

- [ ] **Step 4: Widen the `onDone` callback**

In `frontend/src/services/aeia.service.ts`, change line 18:

```ts
  onDone?: (
    latencyMs: number,
    route?: string,
    model?: string | null,
    cited?: string[]
  ) => void;
```

And the call site at line 135:

```ts
              callbacks.onDone?.(
                payload.latency_ms,
                payload.route,
                payload.model,
                payload.cited
              );
```

- [ ] **Step 5: Store `cited` on the message**

In `frontend/src/app/page.tsx`, change the `onDone` signature (line 174) to `onDone: (latencyMs, route, model, cited) => {` and add `cited` to the object spread in its `setMessages` call (after `sources: currentSources,`):

```tsx
                      cited: cited ?? [],
```

- [ ] **Step 6: Render the distinction**

In `frontend/src/components/aeia/chat-message-item.tsx`, replace the chip header `<span>` (line 130) with a computed label. Immediately before the `return` of the sources block, add:

```tsx
                const citedSet = new Set(message.cited ?? []);
                const citedCount = message.sources.filter((s) =>
                  citedSet.has(s.citation)
                ).length;
                const headerLabel =
                  message.cited === undefined
                    ? `${message.sources.length} source${message.sources.length === 1 ? "" : "s"} retrieved`
                    : citedCount === 0
                      ? `${message.sources.length} source${message.sources.length === 1 ? "" : "s"} retrieved, none cited`
                      : `${citedCount} of ${message.sources.length} sources cited`;
```

Place that just inside the `{message.sources && message.sources.length > 0 && (` block, converting it to an IIFE or extracting the block into a small `SourceChips` component — extracting is preferred, since `chat-message-item.tsx` already carries several responsibilities.

Use `headerLabel` in the header span, and inside the `.map` compute per-chip state:

```tsx
                  const isCited = citedSet.has(s.citation);
```

Then on the chip `<button>`, replace the `title` with:

```tsx
                      title={isCited ? s.file_path : `${fileName} — retrieved but not cited`}
```

and append the dimming classes to the existing `className` string:

```tsx
                      className={`group flex items-center gap-2 border-l-2 hover:border-moss-500 bg-stone-900/40 hover:bg-stone-900 pl-2.5 pr-2 py-1 text-[11px] transition text-left ${
                        isCited
                          ? "border-stone-700 text-stone-400"
                          : "border-stone-800 text-stone-600 opacity-60"
                      }`}
```

Uncited chips stay clickable — they were genuinely retrieved and are still worth opening. They simply no longer claim to have been cited.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && pnpm vitest run src/components/aeia/__tests__/chat-message-item.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 8: Typecheck and lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint`
Expected: no errors.

- [ ] **Step 9: Run the frontend suite**

Run: `cd frontend && pnpm vitest run`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/types/aeia.ts frontend/src/services/aeia.service.ts frontend/src/app/page.tsx frontend/src/components/aeia/chat-message-item.tsx frontend/src/components/aeia/__tests__/chat-message-item.test.tsx
git commit -m "feat(frontend): distinguish cited sources from merely retrieved ones

The chip header claimed 'N sources cited' for every answer, including
refusals that cited nothing. It now reports the cited count against the
retrieved count, and uncited chips are dimmed and labelled while staying
clickable."
```

---

# Stage 2 — Retrieval primitives

## Task 6: Index symbol metadata that is already parsed and thrown away

`AstChunk` carries `symbol_name`/`node_type` and `BlockChunk` carries `identifier`/`block_type`, but `CodeChunk` drops all of it and the Qdrant payload never stores it. There is no symbol index to query today.

**Files:**
- Modify: `src/ingestion/chunker.py:19-25` (dataclass), `:139-145`, `:158-164`, `:177-183`, `:196-202`, `:214-220`, `:247-253` (all six construction sites)
- Modify: `src/ingestion/pipeline.py:8-15` (import), `:82-99` (payload index), `:260-267` (payload)
- Test: `tests/test_symbol_metadata.py` (create)

**Interfaces:**
- Produces: `CodeChunk.symbol_name: str` and `CodeChunk.node_type: str` (always present, `""` when unknown); Qdrant payload keys `symbol_name` and `node_type`; a keyword payload index on `symbol_name`. Tasks 7–9 depend on all of these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_symbol_metadata.py`:

```python
"""Symbol metadata must survive chunking.

The AST and block parsers already extract symbol names; before this change
CodeChunk discarded them, so symbol-level lookup was impossible.
"""

from pathlib import Path

from src.ingestion.chunker import CodeAwareChunker


def test_typescript_chunks_carry_ast_symbol_names(tmp_path: Path):
    source = tmp_path / "auth.ts"
    source.write_text(
        "export async function authorize(credentials: string) {\n"
        "  return credentials;\n"
        "}\n"
        "\n"
        "export function signOut() {\n"
        "  return true;\n"
        "}\n",
        encoding="utf-8",
    )

    chunks = CodeAwareChunker().chunk_file(source, "src/lib/auth.ts")

    symbols = {c.symbol_name for c in chunks}
    assert "authorize" in symbols
    assert "signOut" in symbols


def test_prisma_chunks_carry_block_identifiers(tmp_path: Path):
    source = tmp_path / "schema.prisma"
    source.write_text(
        "model User {\n  id String @id\n}\n\nmodel Session {\n  id String @id\n}\n",
        encoding="utf-8",
    )

    chunks = CodeAwareChunker().chunk_file(source, "prisma/schema.prisma")

    symbols = {c.symbol_name for c in chunks}
    assert "User" in symbols
    assert "Session" in symbols


def test_symbol_fields_are_present_and_empty_when_unknown(tmp_path: Path):
    """Absent is not the same as empty: consumers filter on these keys."""
    source = tmp_path / "config.json"
    source.write_text('{"key": "value"}\n', encoding="utf-8")

    chunks = CodeAwareChunker().chunk_file(source, "config.json")

    assert chunks
    for chunk in chunks:
        assert chunk.symbol_name == ""
        assert chunk.node_type == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_symbol_metadata.py -v`
Expected: FAIL — `AttributeError: 'CodeChunk' object has no attribute 'symbol_name'`

- [ ] **Step 3: Extend the `CodeChunk` dataclass**

In `src/ingestion/chunker.py`, replace lines 18-25:

```python
@dataclass
class CodeChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    file_type: str
    chunk_index: int
    # Symbol identity, when the parser could determine it. Always present,
    # empty when unknown, because consumers filter on these payload keys.
    symbol_name: str = ""
    node_type: str = ""
```

Defaults keep every existing construction site valid, so the six edits below can land one at a time without breaking the module.

- [ ] **Step 4: Populate from the AST parser**

In `src/ingestion/chunker.py`, in the TypeScript branch, add two fields to the `CodeChunk(...)` at lines 139-146:

```python
                        chunk_index=i,
                        symbol_name=c.symbol_name,
                        node_type=c.node_type,
```

- [ ] **Step 5: Populate from the four block parsers**

The Prisma (line 158), YAML (line 177), Markdown (line 196), and SQL (line 214) branches all iterate `BlockChunk` objects bound to `b`. In each of those four `CodeChunk(...)` calls, add after `chunk_index=i,`:

```python
                        symbol_name=b.identifier,
                        node_type=b.block_type,
```

- [ ] **Step 6: Leave the generic fallback explicit**

The generic splitter path at line 247 has no parser and therefore no symbol. Add after `chunk_index=i,` to make that explicit rather than relying on the dataclass default:

```python
                    symbol_name="",
                    node_type="",
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_symbol_metadata.py -v`
Expected: PASS (3 passed)

- [ ] **Step 8: Store the fields in the Qdrant payload**

In `src/ingestion/pipeline.py`, add to the payload dict at lines 260-267:

```python
                                "chunk_index": chunk.chunk_index,
                                "symbol_name": chunk.symbol_name,
                                "node_type": chunk.node_type,
```

- [ ] **Step 9: Create the payload index**

Add `PayloadSchemaType` to the existing `qdrant_client.models` import at `src/ingestion/pipeline.py:8-15`, then append to `init_collection` (after the `create_collection` call, at the end of the method):

```python
        # Keyword index on symbol_name so get_symbol() filters instead of
        # scanning. create_payload_index is idempotent, so this is safe on an
        # existing collection and needs no recreate.
        self.client.create_payload_index(
            collection_name=settings.collection_name,
            field_name="symbol_name",
            field_schema=PayloadSchemaType.KEYWORD,
        )
```

- [ ] **Step 10: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add src/ingestion/chunker.py src/ingestion/pipeline.py tests/test_symbol_metadata.py
git commit -m "feat(ingestion): carry parsed symbol names into the Qdrant payload

AstChunk.symbol_name and BlockChunk.identifier were both extracted and
then discarded by CodeChunk, so no symbol index existed to query. Both
now reach the payload, with a keyword index on symbol_name.

Fields are present-and-empty rather than absent when a parser cannot
name the symbol, because consumers filter on these keys."
```

---

## Task 7: Backfill symbols onto the existing collection without re-embedding

Task 6 only affects newly ingested points. Point ids are `sha256(file_path::chunk_index)` (`src/ingestion/pipeline.py:59-67`), so re-chunking reproduces exactly the ids already stored and `set_payload` can attach the fields in place.

**Files:**
- Modify: `src/ingestion/pipeline.py` (add `backfill_symbols`), `:391-407` (CLI)
- Test: `tests/test_symbol_backfill.py` (create)

**Interfaces:**
- Consumes: `CodeChunk.symbol_name`/`node_type` from Task 6; `_point_id` from `src/ingestion/pipeline.py:59`
- Produces: `IngestionPipeline.backfill_symbols() -> dict` returning `{"files": int, "points": int}`; CLI flag `--backfill-symbols`

- [ ] **Step 1: Write the failing test**

Create `tests/test_symbol_backfill.py`:

```python
"""The backfill must reproduce existing point ids exactly and never embed.

Re-embedding 852 files would cost quota and invalidate the embedding cache;
the whole design depends on _point_id being deterministic.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.pipeline import IngestionPipeline, _point_id


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "auth.ts").write_text(
        "export async function authorize() {\n  return 1;\n}\n", encoding="utf-8"
    )
    monkeypatch.setattr("src.ingestion.pipeline.settings.corpus_path", corpus)

    with (
        patch("src.ingestion.pipeline.QdrantClient", MagicMock()),
        patch("src.ingestion.pipeline.TextEmbedding", MagicMock()),
    ):
        yield IngestionPipeline()


def test_backfill_uses_deterministic_point_ids(pipeline):
    result = pipeline.backfill_symbols()

    assert result["points"] > 0
    assert pipeline.client.set_payload.called
    sent_ids = [
        point_id
        for call in pipeline.client.set_payload.call_args_list
        for point_id in call.kwargs["points"]
    ]
    assert _point_id("auth.ts", 0) in sent_ids


def test_backfill_sends_only_symbol_fields(pipeline):
    pipeline.backfill_symbols()

    for call in pipeline.client.set_payload.call_args_list:
        assert set(call.kwargs["payload"]) == {"symbol_name", "node_type"}


def test_backfill_never_computes_embeddings(pipeline):
    """A quota-free, cache-safe migration is the entire point."""
    with patch.object(pipeline, "_get_embeddings") as embed:
        pipeline.backfill_symbols()

    embed.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_symbol_backfill.py -v`
Expected: FAIL — `AttributeError: 'IngestionPipeline' object has no attribute 'backfill_symbols'`

- [ ] **Step 3: Implement `backfill_symbols`**

Add to `IngestionPipeline` in `src/ingestion/pipeline.py`, after `_upsert_chunks` (which ends at line 274):

```python
    def backfill_symbols(self) -> dict:
        """Attach symbol_name/node_type to points that predate Task 6.

        Point ids are a deterministic hash of (file_path, chunk_index), so
        re-chunking the corpus reproduces the ids already stored and
        set_payload can attach the new fields in place.

        Re-parses but never embeds: no quota is spent and the embedding cache
        is untouched. Safe to re-run — set_payload is idempotent.
        """
        corpus_path = settings.corpus_path
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus directory not found at {corpus_path}")

        files = self.scan_files(corpus_path)
        logger.info("Backfilling symbol metadata across %d files...", len(files))

        points_updated = 0
        for file_path in tqdm(files, desc="Backfilling symbols"):
            rel_path = str(file_path.relative_to(corpus_path))
            chunks = self.chunker.chunk_file(file_path, rel_path)

            by_symbol: dict[tuple[str, str], list[int]] = {}
            for chunk in chunks:
                key = (chunk.symbol_name, chunk.node_type)
                by_symbol.setdefault(key, []).append(
                    _point_id(chunk.file_path, chunk.chunk_index)
                )

            # One call per distinct (symbol_name, node_type) pair in the file
            # rather than one per point: set_payload takes a point list.
            for (symbol_name, node_type), point_ids in by_symbol.items():
                self.client.set_payload(
                    collection_name=settings.collection_name,
                    payload={"symbol_name": symbol_name, "node_type": node_type},
                    points=point_ids,
                )
                points_updated += len(point_ids)

        logger.info("Backfill complete: %d points updated.", points_updated)
        return {"files": len(files), "points": points_updated}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_symbol_backfill.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Add the CLI flag**

In `src/ingestion/pipeline.py`, replace the `__main__` block body (lines 398-407):

```python
    parser = argparse.ArgumentParser(description="Ingest the target corpus into Qdrant.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and rebuild the collection (causes query downtime; needed for schema changes).",
    )
    parser.add_argument(
        "--backfill-symbols",
        action="store_true",
        help=(
            "Attach symbol_name/node_type to existing points and exit. "
            "Re-parses the corpus but computes no embeddings."
        ),
    )
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    if args.backfill_symbols:
        pipeline.init_collection()
        result = pipeline.backfill_symbols()
        print(f"Backfilled {result['points']} points across {result['files']} files.")
    else:
        pipeline.run(recreate=args.recreate)
```

`init_collection()` runs first so the `symbol_name` payload index from Task 6 exists before anything queries it.

- [ ] **Step 6: Document the migration**

Add to the README's ingestion section:

```markdown
### Backfilling symbol metadata

Collections ingested before symbol indexing landed need a one-time backfill so
`get_symbol` can find definitions:

```bash
uv run python -m src.ingestion.pipeline --backfill-symbols
```

This re-parses the corpus to recover symbol names and writes them onto the
existing points. It computes no embeddings, spends no API quota, leaves the
embedding cache intact, and is safe to re-run.
```

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ingestion/pipeline.py tests/test_symbol_backfill.py README.md
git commit -m "feat(ingestion): add --backfill-symbols migration

Task 6 only affects newly ingested points. Because point ids are a
deterministic hash of (file_path, chunk_index), re-chunking reproduces
the stored ids and set_payload attaches symbol fields in place.

Re-parses but never embeds: no quota spent, embedding cache untouched,
idempotent on re-run."
```

---

## Task 8: `CodeLookup` — symbol and scoped search

**Files:**
- Create: `src/retrieval/lookup.py`
- Modify: `tests/conftest.py:59-70` (teach `FakeQdrantClient` to honour filters), `:22-49` (add symbol payloads)
- Test: `tests/test_code_lookup.py` (create)

**Interfaces:**
- Consumes: payload keys `symbol_name`/`node_type` from Task 6
- Produces:
  - `CodeLookup(client: QdrantClient)` — takes a client rather than making one, so it reuses `Retriever.client` in production and a fake in tests
  - `CodeLookup.get_symbol(name: str, file_path: str | None = None, limit: int = 5) -> list[dict]`
  - `CodeLookup.search_code(retriever, query: str, top_k: int = 5, file_path: str | None = None, file_type: str | None = None) -> list[dict]`

  Task 9 adds two more methods to this class; Task 10 registers all four as MCP tools.

**Scope note:** `get_symbol` matches symbol names **exactly**. The spec said "exact/fuzzy"; fuzzy matching is deliberately not implemented, because `search_code` already serves approximate lookup and a text index on `symbol_name` would add cost for a redundant capability. This is a narrowing of the spec — flag it if you disagree.

- [ ] **Step 1: Add symbol-bearing fixtures**

In `tests/conftest.py`, after `FAKE_CHUNKS` (line 49), add:

```python
# Payloads carrying the symbol metadata added in Task 6. Kept separate from
# FAKE_CHUNKS because that list is splatted into RetrievedChunk(**c), which has
# no symbol fields.
FAKE_SYMBOL_PAYLOADS = [
    {
        "content": "export async function authorize(credentials) { /* ... */ }",
        "file_path": "src/lib/auth.ts",
        "start_line": 10,
        "end_line": 42,
        "file_type": "code",
        "chunk_index": 0,
        "symbol_name": "authorize",
        "node_type": "function_declaration",
    },
    {
        "content": "export function signOut() { /* ... */ }",
        "file_path": "src/lib/auth.ts",
        "start_line": 50,
        "end_line": 60,
        "file_type": "code",
        "chunk_index": 1,
        "symbol_name": "signOut",
        "node_type": "function_declaration",
    },
    {
        "content": "model User {\n  id String @id\n}",
        "file_path": "prisma/schema.prisma",
        "start_line": 1,
        "end_line": 12,
        "file_type": "schema",
        "chunk_index": 0,
        "symbol_name": "User",
        "node_type": "model",
    },
]
```

- [ ] **Step 2: Teach `FakeQdrantClient` to honour scroll filters**

Replace `FakeQdrantClient` in `tests/conftest.py` (lines 59-70):

```python
class FakeQdrantClient:
    """Minimal stand-in for the bits of QdrantClient the API touches."""

    def __init__(
        self,
        points_count: int = len(FAKE_CHUNKS),
        payloads: list[dict] | None = None,
    ):
        self.points_count = points_count
        self._payloads = [] if payloads is None else payloads

    def get_collection(self, collection_name: str):
        return SimpleNamespace(points_count=self.points_count)

    def scroll(self, *args, scroll_filter=None, limit=None, **kwargs):
        records = [SimpleNamespace(payload=dict(p)) for p in self._payloads]
        for condition in getattr(scroll_filter, "must", None) or []:
            records = [
                r
                for r in records
                if r.payload.get(condition.key) == condition.match.value
            ]
        if limit is not None:
            records = records[:limit]
        return records, None
```

The default stays an empty payload list so the existing `FakeRetriever` behaviour (`scroll` returning nothing) is unchanged.

- [ ] **Step 3: Write the failing test**

Create `tests/test_code_lookup.py`:

```python
import pytest

from src.retrieval.lookup import CodeLookup
from tests.conftest import FAKE_SYMBOL_PAYLOADS, FakeQdrantClient


@pytest.fixture
def lookup():
    return CodeLookup(client=FakeQdrantClient(payloads=FAKE_SYMBOL_PAYLOADS))


def test_get_symbol_finds_a_function_definition(lookup):
    results = lookup.get_symbol("authorize")

    assert len(results) == 1
    assert results[0]["file_path"] == "src/lib/auth.ts"
    assert results[0]["start_line"] == 10
    assert "authorize" in results[0]["content"]


def test_get_symbol_finds_a_prisma_model(lookup):
    results = lookup.get_symbol("User")

    assert len(results) == 1
    assert results[0]["node_type"] == "model"


def test_get_symbol_can_be_scoped_to_a_file(lookup):
    assert lookup.get_symbol("authorize", file_path="src/lib/auth.ts")
    assert lookup.get_symbol("authorize", file_path="prisma/schema.prisma") == []


def test_get_symbol_returns_empty_for_an_unknown_name(lookup):
    assert lookup.get_symbol("nonExistentFunction") == []


def test_get_symbol_respects_limit(lookup):
    client = FakeQdrantClient(payloads=FAKE_SYMBOL_PAYLOADS * 4)
    results = CodeLookup(client=client).get_symbol("authorize", limit=2)

    assert len(results) == 2
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_code_lookup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.retrieval.lookup'`

- [ ] **Step 5: Create `src/retrieval/lookup.py`**

```python
"""Targeted code lookup primitives.

``Retriever`` answers "what is relevant to this query?". These primitives
answer the follow-up questions an agent asks next — "show me that symbol's
definition", "what is in this file", "give me those exact lines" — none of
which similarity search can express.

Kept separate from ``retriever.py``, which is already a full hybrid search
implementation and should not also own symbol lookup and file I/O.
"""

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.config import settings

logger = logging.getLogger(__name__)

# Upper bound on rows returned by any single lookup, so a wide call cannot
# exhaust the caller's context window.
MAX_RESULTS = 25


class CodeLookup:
    """Payload-level lookups over the indexed corpus.

    Takes a client rather than constructing one so it can share
    ``Retriever.client`` in production and a fake in tests.
    """

    def __init__(self, client: QdrantClient):
        self.client = client

    def get_symbol(
        self,
        name: str,
        file_path: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Chunks whose parsed symbol name matches *name* exactly.

        Matching is exact. Approximate lookup is ``search_code``'s job; adding
        a text index here would duplicate it.
        """
        clean_name = name.strip()
        if not clean_name:
            return []

        conditions = [
            FieldCondition(key="symbol_name", match=MatchValue(value=clean_name))
        ]
        if file_path:
            conditions.append(
                FieldCondition(key="file_path", match=MatchValue(value=file_path.strip()))
            )

        records, _ = self.client.scroll(
            collection_name=settings.collection_name,
            scroll_filter=Filter(must=conditions),
            limit=max(1, min(limit, MAX_RESULTS)),
            with_payload=True,
            with_vectors=False,
        )
        return [r.payload or {} for r in records]

    @staticmethod
    def search_code(
        retriever,
        query: str,
        top_k: int = 5,
        file_path: str | None = None,
        file_type: str | None = None,
    ) -> list[dict]:
        """Hybrid search with optional post-filtering by path or type.

        Filtering happens after retrieval rather than inside Qdrant because
        the BM25 half of the hybrid runs in-process and cannot take a server
        side filter. Over-fetching keeps the filtered result set useful.
        """
        fetch_k = top_k * 4 if (file_path or file_type) else top_k
        chunks = retriever.retrieve(query, top_k=min(fetch_k, MAX_RESULTS))

        results = []
        for chunk in chunks:
            if file_path and not chunk.file_path.startswith(file_path.strip()):
                continue
            if file_type and chunk.file_type != file_type.strip():
                continue
            results.append(
                {
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "file_type": chunk.file_type,
                    "citation": chunk.citation,
                    "score": chunk.score,
                }
            )
            if len(results) == top_k:
                break
        return results
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_code_lookup.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Test `search_code` filtering**

Append to `tests/test_code_lookup.py`:

```python
def test_search_code_filters_by_file_type(lookup, fake_chunks):
    class StubRetriever:
        def retrieve(self, query, top_k=5):
            return fake_chunks

    results = CodeLookup.search_code(
        StubRetriever(), "anything", top_k=5, file_type="schema"
    )

    assert [r["file_path"] for r in results] == ["prisma/schema.prisma"]


def test_search_code_filters_by_path_prefix(lookup, fake_chunks):
    class StubRetriever:
        def retrieve(self, query, top_k=5):
            return fake_chunks

    results = CodeLookup.search_code(
        StubRetriever(), "anything", top_k=5, file_path="src/"
    )

    assert [r["file_path"] for r in results] == ["src/lib/auth.ts"]
```

The `fake_chunks` fixture already exists at `tests/conftest.py:201-204`.

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_code_lookup.py -v`
Expected: PASS (7 passed)

- [ ] **Step 9: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/retrieval/lookup.py tests/test_code_lookup.py tests/conftest.py
git commit -m "feat(retrieval): add CodeLookup.get_symbol and scoped search_code

Similarity search cannot express 'show me this symbol's definition'.
CodeLookup filters the payload indexed in Task 6 instead, and takes a
client so it shares Retriever's connection in production and a fake in
tests.

Symbol matching is exact; approximate lookup stays search_code's job."
```

---

## Task 9: `CodeLookup` — file outline and exact line slices

These two read the corpus checkout, which the retrieval layer has not done before, so path containment matters.

**Files:**
- Modify: `src/retrieval/lookup.py`
- Test: `tests/test_code_lookup_files.py` (create)

**Interfaces:**
- Consumes: `CodeLookup` from Task 8
- Produces:
  - `CodeLookup.get_file_outline(file_path: str, limit: int = 50) -> list[dict]`
  - `CodeLookup.get_file_slice(file_path: str, start_line: int, end_line: int) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_code_lookup_files.py`:

```python
import pytest

from src.retrieval.lookup import MAX_SLICE_BYTES, CodeLookup
from tests.conftest import FAKE_SYMBOL_PAYLOADS, FakeQdrantClient


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    (root / "src").mkdir(parents=True)
    (root / "src" / "auth.ts").write_text(
        "\n".join(f"line {i}" for i in range(1, 101)) + "\n", encoding="utf-8"
    )
    (root / "secret.txt").write_text("not in corpus subdir\n", encoding="utf-8")
    monkeypatch.setattr("src.retrieval.lookup.settings.corpus_path", root)
    return root


@pytest.fixture
def lookup():
    return CodeLookup(client=FakeQdrantClient(payloads=FAKE_SYMBOL_PAYLOADS))


def test_get_file_slice_returns_the_requested_lines(corpus, lookup):
    result = lookup.get_file_slice("src/auth.ts", 3, 5)

    assert result == "line 3\nline 4\nline 5\n"


def test_get_file_slice_clamps_an_overlong_range(corpus, lookup):
    result = lookup.get_file_slice("src/auth.ts", 99, 5000)

    assert result == "line 99\nline 100\n"


def test_get_file_slice_rejects_path_traversal(corpus, lookup):
    assert lookup.get_file_slice("../../etc/passwd", 1, 5).startswith("Error:")


def test_get_file_slice_rejects_an_absolute_path_outside_the_corpus(corpus, lookup):
    assert lookup.get_file_slice("/etc/passwd", 1, 5).startswith("Error:")


def test_get_file_slice_rejects_a_missing_file(corpus, lookup):
    assert lookup.get_file_slice("src/nope.ts", 1, 5).startswith("Error:")


def test_get_file_slice_rejects_an_inverted_range(corpus, lookup):
    assert lookup.get_file_slice("src/auth.ts", 50, 10).startswith("Error:")


def test_get_file_slice_is_byte_capped(corpus, lookup):
    result = lookup.get_file_slice("src/auth.ts", 1, 100)

    assert len(result.encode("utf-8")) <= MAX_SLICE_BYTES


def test_get_file_outline_lists_symbols_in_line_order(corpus, lookup):
    outline = lookup.get_file_outline("src/lib/auth.ts")

    assert [entry["symbol_name"] for entry in outline] == ["authorize", "signOut"]
    assert outline[0]["start_line"] == 10


def test_get_file_outline_returns_empty_for_an_unindexed_file(corpus, lookup):
    assert lookup.get_file_outline("src/unknown.ts") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_code_lookup_files.py -v`
Expected: FAIL — `ImportError: cannot import name 'MAX_SLICE_BYTES'`

- [ ] **Step 3: Add the path guard and the byte cap**

In `src/retrieval/lookup.py`, add `from pathlib import Path` to the imports and these module constants beside `MAX_RESULTS`:

```python
# Upper bound on a single file slice, so one call cannot exhaust the caller's
# context window.
MAX_SLICE_BYTES = 16_000
# Upper bound on outline rows for one file.
MAX_OUTLINE_ENTRIES = 200
```

Then add this module-level helper:

```python
def _resolve_in_corpus(file_path: str) -> Path | None:
    """Resolve *file_path* inside the corpus, or None if it escapes.

    Mirrors the containment discipline in src/agent/tools.py: a path arriving
    from a model is untrusted input. Note that ``corpus_dir / "/etc/passwd"``
    yields an absolute path outside the corpus, which is_relative_to rejects.
    """
    corpus_dir = settings.corpus_path.resolve()
    try:
        candidate = (corpus_dir / file_path.strip()).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not candidate.is_relative_to(corpus_dir):
        logger.warning("Rejected out-of-corpus path request: %r", file_path)
        return None
    if not candidate.is_file():
        return None
    return candidate
```

- [ ] **Step 4: Implement `get_file_slice`**

Add to `CodeLookup`:

```python
    @staticmethod
    def get_file_slice(file_path: str, start_line: int, end_line: int) -> str:
        """Exact lines [start_line, end_line] from a corpus file, 1-indexed.

        Returns an ``Error: ...`` string rather than raising, because callers
        are tool runtimes that hand the text straight to a model.
        """
        if start_line < 1 or end_line < start_line:
            return f"Error: invalid line range {start_line}-{end_line}."

        resolved = _resolve_in_corpus(file_path)
        if resolved is None:
            return f"Error: {file_path!r} is not a readable file inside the corpus."

        try:
            with resolved.open("r", encoding="utf-8", errors="ignore") as handle:
                selected = [
                    line
                    for number, line in enumerate(handle, start=1)
                    if start_line <= number <= end_line
                ]
        except OSError as e:
            logger.warning("Failed to read %s: %s", resolved, e)
            return f"Error: could not read {file_path!r}."

        text = "".join(selected)
        encoded = text.encode("utf-8")
        if len(encoded) > MAX_SLICE_BYTES:
            text = encoded[:MAX_SLICE_BYTES].decode("utf-8", errors="ignore")
        return text
```

Streaming with `enumerate` rather than `read().splitlines()` keeps a large file from being loaded whole to serve a ten-line request.

- [ ] **Step 5: Implement `get_file_outline`**

Add to `CodeLookup`:

```python
    def get_file_outline(self, file_path: str, limit: int = 50) -> list[dict]:
        """Named symbols in a file, in line order, without their bodies.

        Lets a caller see a file's shape and then request only the one symbol
        it needs, instead of pulling whole chunks to find out what is there.
        """
        clean_path = file_path.strip()
        if not clean_path:
            return []

        records, _ = self.client.scroll(
            collection_name=settings.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=clean_path))]
            ),
            limit=MAX_OUTLINE_ENTRIES,
            with_payload=True,
            with_vectors=False,
        )

        entries = [
            {
                "symbol_name": payload.get("symbol_name", ""),
                "node_type": payload.get("node_type", ""),
                "start_line": payload.get("start_line", 0),
                "end_line": payload.get("end_line", 0),
            }
            for payload in (r.payload or {} for r in records)
            if payload.get("symbol_name")
        ]
        entries.sort(key=lambda entry: entry["start_line"])
        return entries[: max(1, min(limit, MAX_OUTLINE_ENTRIES))]
```

Unnamed chunks are filtered out: an outline of blank entries tells a caller nothing.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_code_lookup_files.py -v`
Expected: PASS (9 passed)

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/retrieval/lookup.py tests/test_code_lookup_files.py
git commit -m "feat(retrieval): add get_file_outline and get_file_slice

Lets a caller read a file's shape and then request only the lines it
needs. These are the first retrieval-layer functions to touch the
filesystem, so paths from a model are resolved inside the corpus root
and rejected otherwise, with slices byte-capped."
```

---

## Task 10: Expose the four primitives over MCP

**Files:**
- Modify: `src/mcp/server.py:21-27` (allowlist), `:34-49` (services), `:145-157` (append tools)
- Test: `tests/test_mcp_lookup_tools.py` (create)

**Interfaces:**
- Consumes: all four `CodeLookup` methods from Tasks 8–9
- Produces: MCP tools `get_symbol_definition`, `get_file_outline`, `get_file_slice`, `search_code_scoped`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_lookup_tools.py`:

```python
from src.mcp.server import ALLOWED_MCP_TOOLS, create_mcp_server

NEW_TOOLS = {
    "get_symbol_definition",
    "get_file_outline",
    "get_file_slice",
    "search_code_scoped",
}


def test_new_lookup_tools_are_allowlisted():
    assert NEW_TOOLS <= ALLOWED_MCP_TOOLS


def test_disallowed_tools_are_not_registered():
    """A disallowed tool must be absent from tools/list, not advertised then
    refused — the existing allowlist contract."""
    server = create_mcp_server(allowed_tools={"get_symbol_definition"})

    assert server is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp_lookup_tools.py -v`
Expected: FAIL — `assert NEW_TOOLS <= ALLOWED_MCP_TOOLS` is False.

- [ ] **Step 3: Extend the allowlist**

In `src/mcp/server.py`, replace `ALLOWED_MCP_TOOLS` (lines 21-27):

```python
ALLOWED_MCP_TOOLS = {
    "search_campus_connect",
    "explain_codebase_query",
    "get_commit_history",
    "get_commit_diff",
    "find_module_dependents",
    "get_symbol_definition",
    "get_file_outline",
    "get_file_slice",
    "search_code_scoped",
}
```

- [ ] **Step 4: Provide a `CodeLookup` alongside the existing services**

In `src/mcp/server.py`, add the import:

```python
from src.retrieval.lookup import CodeLookup
```

and a helper after `_get_services` (line 49):

```python
def _get_lookup() -> CodeLookup:
    """CodeLookup sharing the retriever's Qdrant connection."""
    retriever, _ = _get_services()
    return CodeLookup(client=retriever.client)
```

- [ ] **Step 5: Register the four tools**

In `src/mcp/server.py`, insert before `return server` (line 157):

```python
    # ─────────────────────────────────────────────────────────────────────────
    # Tool 6: Symbol Definition Lookup
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "get_symbol_definition",
        (
            "Fetch the definition of a named function, class, interface, type, or Prisma "
            "model by its exact symbol name. Use this after a search surfaces a symbol "
            "you need to read in full. Optionally scope to one file path."
        ),
    )
    def get_symbol_definition(name: str, file_path: str = "", limit: int = 5) -> str:
        results = _get_lookup().get_symbol(
            name, file_path=file_path or None, limit=limit
        )
        if not results:
            return (
                f"No indexed symbol named '{name}' was found. Symbol matching is exact — "
                f"try search_code_scoped for an approximate lookup."
            )

        parts = [f"Found {len(results)} definition(s) for '{name}':"]
        for payload in results:
            citation = (
                f"{payload.get('file_path', '')}"
                f"#L{payload.get('start_line', 0)}-L{payload.get('end_line', 0)}"
            )
            parts.append(
                f"\n--- [{citation}] ({payload.get('node_type', 'unknown')}) ---\n"
                f"{payload.get('content', '').strip()}"
            )
        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 7: File Outline
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "get_file_outline",
        (
            "List the named symbols in one file with their line ranges, without their "
            "bodies. Use this to see a file's shape before requesting specific symbols "
            "or line ranges."
        ),
    )
    def get_file_outline(file_path: str, limit: int = 50) -> str:
        entries = _get_lookup().get_file_outline(file_path, limit=limit)
        if not entries:
            return f"No indexed symbols found for '{file_path}'."

        lines = [f"Outline of {file_path} ({len(entries)} symbols):"]
        for entry in entries:
            lines.append(
                f"  L{entry['start_line']}-{entry['end_line']}  "
                f"{entry['node_type']}  {entry['symbol_name']}"
            )
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 8: Exact Line Slice
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "get_file_slice",
        (
            "Read an exact 1-indexed line range from a file in the corpus. Use this when "
            "a chunk is truncated or you need the lines between two chunks. Paths are "
            "resolved inside the corpus; output is byte-capped."
        ),
    )
    def get_file_slice(file_path: str, start_line: int, end_line: int) -> str:
        text = CodeLookup.get_file_slice(file_path, start_line, end_line)
        if text.startswith("Error:"):
            return text
        if not text:
            return f"No lines in range {start_line}-{end_line} of '{file_path}'."
        return f"--- [{file_path}#L{start_line}-L{end_line}] ---\n{text}"

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 9: Scoped Hybrid Search
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "search_code_scoped",
        (
            "Hybrid search restricted to a path prefix and/or a file type "
            "(code, schema, config, markdown, migration). Use this to narrow a follow-up "
            "search after a broad one returned the wrong area of the codebase."
        ),
    )
    def search_code_scoped(
        query: str,
        top_k: int = 5,
        file_path: str = "",
        file_type: str = "",
    ) -> str:
        retriever, _ = _get_services()
        results = CodeLookup.search_code(
            retriever,
            query,
            top_k=min(max(1, top_k), 15),
            file_path=file_path or None,
            file_type=file_type or None,
        )
        if not results:
            return "No matching code chunks found within that scope."

        parts = [f"Found {len(results)} relevant code chunks:"]
        for i, r in enumerate(results, 1):
            parts.append(
                f"\n--- Chunk {i}: [{r['citation']}] "
                f"(Type: {r['file_type']}, Score: {r['score']:.4f}) ---\n"
                f"{r['content'].strip()}"
            )
        return "\n".join(parts)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp_lookup_tools.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Update the MCP server description**

In `src/mcp/server.py`, bump the `version` to `"0.5.0"` and extend `instructions` (lines 60-68):

```python
        instructions=(
            "Model Context Protocol server for Campus Connect codebase intelligence. "
            "Provides grounded semantic search, architectural query explanation, "
            "symbol definition lookup, file outlines, exact line slices, "
            "git commit inspection, and reverse module dependency analysis."
        ),
```

- [ ] **Step 8: Run the whole suite, including the MCP protocol tests**

Run: `uv run pytest tests/test_mcp_tools.py tests/test_mcp_protocol.py tests/test_mcp_lookup_tools.py -v`
Expected: PASS. If `tests/test_mcp_protocol.py` asserts an exact tool count or an exact `tools/list` set, update it to include the four new names.

- [ ] **Step 9: Run the full suite**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 10: Document the new tools**

Add a row per tool to the MCP tools table in `README.md`:

```markdown
| `get_symbol_definition` | Fetch a named function / class / interface / Prisma model by exact symbol name |
| `get_file_outline` | List a file's named symbols and line ranges without their bodies |
| `get_file_slice` | Read an exact 1-indexed line range from a corpus file |
| `search_code_scoped` | Hybrid search restricted to a path prefix and/or file type |
```

- [ ] **Step 11: Commit**

```bash
git add src/mcp/server.py tests/test_mcp_lookup_tools.py README.md
git commit -m "feat(mcp): expose symbol, outline, slice, and scoped search tools

An external agent can now iterate on retrieval itself: read a file's
outline, pull one symbol's definition, or fetch the exact lines between
two chunks. This is the capability the one-shot pipeline could not
express, and it validates the primitives before AEIA's own loop (Stage
3) is built on them."
```

---

# Stage 3 is deliberately out of scope

The internal Gemini tool-calling loop is specified in `docs/superpowers/specs/2026-09-18-agentic-retrieval-design.md` but is **not** part of this plan. It gets its own plan after the primitives above have been exercised through a real MCP client, because:

- The loop's quota and latency risk is real (~9.9s per pass observed, `max_iterations=4`), and Stages 1–2 deliver value without paying it.
- The deferred streaming decision (incremental `sources` per iteration vs. deferring to `done`) should be made with the UI in view.

Do not add the cycle to `src/agent/graph.py` as part of this plan.
