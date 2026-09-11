import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.config import settings


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints (no auth needed)
# ─────────────────────────────────────────────────────────────────────────────
def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs_url" in data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["collection"] == "campus_connect"
    assert data["points_indexed"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Auth tests
# ─────────────────────────────────────────────────────────────────────────────
def test_ask_requires_api_key(client):
    """Requests without X-API-Key header should be rejected."""
    payload = {"question": "Where is auth implemented?", "top_k": 3}
    response = client.post("/ask", json=payload)
    assert response.status_code == 401  # missing credential, not a validation error


def test_ask_rejects_wrong_api_key(client):
    """Requests with an invalid API key should get 401."""
    payload = {"question": "Where is auth implemented?", "top_k": 3}
    response = client.post(
        "/ask", json=payload, headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_ask_endpoint_valid_question(client, auth_headers):
    """Valid request with correct API key should succeed."""
    payload = {
        "question": "Where is authentication implemented?",
        "top_k": 3,
    }
    response = client.post("/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == payload["question"]
    assert len(data["answer"]) > 10
    assert len(data["sources"]) == 3
    assert data["latency_ms"] > 0


def test_ask_endpoint_invalid_input(client, auth_headers):
    """Validation errors should return 422."""
    payload = {"question": "ab", "top_k": 3}
    response = client.post("/ask", json=payload, headers=auth_headers)
    assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion status endpoint (public)
# ─────────────────────────────────────────────────────────────────────────────
def test_ingest_status(client):
    response = client.get("/ingest/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["idle", "running", "completed", "failed"]


def test_ingest_requires_api_key(client):
    """POST /ingest should require auth."""
    response = client.post("/ingest")
    assert response.status_code == 401  # missing credential, not a validation error


def test_ingest_rejects_wrong_key(client):
    response = client.post("/ingest", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401
