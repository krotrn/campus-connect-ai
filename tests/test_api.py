import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


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


def test_ask_endpoint_valid_question(client):
    payload = {
        "question": "Where is authentication implemented?",
        "top_k": 3
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == payload["question"]
    assert len(data["answer"]) > 10
    assert len(data["sources"]) == 3
    assert data["latency_ms"] > 0


def test_ask_endpoint_invalid_input(client):
    # Test min_length validation on question
    payload = {"question": "ab", "top_k": 3}
    response = client.post("/ask", json=payload)
    assert response.status_code == 422

