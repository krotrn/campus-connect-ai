"""Tests for the interactive Web UI playground."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_ui_endpoint_returns_html(client):
    """GET /ui returns HTTP 200 and serves the interactive HTML playground."""
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AEIA — AI Engineering Intelligence Assistant" in response.text
    assert "queryInput" in response.text
    assert "codeModal" in response.text
    assert "statusBadge" in response.text


def test_root_browser_redirect(client):
    """GET / with text/html Accept header redirects browser clients to /ui."""
    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"}, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers.get("location") == "/ui"


def test_root_json_for_api_clients(client):
    """GET / with application/json Accept header returns standard JSON info."""
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data.get("ui_url") == "/ui"
    assert "docs_url" in data

