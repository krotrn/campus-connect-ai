# PRD: AI Engineering Intelligence Assistant

**Status:** Draft v1
**Owner:** You
**Type:** Personal portfolio flagship project (production-grade)

---

## 1. Problem Statement

Developers joining or returning to a codebase spend a disproportionate amount of time answering questions that already have answers scattered across source code, docs, commit history, and issues — but not in one place, and not in natural language:

- "Where is X implemented?"
- "Why did this break after that change?"
- "What depends on this module?"
- "How do I set this up locally?"

Existing tools solve pieces of this (grep, GitHub search, docs sites) but none reason across code + docs + history + config together, or explain *why*, not just *where*.

**This project builds a system that ingests a real software project (code, docs, git history, config) and answers engineering questions about it — with citations, measured accuracy, and production-grade reliability.**

The point of the project is not the chatbot. It's proving you can design, evaluate, deploy, and operate an AI system responsibly — the skill the 2026 market actually screens for.

---

## 2. Goals

1. Ship a working, deployed system — not a notebook demo.
2. Prove retrieval and answer quality with measured evaluation metrics, tracked over versions.
3. Demonstrate production engineering: async ingestion, error handling, observability, CI, deployment.
4. Demonstrate agentic reasoning (routing, tool use) once the RAG core is proven.
5. Demonstrate MCP as a real, callable tool interface — not just a buzzword.
6. Produce a README/repo that functions as an interview artifact on its own.

## 3. Non-Goals (v1–v3)

- No fine-tuning or custom model training in the initial phases.
- No multi-tenant SaaS, billing, or user management beyond basic auth.
- No Kubernetes / complex microservice topology.
- No multi-agent swarm (>2 collaborating agents) — one router + a small number of tools is enough to prove the concept.
- Not trying to outperform GitHub Copilot / Cursor. This is a focused engineering-intelligence tool, not a general coding assistant.

---

## 4. Target User / Persona

**Primary:** A developer (could be you, or a hypothetical new hire) joining an existing codebase who needs fast, grounded answers about architecture, code location, and history — without reading everything first.

**Secondary (portfolio audience):** A technical interviewer or hiring manager evaluating whether you can build and reason about production AI systems.

---

## 5. Core Use Cases

| # | User story | Example question |
|---|---|---|
| 1 | Architecture navigation | "What is the request flow from the frontend to the database?" |
| 2 | Code location | "Where is authentication implemented?" |
| 3 | Change analysis | "Which files changed when feature X was added?" |
| 4 | Debugging assistance | "What components are involved in processing a login request?" |
| 5 | Dependency reasoning | "What depends on this module/service?" |
| 6 | Onboarding | "How do I set this project up locally?" |
| 7 | Config/schema lookup | "What environment variables does the payment service need?" |

Each of these becomes a labeled item in the evaluation dataset (Section 8).

---

## 6. Corpus Definition — **CONFIRMED**

