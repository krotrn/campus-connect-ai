import json
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


def test_stream_requires_auth(client):
    response = client.post("/ask/stream", json={"question": "Where is auth?"})
    assert response.status_code == 422  # Missing header


def test_stream_rejects_wrong_key(client):
    response = client.post(
        "/ask/stream",
        json={"question": "Where is auth?"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_stream_returns_sse_events(client, auth_headers):
    payload = {"question": "Where is user authentication implemented?", "top_k": 2}
    response = client.post("/ask/stream", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = []
    for line in response.text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if data_str:
                events.append(json.loads(data_str))

    assert len(events) >= 2  # At least sources and done
    event_types = [e.get("type") for e in events]
    assert "sources" in event_types
    assert "done" in event_types

    sources_event = next(e for e in events if e.get("type") == "sources")
    assert len(sources_event["sources"]) == 2
    assert "file_path" in sources_event["sources"][0]


def test_ask_with_stream_flag(client, auth_headers):
    payload = {"question": "Where is database schema defined?", "top_k": 2, "stream": True}
    response = client.post("/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

