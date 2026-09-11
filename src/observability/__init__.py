"""
Langfuse observability wrapper.

Provides traced versions of retrieval and generation that automatically
capture latency, scores, and metadata to Langfuse.

If Langfuse keys are not configured, all tracing is silently skipped
and the raw functions execute normally.  Tracing is *never* allowed to
fail a user request: if the Langfuse SDK raises for any reason, the
pipeline falls back to untraced execution.

Targets the Langfuse v3/v4 OpenTelemetry-based SDK, where traces are
modelled as nested observations (``start_as_current_observation``)
rather than the v2 ``client.trace()`` / ``trace.span()`` objects.
"""

import logging
import time

from langfuse import Langfuse

from src.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Client init (None if not configured → tracing becomes no-op)
# ─────────────────────────────────────────────────────────────────────────────
_langfuse: Langfuse | None = None


def init_langfuse() -> Langfuse | None:
    """Initialize Langfuse client if keys are configured."""
    global _langfuse
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        logger.info("Langfuse tracing disabled (no keys configured)")
        _langfuse = None
        return None

    try:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("Langfuse tracing enabled (host=%s)", settings.langfuse_host)
        return _langfuse
    except Exception as e:
        logger.warning("Langfuse initialization failed, continuing untraced: %s", e)
        _langfuse = None
        return None


def get_langfuse() -> Langfuse | None:
    return _langfuse


def flush():
    """Flush pending traces (call on shutdown)."""
    if _langfuse:
        try:
            _langfuse.flush()
        except Exception as e:
            logger.warning("Langfuse flush failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Traced RAG pipeline
# ─────────────────────────────────────────────────────────────────────────────
def traced_ask(question: str, top_k: int, retriever, generator, history=None, api_key: str | None = None) -> dict:
    """
    Execute the full RAG pipeline with Langfuse tracing.

    If Langfuse is not configured — or if the tracing SDK errors — the
    pipeline still runs to completion untraced.
    Returns dict with: answer, sources, latency_ms, trace_id
    """
    if not _langfuse:
        return _untraced_ask(question, top_k, retriever, generator, history=history, api_key=api_key)

    try:
        return _traced_ask_impl(question, top_k, retriever, generator, history=history, api_key=api_key)
    except Exception as e:
        # Tracing must never take down a request. Domain errors raised by the
        # pipeline itself propagate from _untraced_ask below instead.
        logger.warning("Langfuse tracing failed, retrying untraced: %s", e, exc_info=True)
        return _untraced_ask(question, top_k, retriever, generator, history=history, api_key=api_key)


def _untraced_ask(question: str, top_k: int, retriever, generator, history=None, api_key: str | None = None) -> dict:
    """Plain execution without any tracing overhead."""
    start = time.time()
    chunks = retriever.retrieve(question, top_k=top_k)
    result = generator.generate(question, chunks, history=history, api_key=api_key)
    latency_ms = round((time.time() - start) * 1000, 2)

    return {
        "answer": result.answer,
        "sources": result.sources,
        "latency_ms": latency_ms,
        "trace_id": None,
    }


def _traced_ask_impl(question: str, top_k: int, retriever, generator, history=None, api_key: str | None = None) -> dict:
    """Full Langfuse-traced execution using the v4 observation API."""
    with _langfuse.start_as_current_observation(
        name="rag-ask",
        as_type="chain",
        input={"question": question, "top_k": top_k},
        metadata={"version": settings_version()},
    ) as root:
        trace_id = _langfuse.get_current_trace_id()

        # ── Retrieval span ────────────────────────────────────────────────
        retrieval_start = time.time()
        with _langfuse.start_as_current_observation(
            name="retrieval",
            as_type="retriever",
            input={"query": question, "top_k": top_k},
        ) as retrieval_span:
            chunks = retriever.retrieve(question, top_k=top_k)
            retrieval_ms = round((time.time() - retrieval_start) * 1000, 2)
            retrieval_span.update(
                output={
                    "num_chunks": len(chunks),
                    "top_files": [c.file_path for c in chunks[:5]],
                    "top_scores": [round(c.score, 4) for c in chunks[:5]],
                },
                metadata={"latency_ms": retrieval_ms},
            )

        # ── Generation span ───────────────────────────────────────────────
        generation_start = time.time()
        with _langfuse.start_as_current_observation(
            name="gemini-generate",
            as_type="generation",
            model=generator.model_name,
            input={"question": question, "context_chunks": len(chunks)},
            model_parameters={"temperature": 0.1},
        ) as generation_span:
            result = generator.generate(question, chunks, history=history, api_key=api_key)
            generation_ms = round((time.time() - generation_start) * 1000, 2)
            generation_span.update(
                output=result.answer[:500],  # trim for Langfuse display
                metadata={
                    "latency_ms": generation_ms,
                    "answer_length": len(result.answer),
                },
            )

        total_ms = round(retrieval_ms + generation_ms, 2)
        root.update(
            output={
                "answer": result.answer[:200],
                "num_sources": len(result.sources),
            },
            metadata={
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "total_ms": total_ms,
            },
        )

    return {
        "answer": result.answer,
        "sources": result.sources,
        "latency_ms": total_ms,
        "trace_id": trace_id,
    }


def settings_version() -> str:
    """Application version reported on traces."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("aeia")
    except PackageNotFoundError:
        return "unknown"
