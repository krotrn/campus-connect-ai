# ADR 0011: Automated Testing Architecture (Unit, Integration, and Regression)

## Status
Accepted

## Date
2026-09-03

## Context
A production-grade AI engineering system requires a robust automated testing pyramid covering:
1. **Unit Tests**: Verifying deterministic code logic (chunking algorithms, AST splitting, line number calculation, payload validation).
2. **Integration Tests**: Verifying external integrations (vector similarity queries against running Qdrant instance, FastAPI endpoints, input validation error handling).
3. **Regression / Eval Tests**: Ensuring retrieval accuracy metrics (Recall@K, MRR) do not regress below baseline thresholds.

Without automated tests, changes to chunking parameters or prompt engineering could silently break citation tracking or API contracts.

## Decision
We implement a three-tiered test suite using `pytest` and `pytest-asyncio`:
1. `tests/test_chunker.py`: Unit tests validating TypeScript AST boundaries, markdown header extraction, exact 1-indexed line calculations, and error resilience.
2. `tests/test_retriever.py`: Integration tests validating vector embedding generation, Qdrant similarity searches, top-K constraints, and citation formatting.
3. `tests/test_api.py`: FastAPI `TestClient` tests validating `GET /health`, `POST /ask` contract conformity, and `422` validation errors on invalid inputs.

## Consequences
- **Positive**: Full test coverage of core ingestion, retrieval, and API logic runnable locally with a single `uv run pytest`.
- **Positive**: Ready for CI/CD automation in GitHub Actions.

