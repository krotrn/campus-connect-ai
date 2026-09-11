# ADR 0032: Production Hardening — Credential Boundary, Async Correctness & Offline Test Strategy

## Status

Accepted

## Date

2026-09-11

## Context

A full audit of the codebase ahead of deployment surfaced a set of defects that
shared a common shape: each worked in local development and failed — silently or
loudly — the moment the system met a real deployment, a second concurrent user,
or an enabled optional feature.

**Credential boundary.** The console read the backend API key from
`NEXT_PUBLIC_API_KEY`. Next inlines any `NEXT_PUBLIC_`-prefixed value into the
client bundle, so the key shipped to every visitor's browser and `X-API-Key`
authentication was decorative. This was compounded by `CORSMiddleware` being
configured with `allow_origins=["*"]` *and* `allow_credentials=True` — a
combination browsers reject outright on credentialed requests, and which in
combination with the exposed key left the API effectively open.

**Async correctness.** `/ask` and `/agent/ask` were declared `async def` but
performed entirely synchronous work: embedding, Qdrant I/O, and multi-second
Gemini calls. That work therefore ran on the event loop, serializing all
requests behind whichever question was in flight — including `/health`.

**Dependency drift.** `src/observability` targeted the Langfuse v2 client API
(`client.trace()`, `trace.span()`, `trace.generation()`). `pyproject.toml` pins
`langfuse>=4.15.1`, whose client exposes none of those methods. Tracing appeared
to work only because the keys were unset, short-circuiting to the untraced path.
Configuring Langfuse would have turned every `/ask` into a 500.

**Deployment path.** The container copied only `src/`, so the corpus the agent's
git tools and the webhook operate on was absent, and every non-RAG route failed
inside Docker. The compose healthcheck shelled out to `curl`, which the slim base
image does not ship, so the API container could never report healthy.

**Verification.** Fifteen of seventeen test files required a live Qdrant *and* a
real Gemini key. With the stack down the suite hung indefinitely rather than
failing, and there was no CI workflow despite the README advertising one.

## Decision

### 1. The credential boundary moves to the server

The browser no longer holds the backend API key. Requests go to Next route
handlers under `frontend/src/app/api/aeia/*`, which read server-only
`AEIA_API_URL` / `AEIA_API_KEY` and attach `X-API-Key` before proxying to
FastAPI. `getServerEnv()` throws if called from the browser, so a mistaken
import into a client component fails loudly rather than leaking.

Proxying to an *arbitrary* user-supplied URL would make the console an open
proxy, so the "custom backend" feature is preserved differently: when a user
enters their own backend URL, the browser calls that host **directly** and the
user supplies the key for *their* deployment. That key is theirs, and is only
ever sent to the host they named.

