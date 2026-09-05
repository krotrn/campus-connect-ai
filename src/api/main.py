import time
from contextlib import asynccontextmanager
from typing import List, Optional

from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.agent import create_agent_graph
from src.agent.memory import memory_manager, rewrite_query_with_history
from src.api.tasks import IngestionStatus, get_status, trigger_ingestion
from src.api.webhook import handle_github_webhook
from src.config import settings
from src.errors import (
    AEIAError,
    CorpusUnavailableError,
    LLMQuotaExceededError,
    LLMServiceUnavailableError,
    VectorDBUnavailableError,
)
from src.generation.generator import AnswerGenerator, SourceCitation
from src.mcp import get_streamable_http_app, mcp_server
from src.observability import flush as langfuse_flush, init_langfuse, traced_ask
from src.retrieval.retriever import Retriever

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
    print("🚀 Initializing AEIA Retriever, Generator, Agent, and MCP Server...")
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


# Mount Model Context Protocol (MCP) Streamable HTTP endpoint (2026-07-28 spec)
app.mount("/mcp", get_streamable_http_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Auth dependency
# ─────────────────────────────────────────────────────────────────────────────
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate the X-API-Key header against the configured key."""
    if x_api_key != settings.api_key:
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
        description="Route query through LangGraph state machine with non-RAG tools",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to maintain multi-turn conversational history",
    )


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceCitation]
    latency_ms: float
    session_id: Optional[str] = None
    rewritten_question: Optional[str] = None


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
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to maintain multi-turn conversational history",
    )


class AgentAskResponse(BaseModel):
    question: str
    route: str
    route_reasoning: str
    tool_output: Optional[str] = None
    answer: str
    sources: List[dict]
    steps_taken: List[str]
    latency_ms: float
    session_id: Optional[str] = None
    rewritten_question: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    collection: str
    points_indexed: int
    qdrant_url: str


class IngestionResponse(BaseModel):
    status: str
    message: str
    chunks_ingested: int = 0
    files_processed: int = 0
    error: Optional[str] = None


STATIC_DIR = Path(__file__).parent / "static"
STATIC_INDEX = STATIC_DIR / "index.html"


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints (no auth)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["General"])
async def root(request: Request):
    """API root. Redirects browsers to /ui while returning JSON to API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/ui", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return {
        "message": "AI Engineering Intelligence Assistant is running",
        "docs_url": "/docs",
        "health_url": "/health",
        "ui_url": "/ui",
    }


@app.get("/ui", tags=["UI"], response_class=FileResponse)
async def ui_playground():
    """Serve the interactive Web UI playground."""
    if not STATIC_INDEX.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UI playground file not found",
        )
    return FileResponse(STATIC_INDEX)


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    retriever: Optional[Retriever] = services.get("retriever")
    if not retriever:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Services not initialized",
        )

    try:
        collection_info = retriever.client.get_collection(settings.collection_name)
        return HealthResponse(
            status="healthy",
            collection=settings.collection_name,
            points_indexed=collection_info.points_count or 0,
            qdrant_url=settings.qdrant_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Qdrant connection error: {str(e)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Protected endpoints (auth + rate limit)
# ─────────────────────────────────────────────────────────────────────────────
@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["RAG"],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.rate_limit)
async def ask_question(request: Request, body: AskRequest):
    retriever: Optional[Retriever] = services.get("retriever")
    generator: Optional[AnswerGenerator] = services.get("generator")
    agent = services.get("agent")

    if not retriever or not generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is initializing",
        )

    start_time = time.time()
    session_id, session_mem = memory_manager.get_or_create(body.session_id)
    history = session_mem.get_history()

    # Coreference resolution / search query expansion
    client = generator.client if generator else None
    search_query = rewrite_query_with_history(body.question, history, client=client)

    try:
        if body.use_agent and agent:
            final_state = agent.invoke({
                "question": search_query,
                "top_k": body.top_k,
                "steps_taken": ["received_query"],
            })
            citations = [
                SourceCitation(
                    file_path=s.get("file_path", "unknown"),
                    start_line=s.get("start_line", 1),
                    end_line=s.get("end_line", 1),
                    citation=s.get("citation", "agent-source"),
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
            )

        result = traced_ask(search_query, body.top_k, retriever, generator, history=history)
        session_mem.add_turn(body.question, result["answer"])

        return AskResponse(
            question=body.question,
            answer=result["answer"],
            sources=result["sources"],
            latency_ms=result["latency_ms"],
            session_id=session_id,
            rewritten_question=search_query if search_query != body.question else None,
        )
    except (AEIAError, APIError, HTTPException):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}",
        )


@app.post(
    "/agent/ask",
    response_model=AgentAskResponse,
    tags=["Agent"],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit(settings.rate_limit)
async def agent_ask(request: Request, body: AgentAskRequest):
    agent = services.get("agent")
    generator: Optional[AnswerGenerator] = services.get("generator")
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent state machine is initializing",
        )

    start_time = time.time()
    session_id, session_mem = memory_manager.get_or_create(body.session_id)
    history = session_mem.get_history()

    # Coreference resolution / search query expansion
    client = generator.client if generator else None
    search_query = rewrite_query_with_history(body.question, history, client=client)

    try:
        final_state = agent.invoke({
            "question": search_query,
            "top_k": body.top_k,
            "steps_taken": ["received_query"],
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