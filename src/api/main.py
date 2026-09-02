import time
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.config import settings
from src.generation.generator import AnswerGenerator, SourceCitation
from src.retrieval.retriever import Retriever

# Singleton instances initialized on startup
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
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/ask", response_model=AskResponse, tags=["RAG"])
async def ask_question(request: AskRequest):
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
        chunks = retriever.retrieve(request.question, top_k=request.top_k)

        # 2. Generate grounded answer
        result = generator.generate(request.question, chunks)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return AskResponse(
            question=request.question,
            answer=result.answer,
            sources=result.sources,
            latency_ms=latency_ms,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}",
        )