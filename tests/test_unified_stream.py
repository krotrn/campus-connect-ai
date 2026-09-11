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


def parse_sse_events(response_text: str):
    events = []
    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if data_str:
                events.append(json.loads(data_str))
    return events


def test_unified_stream_direct_rag_route(client, auth_headers):
    payload = {"question": "Where is user authentication implemented?", "top_k": 2}
    response = client.post("/ask/stream", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = parse_sse_events(response.text)
    assert len(events) >= 2
    sources_event = next(e for e in events if e.get("type") == "sources")
    assert sources_event.get("route") == "direct_rag"
    assert len(sources_event["sources"]) == 2

    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event.get("route") == "direct_rag"


def test_unified_stream_git_commit_route(client, auth_headers):
    payload = {"question": "What files changed in commit 6e19f61?", "top_k": 2}
    response = client.post("/ask/stream", json=payload, headers=auth_headers)
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    assert len(events) >= 2
    sources_event = next(e for e in events if e.get("type") == "sources")
    assert sources_event.get("route") == "git_commit"
    assert len(sources_event["sources"]) > 0

    tokens = "".join(e.get("text", "") for e in events if e.get("type") == "token")
    assert "6e19f61" in tokens

    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event.get("route") == "git_commit"


def test_unified_stream_file_dependents_route(client, auth_headers):
    payload = {"question": "Which files depend on redis?", "top_k": 2}
    response = client.post("/ask/stream", json=payload, headers=auth_headers)
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    assert len(events) >= 2
    sources_event = next(e for e in events if e.get("type") == "sources")
    assert sources_event.get("route") == "file_dependents"

    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event.get("route") == "file_dependents"

