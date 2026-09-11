import asyncio
import logging
import threading
from enum import StrEnum

logger = logging.getLogger(__name__)


class IngestionStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# In-memory state — sufficient for single-process V3
_state_lock = threading.Lock()
_state = {
    "status": IngestionStatus.IDLE,
    "error": None,
    "chunks_ingested": 0,
    "files_processed": 0,
}


def _update_state(**kwargs):
    """Thread-safe state update."""
    with _state_lock:
        _state.update(kwargs)


def _claim_run() -> bool:
    """Atomically mark ingestion as RUNNING.

    Returns True if this caller won the claim, False if a run is already in
    flight. Checking the status and setting it must happen under one lock:
    otherwise two concurrent /ingest requests can both pass the check, and a
    full ingest recreates the collection.
    """
    with _state_lock:
        if _state["status"] == IngestionStatus.RUNNING:
            return False
        _state.update(status=IngestionStatus.RUNNING, error=None)
        return True


def get_status() -> dict:
    with _state_lock:
        return dict(_state)


def _hot_reload_retriever():
    """Reload the in-memory BM25 index on the active Retriever singleton."""
    try:
        from src.api.main import services

        retriever = services.get("retriever")
        if retriever:
            retriever.reload_bm25()
    except Exception as e:
        logger.warning("Could not reload in-memory BM25 index: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Full re-ingestion (existing)
# ─────────────────────────────────────────────────────────────────────────────


async def trigger_ingestion() -> bool:
    """
    Launch full ingestion in a background thread.
    Returns False if already running.
    """
    if not _claim_run():
        return False

    loop = asyncio.get_running_loop()
    loop.create_task(_run_full_in_background(loop))
    return True


async def _run_full_in_background(loop: asyncio.AbstractEventLoop):
    try:
        result = await loop.run_in_executor(None, _sync_full_ingest)
        _update_state(
            status=IngestionStatus.COMPLETED,
            chunks_ingested=result.get("chunks", 0),
            files_processed=result.get("files", 0),
        )
    except Exception as e:
        logger.exception("Full ingestion failed")
        _update_state(status=IngestionStatus.FAILED, error=str(e))


def _sync_full_ingest() -> dict:
    """Run the full ingestion pipeline synchronously (called in a thread)."""
    from src.ingestion.pipeline import IngestionPipeline

    # Non-destructive full sync: upsert everything, then prune stale points.
    # Using recreate=True here would blank the collection for the whole run.
    pipeline = IngestionPipeline()
    result = pipeline.run(recreate=False)

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


async def trigger_incremental_ingestion(changed_files: list[str]) -> bool:
    """
    Launch incremental ingestion for *changed_files* in a background thread.
    Returns False if already running.
    """
    if not _claim_run():
        return False

    loop = asyncio.get_running_loop()
    loop.create_task(_run_incremental_in_background(loop, changed_files))
    return True


async def _run_incremental_in_background(
    loop: asyncio.AbstractEventLoop,
    changed_files: list[str],
):
    try:
        result = await loop.run_in_executor(None, _sync_incremental_ingest, changed_files)
        _update_state(
            status=IngestionStatus.COMPLETED,
            chunks_ingested=result.get("chunks", 0),
            files_processed=result.get("files", 0),
        )
    except Exception as e:
        logger.exception("Incremental ingestion failed")
        _update_state(status=IngestionStatus.FAILED, error=str(e))


def _sync_incremental_ingest(changed_files: list[str]) -> dict:
    """Run incremental ingestion synchronously (called in a thread)."""
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    result = pipeline.run_incremental(changed_files)

    _hot_reload_retriever()

    return result
