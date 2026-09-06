# ADR 0031: Modernized Python 3.12+ Type Annotation Standard & Ingestion Progress Instrumentation

## Status

Accepted

## Date

2026-09-07

## Context

AEIA specifies Python `>=3.12` in `pyproject.toml`. However, as the codebase evolved through multiple feature milestones (V1 through V7), modules accumulated inconsistent type annotations:
- Some modules used legacy `typing` imports (`typing.List`, `typing.Dict`, `typing.Optional`, `typing.Union`, `typing.Tuple` from PEP 484).
- Other modules utilized modern Python 3.10+ native container generics (`list[str]`, `dict[str, Any]`) and union syntax (`str | None` from PEP 585 and PEP 604).

Additionally, the corpus ingestion pipeline (`src/ingestion/pipeline.py`), which indexes over 800 files and ~94,300 lines of code across Campus Connect, previously relied on occasional standard `print` statements. During initial vector embedding generation and Qdrant batch upserts, developers had no visual indicator of batch completion speed, percentage progress, or estimated time to completion (ETA).

Finally, deploying AEIA alongside managed Qdrant Cloud clusters required API key authentication, which was unexposed in server configuration.

## Decision

We performed a comprehensive type standardization across the codebase, added `tqdm` progress tracking to the ingestion pipeline, and introduced Qdrant API key support.

### 1. Python 3.12+ Native Type Annotation Standard
We standardized all type hints across `src/agent/`, `src/api/`, `src/ingestion/`, `src/retrieval/`, `src/generation/`, and `tests/`:
- Replaced `List[T]` with native `list[T]`.
- Replaced `Dict[K, V]` with native `dict[K, V]`.
- Replaced `Optional[T]` and `Union[A, B]` with pipe union syntax `T | None` and `A | B`.
- Replaced `Tuple[...]` with native `tuple[...]`.
- Configured Ruff (`pyproject.toml`) with target version `py312` to enforce consistent type conventions.

### 2. Ingestion Progress Instrumentation (`tqdm`)
We added `tqdm>=4.66.0` to project dependencies and wrapped key ingestion stages in visual progress bars:
- **File Parsing & AST Chunking**: Displays real-time progress across candidate repository files.
- **Batch FastEmbed Generation**: Visualizes dense embedding vector generation (batch size 32) with tokens-per-second indicators.
- **Qdrant Batch Upsertion**: Tracks points successfully indexed into the `campus_connect` vector collection.

```text
Chunking Campus Connect files: 100%|██████████| 808/808 [00:04<00:00, 185.2file/s]
Generating BGE-small embeddings: 100%|██████████| 42/42 [00:18<00:00,  2.31it/s]
Upserting points to Qdrant: 100%|██████████| 42/42 [00:02<00:00, 16.42it/s]
```

### 3. Qdrant Cloud Authentication (`qdrant_api_key`)
We added `qdrant_api_key: str = ""` to `Settings` (`src/config.py`). When present, `Retriever` (`src/retrieval/retriever.py`) and `IngestionPipeline` (`src/ingestion/pipeline.py`) initialize `QdrantClient` with `api_key=settings.qdrant_api_key`, enabling out-of-the-box connectivity to managed Qdrant Cloud clusters without code modifications.

## Consequences

### Positive
- **Idiomatic Modern Python**: Eliminates redundant `typing` module imports and ensures clean, readable function signatures across all layers.
- **Predictable Ingestion Operations**: Developers running `python -m src.ingestion.pipeline` have clear visibility into processing stages, batch progress, and hardware embedding throughput.
- **Cloud Readiness**: Supports secure remote vector databases (Qdrant Cloud) with API key authorization for production cloud deployments.

### Trade-Offs
- Adds a small, lightweight runtime dependency (`tqdm`).

## Validation

- `uv run ruff check .` (verifies clean linting and formatting).
- `PYTHONPATH=. uv run python -m src.ingestion.pipeline` (verifies visual progress bars and successful indexing).
- `pytest tests/test_retriever.py` (verifies Qdrant client connection and retrieval).

