import json
import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from google import genai
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse as StarletteJSONResponse

from src.agent import create_agent_graph
from src.agent.memory import memory_manager, rewrite_query_with_history
from src.agent.router import route_query
from src.api.tasks import IngestionStatus, get_status, trigger_ingestion
from src.api.webhook import handle_github_webhook
from src.config import settings
from src.errors import (
    AEIAError,
    LLMQuotaExceededError,
)
from src.generation.generator import AnswerGenerator, SourceCitation
from src.logging_config import configure_logging
from src.mcp import get_streamable_http_app, mcp_server
from src.observability import flush as langfuse_flush
from src.observability import init_langfuse, traced_ask
from src.retrieval.retriever import Retriever

configure_logging()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ─────────────────────────────────────────────────────────────────────────────
# Singleton services
# ─────────────────────────────────────────────────────────────────────────────
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AEIA Retriever, Generator, Agent, and MCP Server...")
    retriever = Retriever()
    generator = AnswerGenerator()
    services["retriever"] = retriever
    services["generator"] = generator
    services["agent"] = create_agent_graph(retriever, generator)
    init_langfuse()
    try:
        async with mcp_server.session_manager.run():
            yield  # Application is running and serving requests
    finally:
        # Runs only on server shutdown
        mcp_server.session_manager._has_started = False
        langfuse_flush()
        services.clear()


app = FastAPI(
    title="AI Engineering Intelligence Assistant (AEIA)",
    description="Grounded code and architecture intelligence assistant for Campus Connect.",
    version="0.4.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AEIAError)
async def aeia_error_handler(request: Request, exc: AEIAError):
    headers = {}
    if isinstance(exc, LLMQuotaExceededError) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "detail": exc.message,
        },
        headers=headers if headers else None,
    )


@app.exception_handler(APIError)
async def google_api_error_handler(request: Request, exc: APIError):
    status_code = getattr(exc, "code", 500) or 500
    message = getattr(exc, "message", str(exc))

    if status_code == 429 or "RESOURCE_EXHAUSTED" in message:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "LLM_QUOTA_EXHAUSTED",
                "message": "Upstream Gemini LLM quota exhausted. Please try again later.",
                "detail": message,
            },
        )
    elif status_code in (502, 503, 504):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "LLM_SERVICE_UNAVAILABLE",
                "message": "Upstream Gemini LLM service is temporarily unavailable.",
                "detail": message,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "LLM_GATEWAY_ERROR",
                "message": f"Upstream Gemini LLM returned error code {status_code}.",
                "detail": message,
            },
        )


def _api_key_matches(candidate: str | None) -> bool:
    """Constant-time API key comparison to avoid leaking the key by timing."""
    return bool(candidate) and secrets.compare_digest(candidate, settings.api_key)


# Mount Model Context Protocol (MCP) Streamable HTTP endpoint (2026-07-28 spec)
# Mount MCP with API key authentication middleware
_mcp_app = get_streamable_http_app()
_original_mcp_app_call = _mcp_app.__call__


async def _authenticated_mcp(scope, receive, send):
    """ASGI middleware that enforces X-API-Key on the MCP mount."""
    if scope["type"] == "http":
        headers = dict((k.decode(), v.decode()) for k, v in scope.get("headers", []))
        if not _api_key_matches(headers.get("x-api-key")):
            response = StarletteJSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid or missing API key for MCP endpoint."},
            )
            await response(scope, receive, send)
            return
    await _original_mcp_app_call(scope, receive, send)


app.mount("/mcp", _authenticated_mcp)

# CORS is restricted to the configured console origins. A wildcard origin
# combined with allow_credentials is rejected by browsers, and this API is
# meant to be reached through the console's server-side proxy anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Gemini-API-Key", "Accept"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Auth dependency
# ─────────────────────────────────────────────────────────────────────────────
def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    """Validate the X-API-Key header against the configured key."""
    if not _api_key_matches(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Engineering question about the codebase",
        examples=["Where is user authentication implemented?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of context chunks to retrieve",
    )
    use_agent: bool = Field(
        default=False,
        description=(
            "Force the LangGraph agent even for queries the router sends to direct RAG. "
            "Non-RAG routes (git history, commit diffs, dependencies) always use the agent."
        ),
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to maintain multi-turn conversational history",
    )
    stream: bool = Field(
        default=False,
        description="Stream response tokens via Server-Sent Events (SSE)",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Optional client-provided Gemini API key to override server quota or defaults",
    )


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceCitation]
    latency_ms: float
    session_id: str | None = None
    rewritten_question: str | None = None
    route: str | None = None
    route_reasoning: str | None = None
    model: str | None = None


class AgentAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Engineering question about the codebase",
        examples=["Which files changed in commit 6e19f61?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of context chunks if routed to RAG",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to maintain multi-turn conversational history",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Optional client-provided Gemini API key to override server quota or defaults",
    )


class AgentAskResponse(BaseModel):
    question: str
    route: str
    route_reasoning: str
    tool_output: str | None = None
    answer: str
    sources: list[dict]
    steps_taken: list[str]
    latency_ms: float
    session_id: str | None = None
    rewritten_question: str | None = None


class HealthResponse(BaseModel):
    status: str
    collection: str
    points_indexed: int
    indexed_points: int | None = None
    qdrant_url: str


class IngestionResponse(BaseModel):
    status: str
    message: str
    chunks_ingested: int = 0
    files_processed: int = 0
    error: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints (no auth)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["General"])
async def root():
    """API root. Returns JSON metadata to API clients."""
    return {
        "message": "AI Engineering Intelligence Assistant is running",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health_check():
    retriever: Retriever | None = services.get("retriever")
    if not retriever:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Services not initialized",
        )

    try:
        collection_info = retriever.client.get_collection(settings.collection_name)
        points = collection_info.points_count or 0
        return HealthResponse(
            status="healthy",
            collection=settings.collection_name,
            points_indexed=points,
            indexed_points=points,
            qdrant_url=settings.qdrant_url,
        )
    except Exception as e:
        logger.warning("Health check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Qdrant connection error: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Shared request helpers
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_gemini_key(request: Request, body_key: str | None) -> str | None:
    """Client-supplied Gemini key from the body or the X-Gemini-API-Key header."""
    return (
        (body_key or "").strip()
        or request.headers.get("x-gemini-api-key", "").strip()
        or None
    )


def _build_rewriter_client(
    gemini_api_key: str | None,
    generator: AnswerGenerator | None,
) -> genai.Client | None:
    if gemini_api_key:
        return genai.Client(api_key=gemini_api_key)
    return generator.client if generator else None


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_ask_response(
    body: AskRequest,
    search_query: str,
    session_id: str,
    session_mem: Any,
    retriever: Retriever,
    generator: AnswerGenerator,
    route: str,
    reasoning: str,
    target: str | None,
    agent: Any | None = None,
    gemini_api_key: str | None = None,
):
    start_time = time.time()
    use_agent = agent is not None and (route != "direct_rag" or body.use_agent)

    def event_generator():
        try:
            if use_agent:
                final_state = agent.invoke({
                    "question": search_query,
                    "top_k": body.top_k,
                    "route": route,
                    "route_reasoning": reasoning,
                    "target": target,
                    "steps_taken": ["received_query"],
                    "gemini_api_key": gemini_api_key,
                })
                latency_ms = round((time.time() - start_time) * 1000, 2)
                answer_text = final_state.get("answer", "")
                sources = final_state.get("sources", [])

                yield _sse({
                    "type": "sources",
                    "sources": sources,
                    "session_id": session_id,
                    "rewritten_question": search_query if search_query != body.question else None,
                    "route": route,
                    "route_reasoning": reasoning,
                })

                for line in answer_text.splitlines(keepends=True):
                    yield _sse({"type": "token", "text": line})

                session_mem.add_turn(body.question, answer_text)
                yield _sse({
                    "type": "done",
                    "latency_ms": latency_ms,
                    "session_id": session_id,
                    "route": route,
                    "route_reasoning": reasoning,
                    "model": settings.gemini_model if gemini_api_key or settings.has_gemini_key else None,
                })
            else:
                chunks = retriever.retrieve(search_query, top_k=body.top_k)
                full_answer = []
                for event in generator.generate_stream(
                    search_query,
                    chunks,
                    history=session_mem.get_history(),
                    api_key=gemini_api_key,
                ):
                    if event["type"] == "sources":
                        yield _sse({
                            "type": "sources",
                            "sources": event["sources"],
                            "session_id": session_id,
                            "rewritten_question": search_query if search_query != body.question else None,
                            "route": "direct_rag",
                            "route_reasoning": reasoning,
                        })
                    elif event["type"] == "token":
                        full_answer.append(event["text"])
                        yield _sse({"type": "token", "text": event["text"]})
                    elif event["type"] == "done":
                        latency_ms = round((time.time() - start_time) * 1000, 2)
                        session_mem.add_turn(body.question, "".join(full_answer))
                        yield _sse({
                            "type": "done",
                            "latency_ms": latency_ms,
                            "session_id": session_id,
                            "route": "direct_rag",
                            "route_reasoning": reasoning,
                            "model": event.get("model"),
                        })
        except AEIAError as e:
            logger.error("Stream failed: %s", e, exc_info=True)
            yield _sse({"type": "error", "error": e.message, "code": e.error_code})
        except Exception:
            # Never leak raw exception text (which can carry internal hosts and
            # credentials) to the browser; the detail goes to the server log.
            logger.exception("Unhandled error while streaming answer")
            yield _sse({
                "type": "error",
                "error": "An internal error occurred while generating the answer.",
                "code": "INTERNAL_ERROR",
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _ask_impl(request: Request, body: AskRequest):
    """Shared implementation behind /ask and /ask/stream.

    Kept separate from the rate-limited route functions so that /ask/stream
    delegating to it does not consume the caller's rate budget twice.
    """
    retriever: Retriever | None = services.get("retriever")
    generator: AnswerGenerator | None = services.get("generator")
    agent = services.get("agent")

    if not retriever or not generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is initializing",
        )

    start_time = time.time()
    session_id, session_mem = memory_manager.get_or_create(body.session_id)
    history = session_mem.get_history()

    effective_gemini_key = _resolve_gemini_key(request, body.gemini_api_key)

    # Coreference resolution / search query expansion
    search_query = rewrite_query_with_history(
        body.question,
        history,
        client=_build_rewriter_client(effective_gemini_key, generator),
    )

    # Route once, then reuse the decision for both the streaming branch and the
    # agent graph so ambiguous queries cost a single classification call.
    route, reasoning, target = route_query(search_query, api_key=effective_gemini_key)

    # If client requested Server-Sent Events (SSE) streaming
    if body.stream or "text/event-stream" in request.headers.get("accept", ""):
        return _stream_ask_response(
            body=body,
            search_query=search_query,
            session_id=session_id,
            session_mem=session_mem,
            retriever=retriever,
            generator=generator,
            route=route,
            reasoning=reasoning,
            target=target,
            agent=agent,
            gemini_api_key=effective_gemini_key,
        )

    try:
        if agent and (route != "direct_rag" or body.use_agent):
            final_state = agent.invoke({
                "question": search_query,
                "top_k": body.top_k,
                "route": route,
                "route_reasoning": reasoning,
                "target": target,
                "steps_taken": ["received_query"],
                "gemini_api_key": effective_gemini_key,
            })
            citations = [
                SourceCitation(
                    file_path=s.get("file_path", "unknown"),
                    start_line=s.get("start_line", 1),
                    end_line=s.get("end_line", 1),
                    citation=s.get("citation", "agent-source"),
                    content=s.get("content"),
                    score=s.get("score"),
                )
                for s in final_state.get("sources", [])
            ]
            latency_ms = round((time.time() - start_time) * 1000, 2)
            answer_text = final_state.get("answer", "")
            session_mem.add_turn(body.question, answer_text)
            return AskResponse(
                question=body.question,
                answer=answer_text,
                sources=citations,
                latency_ms=latency_ms,
                session_id=session_id,
                rewritten_question=search_query if search_query != body.question else None,
                route=final_state.get("route", route),
                route_reasoning=final_state.get("route_reasoning", reasoning),
            )

        result = traced_ask(
            search_query,
            body.top_k,
            retriever,
            generator,
            history=history,
            api_key=effective_gemini_key,
        )
        session_mem.add_turn(body.question, result["answer"])

        return AskResponse(
            question=body.question,
            answer=result["answer"],
            sources=result["sources"],
            latency_ms=result["latency_ms"],
            session_id=session_id,
            rewritten_question=search_query if search_query != body.question else None,
            route="direct_rag",
            route_reasoning=reasoning or "Direct RAG invocation",
        )
    except (AEIAError, APIError, HTTPException):
        raise
    except Exception as e:
        logger.exception("Error processing question")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Protected endpoints (auth + rate limit)
#
# These are defined with `def`, not `async def`, on purpose: the RAG pipeline is
# synchronous and slow (embedding, Qdrant I/O, multi-second LLM calls). FastAPI
# runs sync handlers in a worker threadpool, so one in-flight question no longer
# blocks the event loop — and therefore every other request — for its duration.
# ─────────────────────────────────────────────────────────────────────────────
@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["RAG"],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.rate_limit)
def ask_question(request: Request, body: AskRequest):
    return _ask_impl(request, body)


@app.post(
    "/ask/stream",
    tags=["RAG"],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.rate_limit)
def ask_question_stream(request: Request, body: AskRequest):
    """Dedicated Server-Sent Events (SSE) streaming endpoint."""
    body.stream = True
    return _ask_impl(request, body)


@app.post(
    "/agent/ask",
    response_model=AgentAskResponse,
    tags=["Agent"],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.rate_limit)
def agent_ask(request: Request, body: AgentAskRequest):
    agent = services.get("agent")
    generator: AnswerGenerator | None = services.get("generator")
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent state machine is initializing",
        )

    start_time = time.time()
    session_id, session_mem = memory_manager.get_or_create(body.session_id)
    history = session_mem.get_history()

    effective_gemini_key = _resolve_gemini_key(request, body.gemini_api_key)

    # Coreference resolution / search query expansion
    search_query = rewrite_query_with_history(
        body.question,
        history,
        client=_build_rewriter_client(effective_gemini_key, generator),
    )

    try:
        final_state = agent.invoke({
            "question": search_query,
            "top_k": body.top_k,
            "steps_taken": ["received_query"],
            "gemini_api_key": effective_gemini_key,
        })
        latency_ms = round((time.time() - start_time) * 1000, 2)
        answer_text = final_state.get("answer", "")
        session_mem.add_turn(body.question, answer_text)
        return AgentAskResponse(
            question=body.question,
            route=final_state.get("route", "direct_rag"),
            route_reasoning=final_state.get("route_reasoning", ""),
            tool_output=final_state.get("tool_output"),
            answer=answer_text,
            sources=final_state.get("sources", []),
            steps_taken=final_state.get("steps_taken", []),
            latency_ms=latency_ms,
            session_id=session_id,
            rewritten_question=search_query if search_query != body.question else None,
        )
    except (AEIAError, APIError, HTTPException):
        raise
    except Exception as e:
        logger.exception("Error executing agent workflow")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent workflow: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion endpoints (auth-protected, no rate limit)
# ─────────────────────────────────────────────────────────────────────────────
@app.post(
    "/ingest",
    response_model=IngestionResponse,
    tags=["Ingestion"],
    dependencies=[Depends(verify_api_key)],
)
async def start_ingestion():
    """Trigger background re-ingestion of the corpus."""
    started = await trigger_ingestion()
    if not started:
        return IngestionResponse(
            status=IngestionStatus.RUNNING,
            message="Ingestion is already running",
        )
    return IngestionResponse(
        status=IngestionStatus.RUNNING,
        message="Ingestion started in background",
    )


@app.get(
    "/ingest/status",
    response_model=IngestionResponse,
    tags=["Ingestion"],
)
async def ingestion_status():
    """Check the status of the last ingestion run."""
    state = get_status()
    return IngestionResponse(
        status=state["status"],
        message=f"Ingestion is {state['status']}",
        chunks_ingested=state.get("chunks_ingested", 0),
        files_processed=state.get("files_processed", 0),
        error=state.get("error"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Webhook (HMAC-SHA256 authenticated, no API key)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/webhook/github", tags=["Webhook"])
async def github_webhook(request: Request):
    """Receive GitHub push events, pull corpus, and trigger incremental ingestion."""
    return await handle_github_webhook(request)
