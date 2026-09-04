# AEIA Developer Mastery & Onboarding Curriculum
## The Complete Engineering Guide to Building, Understanding, and Extending AEIA

> **Mission**: This curriculum provides a complete, line-by-line understanding of the **AI Engineering Intelligence Assistant (AEIA)** codebase. By completing this guide, any software engineer will possess the exact theoretical knowledge, hands-on experience, and architectural intuition required to build this system from scratch, reason about every design decision, and contribute production-grade improvements.

---

## 1. System Overview: What is AEIA?

**AEIA (AI Engineering Intelligence Assistant)** is an industrial-grade, grounded code intelligence and agentic reasoning system designed to analyze and answer engineering queries about the **Campus Connect** repository (~94k lines of TypeScript, Prisma schemas, SQL migrations, Docker configs, and documentation).

Unlike generic chatbots or naive vector search demos, AEIA solves the fundamental challenges of **Codebase RAG (Retrieval-Augmented Generation)**:
1. **Semantic Opacity in Code & Configs**: Plain embedding models fail on YAML service definitions, SQL DDL, and environment variables. AEIA introduces **Code-Aware Chunking** with **Semantic Prefix Enrichment** to bridge the natural-language to syntax gap.
2. **Precision vs. Recall**: Code retrieval requires both exact keyword matching (function signatures, variable names) and conceptual semantic matching ("user authentication flow"). AEIA implements **Hybrid Retrieval** fusing dense vectors (BGE-small) with sparse lexical search (BM25Okapi) via **Weighted Reciprocal Rank Fusion (RRF 70/30)**.
3. **Strict Grounding & Zero Hallucination**: AI responses cite exact source locations using `[filepath#Lstart-Lend]` line numbers.
4. **Beyond RAG (Agentic Reasoning)**: Queries about git history, commit diffs, or reverse module dependencies cannot be answered by vector search alone. AEIA employs a **LangGraph State Machine** with a **Fast Regex + LLM Router** that dispatches queries to specialized deterministic tools.
5. **Standardized Tool Protocol**: AEIA exposes its capabilities via the official **Model Context Protocol (MCP)** (2026-07-28 stateless HTTP and stdio specifications) for integration into Claude Desktop, Cursor, and IDE sidecars.
6. **Production Resilience**: Includes API Key authentication, client-based rate limiting (`slowapi`), async background ingestion queue, Langfuse request tracing, and graceful degradation under upstream LLM quota exhaustion (`HTTP 429 RESOURCE_EXHAUSTED`).

---

## 2. Curriculum Architecture & Document Roadmap

This onboarding curriculum is organized into modular, deep-dive documents. Read them sequentially or navigate directly to your area of focus:

```mermaid
flowchart TD
    GuideRoot(["docs/developer-guide/"])
    
    GuideRoot --> M0["README.md<br/><b>Master Portal & Syllabus</b>"]
    GuideRoot --> M1["01-technology-stack-and-prerequisites.md<br/><b>16 Technologies Deep-Dive</b>"]
    GuideRoot --> M2["02-architecture-design-and-patterns.md<br/><b>V1-V7 Topology & Patterns</b>"]
    GuideRoot --> M3["03-file-by-file-mastery-catalog.md<br/><b>59 File Inventory & Anatomy</b>"]
    GuideRoot --> M4["04-step-by-step-build-curriculum.md<br/><b>14-Day Hands-on Roadmap</b>"]
    GuideRoot --> M5["05-benchmarking-evaluation-and-contributing.md<br/><b>IR Metrics & Contributing</b>"]

    style GuideRoot fill:#f0f7ff,stroke:#2563eb,stroke-width:2px
    style M0 fill:#f8fafc,stroke:#64748b,stroke-width:1px
    style M1 fill:#fdf4ff,stroke:#c026d3,stroke-width:1px
    style M2 fill:#f0fdf4,stroke:#16a34a,stroke-width:1px
    style M3 fill:#fef3c7,stroke:#d97706,stroke-width:1px
    style M4 fill:#eff6ff,stroke:#3b82f6,stroke-width:1px
    style M5 fill:#faf5ff,stroke:#a855f7,stroke-width:1px
```

### Document Summary

| Document | Purpose | Key Question Answered |
| :--- | :--- | :--- |
| [**01 — Technology Stack & Prerequisites**](01-technology-stack-and-prerequisites.md) | Comprehensive reference for every tool, library, algorithm, and theoretical concept used in AEIA. | *"What technologies do I need to learn, and what hands-on exercises should I build first?"* |
| [**02 — Architecture, Design & Patterns**](02-architecture-design-and-patterns.md) | Deep exploration of the 7 evolutionary versions, software patterns, data flow, and error mitigation strategies. | *"How do the components connect together, and why was the system designed this way?"* |
| [**03 — File-by-File Mastery Catalog**](03-file-by-file-mastery-catalog.md) | Comprehensive line-by-line inspection of all 59 files in the repository. No file left out. | *"What does this line do, why is it here, and how do I safely edit or improve this file?"* |
| [**04 — Step-by-Step Build Curriculum**](04-step-by-step-build-curriculum.md) | Structured 14-day interactive learning roadmap with concrete coding exercises from blank slate to production. | *"How do I build this entire system on my own from scratch?"* |
| [**05 — Benchmarking, Evaluation & Contributing**](05-benchmarking-evaluation-and-contributing.md) | Explains the 20-query golden dataset, IR metrics (Recall@5, Recall@10, MRR), CI automation, and contribution rules. | *"How do I verify my changes without regressing retrieval performance?"* |

