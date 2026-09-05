import asyncio
from enum import Enum
from typing import List, Optional


class IngestionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# In-memory state — sufficient for single-process V3
_state = {
    "status": IngestionStatus.IDLE,
    "error": None,
    "chunks_ingested": 0,
    "files_processed": 0,
}


def get_status() -> dict:
    return dict(_state)


def _hot_reload_retriever():
    """Reload the in-memory BM25 index on the active Retriever singleton."""
    try:
        from src.api.main import services

        retriever = services.get("retriever")
        if retriever:
            retriever.reload_bm25()
    except Exception as e:
        print(f"⚠️ Could not reload in-memory BM25 index: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Full re-ingestion (existing)
# ─────────────────────────────────────────────────────────────────────────────


async def trigger_ingestion() -> bool:
    """
    Launch full ingestion in a background thread.
    Returns False if already running.
    """
    if _state["status"] == IngestionStatus.RUNNING:
        return False

    _state["status"] = IngestionStatus.RUNNING
    _state["error"] = None

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(_run_full_in_background(loop))
    return True


async def _run_full_in_background(loop: asyncio.AbstractEventLoop):
    try:
        result = await loop.run_in_executor(None, _sync_full_ingest)
        _state["status"] = IngestionStatus.COMPLETED
        _state["chunks_ingested"] = result.get("chunks", 0)
        _state["files_processed"] = result.get("files", 0)
    except Exception as e:
        _state["status"] = IngestionStatus.FAILED
        _state["error"] = str(e)


def _sync_full_ingest() -> dict:
    """Run the full ingestion pipeline synchronously (called in a thread)."""
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    result = pipeline.run(recreate=True)

    _hot_reload_retriever()

    from src.config import settings

    info = pipeline.client.get_collection(settings.collection_name)
    return {
        "chunks": info.points_count or 0,
        "files": result.get("files", 0) if isinstance(result, dict) else 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Incremental (delta-only) ingestion
# ─────────────────────────────────────────────────────────────────────────────


async def trigger_incremental_ingestion(changed_files: List[str]) -> bool:
    """
    Launch incremental ingestion for *changed_files* in a background thread.
    Returns False if already running.
    """
    if _state["status"] == IngestionStatus.RUNNING:
        return False

    _state["status"] = IngestionStatus.RUNNING
    _state["error"] = None

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(_run_incremental_in_background(loop, changed_files))
    return True


async def _run_incremental_in_background(
    loop: asyncio.AbstractEventLoop,
    changed_files: List[str],
):
    try:
        result = await loop.run_in_executor(None, _sync_incremental_ingest, changed_files)
        _state["status"] = IngestionStatus.COMPLETED
        _state["chunks_ingested"] = result.get("chunks", 0)
        _state["files_processed"] = result.get("files", 0)
    except Exception as e:
        _state["status"] = IngestionStatus.FAILED
        _state["error"] = str(e)


def _sync_incremental_ingest(changed_files: List[str]) -> dict:
    """Run incremental ingestion synchronously (called in a thread)."""
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    result = pipeline.run_incremental(changed_files)

    _hot_reload_retriever()

    return result