CORS is narrowed to configured origins with `allow_credentials=False`, and both
API key comparisons (the dependency and the MCP mount's ASGI middleware) use
`secrets.compare_digest`. A missing key now returns `401`, not `422` — a missing
credential is an authentication failure, not a schema violation.

### 2. Synchronous handlers run in the threadpool

`/ask`, `/ask/stream`, `/agent/ask`, and `/health` are declared `def`, not
`async def`. FastAPI runs sync handlers in a worker threadpool, so a slow
question no longer blocks the event loop. This is deliberate and load-bearing:
re-adding `async` to these handlers without also making the pipeline awaitable
would reintroduce the stall.

`/ask` and `/ask/stream` both delegate to a shared `_ask_impl`. Previously
`/ask/stream` called the `@limiter.limit`-decorated `/ask` handler, so slowapi
counted each streaming request twice and halved the caller's effective budget.

### 3. Route once, per request

The API layer classifies the query and passes the decision into the agent graph,
whose `router_node` reuses a pre-resolved route instead of re-classifying.
Ambiguous queries previously paid for two LLM classification calls. The router
also now accepts a caller-supplied Gemini key; it previously read only the server
key, so client-key users — the exact audience of ADR 0029 — silently got
`direct_rag` for every question.

### 4. Tracing may never fail a request

`src/observability` is rewritten against the v4 observation API
(`start_as_current_observation`, nested by context manager). Beyond the port,
`traced_ask` now catches any tracing exception and retries untraced. Observability
is not worth a user-visible error.

### 5. Ingestion is non-destructive by default

`IngestionPipeline.run()` defaults to `recreate=False`: chunks are upserted under
their deterministic point IDs and stale points are pruned *afterwards*, so the
collection stays queryable for the whole run. Pruning compares live
`(file_path, chunk_index)` keys against what is indexed, which also removes
points for deleted files and for files that now produce fewer chunks — neither of
which an upsert-only pass cleaned up. `recreate=True` remains available for
schema changes and is documented as causing downtime.

`trigger_ingestion()` claims the RUNNING state under a single lock. The previous
check-then-set allowed two concurrent `POST /ingest` calls to both start, which
under the old destructive default meant two runs recreating the same collection.

### 6. The embedding cache becomes a SQLite store

The JSON cache had grown to 62 MB and was decoded in full on every
`IngestionPipeline()` construction — seconds of parsing and hundreds of megabytes
of Python floats, per ingest trigger. Vectors now live in SQLite as float32
blobs, read back only for the hashes actually requested and committed per batch,
so an interrupted run keeps its progress. Existing JSON caches are migrated once
on first construction.

### 7. Tests run offline by default

`tests/conftest.py` supplies in-memory fakes for the retriever, generator, router
and query rewriter. The default suite needs no Qdrant, no API key, and no model
download, and completes in ~30 seconds — which is what makes CI possible.
`AEIA_TEST_MODE=integration` exercises the real stack for anyone who wants it.

`tests/test_regressions.py` pins each defect fixed here, including static guards
(the streaming route must not call the rate-limited handler; the observability
module must not reintroduce `_langfuse.trace(`). `.github/workflows/ci.yml` runs
backend lint and tests, frontend lint, typecheck, tests and build, and a Docker
image build.

## Consequences

**Positive**

- The backend credential is no longer obtainable from the browser.
- Concurrent questions are served in parallel rather than serialized.
- Enabling Langfuse no longer breaks the API; a tracing bug degrades to untraced.
- The Docker image can actually run the agent, webhook, and healthcheck.
- Re-ingestion no longer blanks the index, and stale chunks are removed.
- CI can run on every push without infrastructure or API spend.

**Negative / trade-offs**

- **Breaking config change.** `NEXT_PUBLIC_API_KEY` is replaced by server-only
  `AEIA_API_KEY`, and `NEXT_PUBLIC_API_URL` by `AEIA_API_URL`. Existing
  deployments must update their environment; see `frontend/.env.example`.
- The console now requires a Node server for its route handlers. It can no
  longer be exported as a purely static site — acceptable, since it is deployed
  on Vercel/Node already.
- `CORS_ALLOW_ORIGINS` must be set explicitly for any origin calling the API
  directly from browser JavaScript; the previous wildcard hid this requirement.
- `MCP_ALLOWED_HOSTS` must name the deployed hostname. The previous hardcoded
  localhost list would have rejected all production traffic, so this surfaces a
  requirement rather than adding one.
- The SQLite cache is a new on-disk format. The one-time JSON migration keeps
  existing work; the legacy `.cache/embedding_cache.json` can be deleted after.

## References

- Supersedes the CORS and credential handling described in
  [ADR 0029](0029-client-side-api-key-injection-and-quota-resilience.md).
- Revises the tracing implementation in
  [ADR 0014](0014-v4-observability-langfuse-tracing.md).
- Revises the ingestion strategy in
  [ADR 0020](0020-incremental-delta-only-ingestion.md).
- Extends the testing strategy in
  [ADR 0011](0011-automated-testing-strategy.md).