---

## 3. Tailored Learning Tracks (Developer Archetypes)

Depending on your engineering background, select the recommended path below to ramp up efficiently:

```mermaid
graph TD
    Start["Choose Your Track"] --> A["Track A: Python / Backend Engineer"]
    Start --> B["Track B: AI / Search / RAG Engineer"]
    Start --> C["Track C: Agentic & Systems Engineer"]
    Start --> D["Track D: DevOps / Reliability Engineer"]

    A --> Doc1["01 - Tech Stack: FastAPI, Pydantic, SlowAPI"]
    A --> Doc3A["03 - File Catalog: src/api/, src/config.py, src/errors.py"]

    B --> Doc1B["01 - Tech Stack: Qdrant, FastEmbed, BM25, RRF"]
    B --> Doc3B["03 - File Catalog: src/ingestion/, src/retrieval/, src/generation/"]
    B --> Doc5["05 - Benchmarking & Metrics"]

    C --> Doc1C["01 - Tech Stack: LangGraph, MCP Spec, StateMachines"]
    C --> Doc3C["03 - File Catalog: src/agent/, src/mcp/"]

    D --> Doc1D["01 - Tech Stack: Docker, Compose, uv, Langfuse, GitHub Actions"]
    D --> Doc3D["03 - File Catalog: Dockerfile, compose.yml, .github/workflows/ci.yml"]
```

### Track A: The Python & API Backend Engineer
- **Goal**: Understand the service interface, concurrency, dependency injection, and security.
- **Priority Reading**:
  1. Read [01 — Tech Stack](01-technology-stack-and-prerequisites.md) sections on **Python 3.12+**, **FastAPI**, **Pydantic V2**, and **SlowAPI**.
  2. Read [02 — Architecture](02-architecture-design-and-patterns.md) on **Lifespan Management** and **Typed Exceptions**.
  3. Study [03 — File Catalog](03-file-by-file-mastery-catalog.md) entries for [`src/api/main.py`](../../src/api/main.py), [`src/api/tasks.py`](../../src/api/tasks.py), [`src/config.py`](../../src/config.py), and [`src/errors.py`](../../src/errors.py).
  4. Run tests: `uv run pytest tests/test_api.py tests/test_error_handling.py -v`.

### Track B: The AI, Search & Information Retrieval Engineer
- **Goal**: Master the RAG pipeline, dense embeddings, BM25 Okapi, RRF ranking, and LLM synthesis.
- **Priority Reading**:
  1. Read [01 — Tech Stack](01-technology-stack-and-prerequisites.md) sections on **Qdrant**, **FastEmbed / BGE-small**, **BM25**, **Weighted RRF**, and **Google GenAI**.
  2. Read [02 — Architecture](02-architecture-design-and-patterns.md) on **Hybrid Retrieval Strategy** and **Semantic Prefix Injection**.
  3. Read Postmortem [`docs/postmortems/001-semantic-bias-config-retrieval.md`](../postmortems/001-semantic-bias-config-retrieval.md).
  4. Study [03 — File Catalog](03-file-by-file-mastery-catalog.md) entries for [`src/ingestion/chunker.py`](../../src/ingestion/chunker.py), [`src/ingestion/pipeline.py`](../../src/ingestion/pipeline.py), [`src/retrieval/retriever.py`](../../src/retrieval/retriever.py), and [`src/generation/generator.py`](../../src/generation/generator.py).
  5. Run benchmark: `PYTHONPATH=. uv run python evals/run_eval.py`.

### Track C: The Agentic Systems & Protocol Engineer
- **Goal**: Understand state graph routing, tool dispatch, and Model Context Protocol (MCP) integrations.
- **Priority Reading**:
  1. Read [01 — Tech Stack](01-technology-stack-and-prerequisites.md) sections on **LangGraph** and **Model Context Protocol (MCP)**.
  2. Read [02 — Architecture](02-architecture-design-and-patterns.md) on the **Agentic Router State Machine** and **Stateless HTTP MCP Mounting**.
  3. Study [03 — File Catalog](03-file-by-file-mastery-catalog.md) entries for [`src/agent/state.py`](../../src/agent/state.py), [`src/agent/tools.py`](../../src/agent/tools.py), [`src/agent/router.py`](../../src/agent/router.py), [`src/agent/graph.py`](../../src/agent/graph.py), and [`src/mcp/server.py`](../../src/mcp/server.py).
  4. Run tests: `uv run pytest tests/test_agent_router.py tests/test_agent_tools.py tests/test_agent_api.py tests/test_mcp_protocol.py tests/test_mcp_tools.py -v`.

