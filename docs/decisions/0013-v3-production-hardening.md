# ADR 0013: V3 Production Hardening — Auth, Rate Limiting, CI, and Async Ingestion

## Status
Accepted

## Date
2026-09-05

## Context

The V2 API (`POST /ask`, `GET /health`) was fully open — no authentication, no rate limiting, no CI pipeline, and ingestion blocked the HTTP server for ~24 minutes. Before exposing the API beyond local development, four hardening measures are needed.

## Decision

### 1. API Key Authentication (FR3.3)

Add a required `X-API-Key` header on all mutating/expensive endpoints (`POST /ask`, `POST /ingest`). Public endpoints (`GET /`, `GET /health`, `GET /ingest/status`) remain open.

**Implementation**: A FastAPI `Depends()` function that compares the header value against `settings.api_key`. Returns HTTP 401 on mismatch.

**Key stored in**: `.env` as `API_KEY=dev-key-change-me` (loaded via `pydantic-settings`).

**Design choice — single static key vs. multi-user JWT**: A single shared key is sufficient for V3. The API has a single consumer (the developer / MCP client). Multi-user auth would add JWT token management, user tables, and session logic with no current benefit. Can be upgraded to JWT in V5 when the agent router serves multiple clients.

### 2. Rate Limiting (FR3.4)

Add `slowapi` (a FastAPI wrapper around `limits`) to throttle `POST /ask` at a configurable rate per client IP.

- Default: `20/minute` (configurable via `RATE_LIMIT` env var)
- Key function: `get_remote_address` (client IP from request)
- Exceeded requests return HTTP 429 with a `Retry-After` header
- Only applied to `/ask` — health checks and ingestion status are unlimited

### 3. GitHub Actions CI (FR3.5)

A `.github/workflows/ci.yml` that runs on every push to `main` and every pull request:

1. Spins up a Qdrant service container
2. Installs deps via `uv sync --dev`
3. Runs ingestion to seed Qdrant (needed for integration tests)
4. Runs `pytest -v`

`GEMINI_API_KEY` is stored as a GitHub Actions secret.

### 4. Async Ingestion Queue (FR3.1)

Add `POST /ingest` and `GET /ingest/status` endpoints. Ingestion runs in a background thread via `asyncio.run_in_executor()`, never blocking HTTP request handling.

**State machine**:
```
IDLE → RUNNING → COMPLETED
                → FAILED (with error message)
```

**Design choice — in-process thread vs. external queue (Celery/BullMQ)**: An in-process thread executor is sufficient for V3. The ingestion pipeline is a single long-running batch job (not a stream of tasks). Adding Celery would require a Redis broker dependency and a separate worker process — unnecessary complexity for a single-user system. Can be upgraded in V5 if multiple concurrent ingestion jobs are needed.

## Files Changed

| File | Change |
|------|--------|
| `src/config.py` | Added `api_key` and `rate_limit` settings |
| `src/api/main.py` | Auth dependency, slowapi rate limiter, `/ingest` and `/ingest/status` endpoints, version bump to 0.2.0 |
| `src/api/tasks.py` | **New** — async ingestion runner with status tracking |
| `tests/test_api.py` | Auth tests (missing key, wrong key, valid key), ingestion endpoint tests |
| `pyproject.toml` | Added `slowapi`, version bump to 0.2.0 |
| `.env` | Added `API_KEY` and `RATE_LIMIT` |
| `.github/workflows/ci.yml` | **New** — CI pipeline with Qdrant service container |

## Consequences

### Positive
- API is safe to expose on a network — unauthorized requests are rejected with 401.
- Rate limiting prevents accidental or malicious query floods.
- CI catches regressions automatically on every PR.
- Ingestion can be triggered via API without blocking the server.

### Negative / Open Items
- Single static API key offers no per-user tracking or revocation — upgrade to JWT in V5 if needed.
- Rate limiting is per-IP, which doesn't work behind a shared proxy — may need `X-Forwarded-For` trust config.
- CI ingestion step is slow (~24 min) — consider caching the Qdrant volume or using a pre-built test fixture.
- In-memory ingestion state is lost on server restart — acceptable for V3 single-process deployment.

