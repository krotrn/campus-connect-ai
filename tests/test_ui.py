"""Tests for API root and UI endpoint retirement."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_ui_endpoint_retired(client):
    """GET /ui returns 404 since legacy static playground was removed in favor of Next.js frontend."""
    response = client.get("/ui")
    assert response.status_code == 404


def test_root_returns_json_for_all_clients(client):
    """GET / returns standard JSON info without redirecting."""
    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs_url" in data
    assert "health_url" in data


def test_root_json_for_api_clients(client):
    """GET / with application/json Accept header returns standard JSON info."""
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs_url" in data
    assert "health_url" in data