### Track D: The Platform, DevOps & Reliability Engineer
- **Goal**: Master local container topology, production packaging, GitHub Actions CI, and observability.
- **Priority Reading**:
  1. Read [01 — Tech Stack](01-technology-stack-and-prerequisites.md) sections on **uv**, **Docker / Compose**, **Langfuse**, and **GitHub Actions**.
  2. Study [03 — File Catalog](03-file-by-file-mastery-catalog.md) entries for [`Dockerfile`](../../Dockerfile), [`compose.yml`](../../compose.yml), [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), and [`src/observability/__init__.py`](../../src/observability/__init__.py).
  3. Run full test suite: `uv run pytest -v`.

---

## 4. Repository Quick-Reference Map

Every file in the repository serves a distinct operational purpose. Below is the master blueprint:

```mermaid
flowchart TD
    Root["<b>aeia/ (Root Workspace)</b>"]

    Root --> Cfg["<b>Root Config & Entrypoints</b><br/><code>pyproject.toml, uv.lock, Dockerfile, compose.yml, main.py</code>"]
    Root --> CI["<b>CI/CD Automation</b><br/><code>.github/workflows/ci.yml</code>"]
    Root --> Src["<b>Application Core (src/)</b>"]
    Root --> Evals["<b>Evaluations (evals/)</b><br/><code>dataset.json, run_eval.py</code>"]
    Root --> Tests["<b>Test Suites (tests/)</b><br/><code>9 test modules (chunker, retriever, api, agent, mcp, errors)</code>"]
    Root --> Docs["<b>Documentation (docs/)</b><br/><code>decisions/ (17 ADRs), postmortems/, developer-guide/</code>"]
    Root --> Corpus["<b>Target Corpus (corpus/)</b><br/><code>campus-connect (~94k LOC full-stack app)</code>"]

    Src --> S_Ingest["<code>ingestion/</code><br/><i>chunker.py, pipeline.py (cache & upsert)</i>"]
    Src --> S_Ret["<code>retrieval/</code><br/><i>retriever.py (Hybrid RRF 70/30)</i>"]
    Src --> S_Gen["<code>generation/</code><br/><i>generator.py (Gemini 2.0 Flash)</i>"]
    Src --> S_Agent["<code>agent/</code><br/><i>state.py, router.py, tools.py, graph.py</i>"]
    Src --> S_Mcp["<code>mcp/</code><br/><i>server.py (2026-07-28 HTTP & Stdio)</i>"]
    Src --> S_Api["<code>api/</code><br/><i>main.py (FastAPI), tasks.py (async queue)</i>"]
    Src --> S_Obs["<code>observability/</code><br/><i>Langfuse spans & latency</i>"]
    Src --> S_Base["<code>src/</code> Base<br/><i>config.py (pydantic), errors.py (domain exceptions)</i>"]

    style Root fill:#f0f7ff,stroke:#2563eb,stroke-width:2px
    style Src fill:#fdf4ff,stroke:#c026d3,stroke-width:2px
    style Corpus fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    style Docs fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style Tests fill:#eff6ff,stroke:#3b82f6,stroke-width:1px
    style Evals fill:#faf5ff,stroke:#a855f7,stroke-width:1px
```

---

## 5. Development Environment Setup

To begin working with AEIA, run the following commands in your shell:

### Step 1: Install `uv` (Fast Python Package Manager)
```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Clone and Synchronize Virtual Environment
```bash
cd /home/krotrn/coding/aeia

# uv sync creates the virtual environment and installs all dependencies exactly as locked in uv.lock
uv sync --dev
```

### Step 3: Configure Environment Variables
Create or verify your `.env` file at the repository root:
```ini
# Required for Gemini answer generation (Free tier key from https://aistudio.google.com/)
GEMINI_API_KEY="your_api_key_here"

# Qdrant vector database URL
QDRANT_URL="http://localhost:6333"
COLLECTION_NAME="campus_connect"

# Authentication & Rate Limiting
API_KEY="dev-key-change-me"
RATE_LIMIT="20/minute"

# Optional: Langfuse tracing (leave empty to disable)
LANGFUSE_PUBLIC_KEY=""
LANGFUSE_SECRET_KEY=""
LANGFUSE_HOST="https://cloud.langfuse.com"
```

### Step 4: Start Qdrant and Ingest Corpus
```bash
# Start Qdrant container in background
docker compose up -d qdrant

# Ingest corpus (chunks codebase, embeds with FastEmbed, uploads to Qdrant)
PYTHONPATH=. uv run python -m src.ingestion.pipeline
```

### Step 5: Run the API Server & Verification Tests
```bash
# Start FastAPI development server with hot reload
PYTHONPATH=. uv run uvicorn src.api.main:app --reload --port 8000

# In a separate terminal, run the automated test suite:
uv run pytest -v

# Run the retrieval benchmark:
PYTHONPATH=. uv run python evals/run_eval.py
```

---

## 6. Next Steps

Proceed immediately to **[01 — Technology Stack and Prerequisites](01-technology-stack-and-prerequisites.md)** to begin learning the exact technologies, mathematical concepts, and engineering patterns required to master this system.