- **Repository**: [`coding-pundit-nitap/campus-connect`](https://github.com/coding-pundit-nitap/campus-connect) (Cloned into `./corpus/campus-connect`)
- **Primary Languages**: TypeScript (385 files), TSX / React (352 files), Markdown (7 files), SQL / Prisma, YAML / JSON.
- **Approximate Size**: 808 files, ~94,300 lines of code across source code, configurations, and documentation.
- **Key Artifacts Present**:
  - Extensive `ARCHITECTURE.md` (32 KB) detailing domain design, data flows, and services.
  - Full documentation (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/`).
  - Multi-tier deployment: `compose.dev.yml`, `compose.prod.yml`, `Dockerfile`, `nginx/`, `monitoring/`.
  - Database schema: `prisma/schema.prisma` and migrations.
  - Active git commit history for change tracking.
- **Excluded Content**: Real `.env` files, `.git`, build outputs (`.next`, `dist`), `node_modules`, binary media.

Corpus ingestion targets:
```
README.md, ARCHITECTURE.md, docs/ (Markdown headers chunking)
src/, workers/ (TypeScript/TSX class, interface, and function boundary chunking)
prisma/schema.prisma (Model and enum chunking)
compose*.yml, Dockerfile, package.json (Config chunking)
git commit history (message + changed files summary)
```

---

## 7. Functional Requirements

### V1 — Core RAG (Week 1)
- FR1.1: Ingest a defined corpus (files → parsed → chunked → embedded → stored)
- FR1.2: Vector similarity retrieval (pgvector or Qdrant)
- FR1.3: LLM answer generation grounded in retrieved chunks, with source citations
- FR1.4: FastAPI endpoint: `POST /ask {question} → {answer, sources}`
- FR1.5: Fully Dockerized, runs with one command

### V2 — Evaluated RAG (Weeks 2–3)
- FR2.1: Hand-labeled evaluation dataset (min. 20–30 Q/A pairs with expected sources)
- FR2.2: Automated metrics: Recall@5, Recall@10, Faithfulness, Answer Relevance
- FR2.3: Hybrid retrieval (BM25 + vector) as a measured improvement
- FR2.4: Reranking as a measured improvement
- FR2.5: Each improvement recorded in README metrics table with before/after numbers

### V3 — Production Hardening (Week 4)
- FR3.1: Async background ingestion (queue-based, not blocking request)
- FR3.2: Structured logging, error handling, retries on LLM/embedding calls
- FR3.3: Basic auth (API key or JWT) on endpoints
- FR3.4: Rate limiting on the `/ask` endpoint
- FR3.5: Automated tests (unit + integration) with CI running on push

### V4 — Observability (Week 5)
- FR4.1: Full trace per request (retrieval latency, rerank latency, LLM latency, token cost)
- FR4.2: Langfuse (or equivalent) dashboard
- FR4.3: At least 2 documented failure-mode investigations (a real hallucination or retrieval miss, root-caused)

### V5 — Agentic Layer (Week 6)
- FR5.1: Router node: simple lookup vs. multi-step reasoning vs. tool action
- FR5.2: Built with an explicit state machine (LangGraph or equivalent) — no ad hoc while-loops
- FR5.3: At least one non-RAG tool call (e.g., "which files changed in commit X")

### V6 — MCP (Week 7)
- FR6.1: One real MCP server exposing at least 2 tools (e.g., `search_documents`, `get_commit_history`)
- FR6.2: Agent calls MCP tools under explicit permission/allowlist, not unrestricted access

### V7 — Evaluation CI (Week 8)
- FR7.1: GitHub Actions workflow runs the eval suite on every PR
- FR7.2: PR fails if retrieval/generation metrics regress below a defined threshold vs. baseline

---

## 8. Evaluation Dataset Spec

Each item:
```json
{
  "id": "q001",
  "question": "Where is user authentication implemented?",
  "expected_sources": ["src/auth/login.py", "src/auth/middleware.py"],
  "expected_answer_summary": "Auth is handled via JWT middleware in auth/middleware.py, login logic in auth/login.py",
  "category": "code_location"
}
```
Minimum 20–30 items across all 7 use case categories in Section 5 before V2 metrics are meaningful.

---

## 9. Non-Functional Requirements

| Requirement | Target (initial) |
|---|---|
| P95 latency (simple query) | < 5s |
| P95 latency (agentic query) | < 12s |
| Cost per query (tracked, not necessarily minimized in v1) | Measured and shown in observability |
| Uptime (deployed instance) | Best-effort; not an SLA-backed service |
| Security | No secrets in corpus; API auth required; input validation on all endpoints |

---

## 10. Success Metrics (What "Done" Looks Like)

- [ ] Deployed, publicly accessible instance (or clearly documented local run)
- [ ] README shows a version-over-version metrics table (Recall@10, Faithfulness, P95 latency) proving iterative improvement
- [ ] At least one documented failure investigated and fixed, with before/after evidence
- [ ] CI pipeline that can fail a PR on eval regression
- [ ] One working MCP server integration
- [ ] One working agentic router with at least one tool call

## 11. Repository Structure (Target)

```
README.md
src/
  ingestion/
  retrieval/
  generation/
  agents/
  mcp/
  api/
tests/
evals/
  dataset.json
  run_eval.py
docker/
docs/
  architecture.md
  decisions/        # short ADRs for major choices
.github/workflows/
  eval-ci.yml
```

## 12. Architectural Decisions & Open Questions

### Resolved Decisions
1. **Corpus**: `coding-pundit-nitap/campus-connect` (See [ADR 0001](docs/decisions/0001-target-corpus.md)).
2. **Local Environment**: `uv` package manager with Python 3.12 (See [ADR 0004](docs/decisions/0004-python-toolchain-uv.md)).
3. **Vector DB & Embeddings**: Qdrant (Docker) + FastEmbed `BAAI/bge-small-en-v1.5` for local zero-cost embeddings (See [ADR 0002](docs/decisions/0002-zero-cost-embedding-and-vector-db.md)).
4. **LLM Provider**: Google Gemini 2.0 Flash / 1.5 Flash via Google AI Studio free tier (See [ADR 0003](docs/decisions/0003-llm-provider-gemini.md)).

### Open Questions (deferred to V3/V4)
1. Deployment target for the live instance — Railway, Fly.io, Render, or a VPS?

---

## 13. Milestone Timeline (reference)

| Week | Milestone |
|---|---|
| 1 | V1 core RAG working end-to-end, ugly is fine |
| 2–3 | V2 evaluated + improved RAG, metrics table started |
| 4 | V3 production hardening |
| 5 | V4 observability |
| 6 | V5 agentic router |
| 7 | V6 MCP server |
| 8 | V7 evaluation CI |