from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError

from src.api.main import app, services
from src.config import settings
from src.errors import (
    LLMQuotaExceededError,
    VectorDBUnavailableError,
)
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import RetrievedChunk, Retriever


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


def test_quota_exceeded_exception_handler(client, auth_headers):
    """When LLMQuotaExceededError is raised, API returns HTTP 429 with LLM_QUOTA_EXHAUSTED."""
    generator = services.get("generator")
    if not generator:
        generator = AnswerGenerator()
        services["generator"] = generator

    with patch.object(
        generator,
        "generate",
        side_effect=LLMQuotaExceededError("Gemini quota exhausted", retry_after=30),
    ):
        response = client.post(
            "/ask",
            json={"question": "Where is auth handled?", "top_k": 2},
            headers=auth_headers,
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "LLM_QUOTA_EXHAUSTED"
        assert "quota" in data["message"].lower()
        assert response.headers.get("Retry-After") == "30"


def test_vector_db_unavailable_exception_handler(client, auth_headers):
    """When VectorDBUnavailableError is raised, API returns HTTP 503."""
    retriever = services.get("retriever")
    if not retriever:
        retriever = Retriever()
        services["retriever"] = retriever

    with patch.object(
        retriever,
        "retrieve",
        side_effect=VectorDBUnavailableError("Qdrant connection lost"),
    ):
        response = client.post(
            "/ask",
            json={"question": "Where is auth handled?", "top_k": 2},
            headers=auth_headers,
        )
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "VECTOR_DB_UNAVAILABLE"


def test_google_api_429_handler(client, auth_headers):
    """When an unhandled APIError 429 bubbles up, google_api_error_handler returns 429."""
    generator = services.get("generator")
    api_err = APIError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}})

    with patch.object(generator, "generate", side_effect=api_err):
        response = client.post(
            "/ask",
            json={"question": "Where is auth handled?", "top_k": 2},
            headers=auth_headers,
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "LLM_QUOTA_EXHAUSTED"


def test_google_api_503_handler(client, auth_headers):
    """When an unhandled APIError 503 bubbles up, google_api_error_handler returns 503."""
    generator = services.get("generator")
    api_err = APIError(503, {"error": {"message": "Backend service unavailable"}})

    with patch.object(generator, "generate", side_effect=api_err):
        response = client.post(
            "/ask",
            json={"question": "Where is auth handled?", "top_k": 2},
            headers=auth_headers,
        )
        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "LLM_SERVICE_UNAVAILABLE"


def test_generator_graceful_degradation_on_quota():
    """AnswerGenerator degrades gracefully by returning context chunks when 429 occurs."""
    gen = AnswerGenerator()
    sample_chunks = [
        RetrievedChunk(
            content="export const authMiddleware = ...",
            file_path="src/middleware/auth.ts",
            start_line=1,
            end_line=10,
            file_type="typescript",
            score=0.95,
        )
    ]

    quota_err = APIError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}})
    with patch.object(gen.client.models, "generate_content", side_effect=quota_err):
        res = gen.generate("How does auth middleware work?", sample_chunks)
        assert "Quota Exceeded" in res.answer or "429" in res.answer
        assert len(res.sources) == 1
        assert res.sources[0].file_path == "src/middleware/auth.ts"
        assert res.sources[0].citation == "src/middleware/auth.ts#L1-L10"


def test_generator_raise_on_quota_option():
    """AnswerGenerator raises LLMQuotaExceededError when configured with raise_on_quota=True."""
    gen = AnswerGenerator(raise_on_quota=True)
    sample_chunks = [
        RetrievedChunk(
            content="sample",
            file_path="file.ts",
            start_line=1,
            end_line=2,
            file_type="typescript",
            score=0.9,
        )
    ]

    quota_err = APIError(429, {"error": {"message": "RESOURCE_EXHAUSTED"}})
    with patch.object(gen.client.models, "generate_content", side_effect=quota_err):
        with pytest.raises(LLMQuotaExceededError) as exc_info:
            gen.generate("Query", sample_chunks)
        assert exc_info.value.status_code == 429
        assert exc_info.value.error_code == "LLM_QUOTA_EXHAUSTED"


def test_retriever_dense_vector_db_error():
    """Retriever raises VectorDBUnavailableError if Qdrant query fails."""
    retriever = Retriever()
    with patch.object(
        retriever.client, "query_points", side_effect=Exception("Connection refused")
    ):
        with pytest.raises(VectorDBUnavailableError) as exc_info:
            retriever._retrieve_dense("test query", top_k=3)
        assert "Connection refused" in exc_info.value.message

