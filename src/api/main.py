import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.tasks import IngestionStatus, get_status, trigger_ingestion
from src.config import settings
from src.generation.generator import AnswerGenerator, SourceCitation
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
    print("🚀 Initializing AEIA Retriever and Generator...")
    services["retriever"] = Retriever()
    services["generator"] = AnswerGenerator()
    yield
    services.clear()


app = FastAPI(
    title="AI Engineering Intelligence Assistant (AEIA)",
    description="Grounded code and architecture intelligence assistant for Campus Connect.",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceCitation]
    latency_ms: float


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


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints (no auth)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["General"])
async def root():
    return {
        "message": "AI Engineering Intelligence Assistant is running",
        "docs_url": "/docs",
        "health_url": "/health",
    }


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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    if not retriever or not generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline is initializing",
        )

    start_time = time.time()

    try:
        # 1. Retrieve top-K grounded chunks
        chunks = retriever.retrieve(body.question, top_k=body.top_k)

        # 2. Generate grounded answer
        result = generator.generate(body.question, chunks)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return AskResponse(
            question=body.question,
            answer=result.answer,
            sources=result.sources,
            latency_ms=latency_ms,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}",
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