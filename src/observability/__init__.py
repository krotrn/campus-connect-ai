"""
Langfuse observability wrapper.

Provides traced versions of retrieval and generation that automatically
capture latency, scores, token usage, and metadata to Langfuse.

If Langfuse keys are not configured, all tracing is silently skipped
and the raw functions execute normally.
"""

import time
from typing import List, Optional

from langfuse import Langfuse

from src.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Client init (None if not configured → tracing becomes no-op)
# ─────────────────────────────────────────────────────────────────────────────
_langfuse: Optional[Langfuse] = None


def init_langfuse() -> Optional[Langfuse]:
    """Initialize Langfuse client if keys are configured."""
    global _langfuse
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        print("📊 Langfuse tracing enabled")
        return _langfuse
    else:
        print("📊 Langfuse tracing disabled (no keys configured)")
        return None


def get_langfuse() -> Optional[Langfuse]:
    return _langfuse


def flush():
    """Flush pending traces (call on shutdown)."""
    if _langfuse:
        _langfuse.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Traced RAG pipeline
# ─────────────────────────────────────────────────────────────────────────────
def traced_ask(question: str, top_k: int, retriever, generator, history=None) -> dict:
    """
    Execute the full RAG pipeline with Langfuse tracing.

    If Langfuse is not configured, runs the pipeline without tracing.
    Returns dict with: answer, sources, latency_ms, trace_id
    """
    if not _langfuse:
        return _untraced_ask(question, top_k, retriever, generator, history=history)

    return _traced_ask_impl(question, top_k, retriever, generator, history=history)


def _untraced_ask(question: str, top_k: int, retriever, generator, history=None) -> dict:
    """Plain execution without any tracing overhead."""
    start = time.time()
    chunks = retriever.retrieve(question, top_k=top_k)
    result = generator.generate(question, chunks, history=history)
    latency_ms = round((time.time() - start) * 1000, 2)

    return {
        "answer": result.answer,
        "sources": result.sources,
        "latency_ms": latency_ms,
        "trace_id": None,
    }


def _traced_ask_impl(question: str, top_k: int, retriever, generator, history=None) -> dict:
    """Full Langfuse-traced execution."""
    trace = _langfuse.trace(
        name="rag-ask",
        input={"question": question, "top_k": top_k},
        metadata={"version": "0.2.0"},
    )

    # ── Retrieval span ────────────────────────────────────────────────────
    retrieval_span = trace.span(
        name="retrieval",
        input={"query": question, "top_k": top_k},
    )

    retrieval_start = time.time()
    chunks = retriever.retrieve(question, top_k=top_k)
    retrieval_ms = round((time.time() - retrieval_start) * 1000, 2)

    retrieval_span.end(
        output={
            "num_chunks": len(chunks),
            "top_files": [c.file_path for c in chunks[:5]],
            "top_scores": [round(c.score, 4) for c in chunks[:5]],
        },
        metadata={"latency_ms": retrieval_ms},
    )

    # ── Generation span ───────────────────────────────────────────────────
    generation_span = trace.generation(
        name="gemini-generate",
        model=generator.model_name,
        input={
            "question": question,
            "context_chunks": len(chunks),
        },
    )

    generation_start = time.time()
    result = generator.generate(question, chunks, history=history)
    generation_ms = round((time.time() - generation_start) * 1000, 2)

    generation_span.end(
        output=result.answer[:500],  # trim for Langfuse display
        metadata={
            "latency_ms": generation_ms,
            "answer_length": len(result.answer),
        },
    )

    # ── Finalize trace ────────────────────────────────────────────────────
    total_ms = round(retrieval_ms + generation_ms, 2)

    trace.update(
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
        "trace_id": trace.id,
    }
