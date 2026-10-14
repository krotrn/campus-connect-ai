# AEIA — AI Engineering Intelligence Assistant

Ask questions about a codebase in plain English and get answers with citations to the source files.

AEIA indexes [campus-connect](https://github.com/coding-pundit-nitap/campus-connect) (code, docs, config and git history) and answers questions like "Where is authentication implemented?" or "What changed in commit abc1234?".

## How it works

- **Ingestion**: syntax-aware chunking, local embeddings (FastEmbed `bge-small-en-v1.5`), stored in Qdrant.
- **Retrieval**: hybrid dense + BM25 search fused with RRF, then reranked with FlashRank.
- **Generation**: Gemini answers using only the retrieved context, with file and line citations.
- **Agent**: a LangGraph router sends each question to RAG, git history, commit diff or dependency lookup.
- **Interfaces**: FastAPI (REST + SSE streaming), an MCP server, and a Next.js web console in `frontend/`.

## Quick start

You need Python 3.12, [uv](https://docs.astral.sh/uv/), Docker and a free [Gemini API key](https://aistudio.google.com/).

```bash
cp .env.example .env              # then set GEMINI_API_KEY
git clone https://github.com/coding-pundit-nitap/campus-connect corpus/campus-connect

docker compose up -d qdrant
uv sync
uv run python -m src.ingestion.pipeline
uv run uvicorn src.api.main:app --reload
```

The API runs at http://localhost:8000 and its interactive docs are at `/docs`.

To run everything in Docker instead, use `docker compose up --build`.

### Web console

```bash
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev
```

Open http://localhost:3000.

## API

All endpoints except `/` and `/health` require an `X-API-Key` header.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/ask` | Ask a question (RAG) |
| POST | `/ask/stream` | Same as `/ask`, streamed over SSE |
| POST | `/agent/ask` | Ask through the agent router |
| POST | `/ingest` | Start ingestion in the background |
| GET | `/ingest/status` | Ingestion progress |
| POST | `/webhook/github` | Re-ingest changed files on push |
| — | `/mcp` | MCP server (streamable HTTP) |

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-change-me" \
  -d '{"question": "Where is user authentication implemented?"}'
```

To run the MCP server over stdio (for Claude Desktop, Cursor, etc.), use `uv run python -m src.mcp.server`.

## Configuration

Settings come from `.env`. See [`.env.example`](.env.example) for the full list.

| Variable | Required | Default |
|---|---|---|
| `GEMINI_API_KEY` | yes | — |
| `QDRANT_URL` | no | `http://localhost:6333` |
| `QDRANT_API_KEY` | no (needed for Qdrant Cloud) | — |
| `API_KEY` | no | `dev-key-change-me` |
| `CORPUS_PATH` | no | `./corpus/campus-connect` |
| `LANGFUSE_*` | no (enables tracing) | — |
| `GITHUB_WEBHOOK_SECRET` | no | — |

## Development

```bash
uv run ruff check .
uv run pytest -q                  # uses in-memory fakes; no Qdrant or API key needed
uv run python evals/run_eval.py   # retrieval benchmark (Recall@K, MRR); add --generation for the RAG triad
```

For the frontend, run `pnpm lint`, `pnpm typecheck` and `pnpm test` in `frontend/`.

## Project layout

```
src/
  api/          FastAPI app, background tasks, GitHub webhook
  agent/        LangGraph router, tools, conversation memory
  ingestion/    chunkers, embedding cache, git sync, pipeline
  retrieval/    hybrid retriever + reranker
  generation/   Gemini answer generator
  mcp/          MCP server
evals/          golden dataset and evaluation scripts
tests/          backend tests
frontend/       Next.js web console
```
