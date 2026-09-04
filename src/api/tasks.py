import asyncio
from enum import Enum
from typing import Optional


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


async def trigger_ingestion() -> bool:
    """
    Launch ingestion in a background thread.
    Returns False if already running.
    """
    if _state["status"] == IngestionStatus.RUNNING:
        return False

    _state["status"] = IngestionStatus.RUNNING
    _state["error"] = None

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(_run_in_background(loop))
    return True


async def _run_in_background(loop: asyncio.AbstractEventLoop):
    try:
        result = await loop.run_in_executor(None, _sync_ingest)
        _state["status"] = IngestionStatus.COMPLETED
        _state["chunks_ingested"] = result.get("chunks", 0)
        _state["files_processed"] = result.get("files", 0)
    except Exception as e:
        _state["status"] = IngestionStatus.FAILED
        _state["error"] = str(e)


def _sync_ingest() -> dict:
    """Run the full ingestion pipeline synchronously (called in a thread)."""
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    pipeline.run(recreate=True)

    # Extract final counts from the Qdrant collection
    from src.config import settings

    info = pipeline.client.get_collection(settings.collection_name)
    return {
        "chunks": info.points_count or 0,
        "files": 0,  # pipeline doesn't return this currently
    }

