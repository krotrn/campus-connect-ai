# ADR 0008: FastAPI Service Interface and Latency Instrumentation

## Status
Accepted

## Date
2026-09-03

## Context
PRD Functional Requirement FR1.4 mandates exposing the RAG pipeline over an HTTP API (`POST /ask {question} -> {answer, sources}`). Non-functional requirements (Section 9) specify P95 latency tracking and input validation.

We need a lightweight, async-ready HTTP framework with automatic OpenAPI documentation, schema validation, and request-level timing instrumentation.

## Decision
We implement the API layer using **FastAPI** in `src/api/main.py`:
1. **Schema Validation**:
   - `AskRequest`: Enforces non-empty questions (`min_length=3`) and bounded `top_k` (between 1 and 20).
   - `AskResponse`: Strictly typed JSON containing the question, grounded answer, list of sources with file/line ranges, and `latency_ms`.
2. **Endpoints**:
   - `GET /health`: Probes Qdrant connectivity and reports collection point count.
   - `POST /ask`: Coordinates retrieval and generation, recording end-to-end execution latency in milliseconds.
3. **Lifespan Management**:
   - Initializes singleton instances of `Retriever` and `AnswerGenerator` during application startup to avoid re-instantiating models on every request.

## Consequences
- **Positive**: Clean separation between core RAG logic and HTTP transport; automatic interactive documentation available at `/docs` (Swagger UI).
- **Positive**: Direct measurement of response latency provides the baseline for V2/V3 performance tracking.

