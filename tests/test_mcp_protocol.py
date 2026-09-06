import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.config import settings


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_mcp_stateless_list_tools(client):
    headers = {
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/list",
        "Content-Type": "application/json",
        "X-API-Key": settings.api_key,
    }
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": {
                    "name": "test-runner",
                    "version": "1.0.0",
                },
            }
        },
    }
    response = client.post("/mcp/", json=body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    result = data["result"]
    assert "tools" in result
    tool_names = [t["name"] for t in result["tools"]]
    assert "search_campus_connect" in tool_names
    assert "get_commit_history" in tool_names
    assert "cacheScope" in result


def test_mcp_stateless_call_tool(client):
    headers = {
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "get_commit_history",
        "Content-Type": "application/json",
        "X-API-Key": settings.api_key,
    }
    body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_commit_history",
            "arguments": {"max_count": 2},
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": {
                    "name": "test-runner",
                    "version": "1.0.0",
                },
            },
        },
    }
    response = client.post("/mcp/", json=body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    result = data["result"]
    assert "content" in result
    text = result["content"][0]["text"]
    assert " - " in text

