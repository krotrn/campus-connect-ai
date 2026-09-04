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


def test_agent_ask_requires_auth(client):
    response = client.post("/agent/ask", json={"question": "What changed in commit 6e19f61?"})
    assert response.status_code == 422  # Missing X-API-Key


def test_agent_ask_rejects_wrong_key(client):
    response = client.post(
        "/agent/ask",
        json={"question": "What changed in commit 6e19f61?"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_agent_ask_git_commit_route(client, auth_headers):
    payload = {"question": "What files changed in commit 6e19f61?", "top_k": 3}
    response = client.post("/agent/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "git_commit"
    assert data["tool_output"] is not None
    assert "6e19f61" in data["tool_output"]
    assert len(data["steps_taken"]) >= 2
    assert data["latency_ms"] > 0


def test_agent_ask_git_history_route(client, auth_headers):
    payload = {"question": "Show latest commits and git log", "top_k": 3}
    response = client.post("/agent/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "git_history"
    assert data["tool_output"] is not None
    assert len(data["tool_output"]) > 10


def test_agent_ask_file_dependents_route(client, auth_headers):
    payload = {"question": "Which files depend on redis?", "top_k": 3}
    response = client.post("/agent/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "file_dependents"
    assert data["tool_output"] is not None


def test_agent_ask_direct_rag_route(client, auth_headers):
    payload = {"question": "Where is authentication implemented?", "top_k": 3}
    response = client.post("/agent/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "direct_rag"
    assert len(data["answer"]) > 10
    assert len(data["sources"]) > 0


def test_ask_endpoint_with_use_agent_flag(client, auth_headers):
    payload = {
        "question": "What files changed in commit 6e19f61?",
        "top_k": 3,
        "use_agent": True,
    }
    response = client.post("/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "6e19f61" in data["answer"]
    assert len(data["sources"]) > 0

