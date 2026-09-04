# ADR 0009: Containerization and Multi-Service Topology

## Status
Accepted

## Date
2026-09-03

## Context
PRD Functional Requirement FR1.5 requires the system to be fully Dockerized and run with a single command (`docker compose up`). The application consists of two communicating services:
1. Vector database (`qdrant/qdrant:latest`).
2. AEIA FastAPI backend application.

To keep container build times minimal and images small, the build process should leverage `uv` multi-stage dependency caching.

## Decision
1. **Container Base**: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
   - Provides minimal Debian base with pre-installed, high-speed `uv`.
   - Compiles bytecode ahead of time (`UV_COMPILE_BYTECODE=1`).
   - Uses frozen lockfile install (`uv sync --frozen --no-dev`).
2. **Orchestration**: `compose.yml` defines both `qdrant` and `api`:
   - `api` depends on `qdrant` with healthy status.
   - `QDRANT_URL` configured as `http://qdrant:6333` inside the Docker network.
   - Port 8000 mapped to host for external API consumers.

```mermaid
graph TB
    subgraph Host["Host Machine"]
        Client["Browser / curl / IDE Client"]
        Port8000["localhost:8000 (FastAPI / MCP)"]
        Port6333["localhost:6333 (Qdrant Dashboard)"]
    end

    subgraph DockerNet["Docker Network: aeia-network"]
        subgraph APIService["Service: api (uv:python3.12-bookworm-slim)"]
            FastAPIApp["FastAPI Server (src.api.main:app)"]
            FastEmbedLocal["FastEmbed Local ONNX Model"]
        end

        subgraph QdrantService["Service: qdrant (qdrant/qdrant:latest)"]
            QdrantDaemon["Qdrant Vector Daemon"]
            QdrantVol[("Qdrant Storage Volume<br/>/qdrant/storage")]
        end
    end

    subgraph Cloud["External Cloud Services"]
        GeminiAPI["Google AI Studio (Gemini 2.0 Flash)"]
        LangfuseCloud["Langfuse Observability"]
    end

    Client --> Port8000 --> FastAPIApp
    Client --> Port6333 --> QdrantDaemon

    FastAPIApp -->|QDRANT_URL=http://qdrant:6333| QdrantDaemon
    QdrantDaemon --- QdrantVol

    FastAPIApp -->|GEMINI_API_KEY| GeminiAPI
    FastAPIApp -->|Tracing / Metrics| LangfuseCloud

    style Host fill:#f8fafc,stroke:#64748b,stroke-width:2px
    style DockerNet fill:#f0f9ff,stroke:#0284c7,stroke-width:2px
    style APIService fill:#fdf4ff,stroke:#c026d3,stroke-width:1px
    style QdrantService fill:#fef3c7,stroke:#d97706,stroke-width:1px
    style Cloud fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
```

## Consequences
- **Positive**: Entire system (database + AI API) boots in one command on any developer machine or VPS without needing local Python or dependencies.
- **Positive**: Sub-second layer caching during iterative Docker builds.

