"""Unit tests for multi-turn conversational session memory and coreference query rewriting."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.agent.memory import (
    ChatMessage,
    SessionMemory,
    SessionMemoryManager,
    rewrite_query_with_history,
)
from src.api.main import app
from src.config import settings


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_session_memory_add_and_sliding_window():
    """Session memory retains turns up to max_turns and evicts older turns."""
    mem = SessionMemory(session_id="sess_test", max_turns=3)

    # Add 4 turns (8 messages)
    for i in range(1, 5):
        mem.add_turn(f"User question {i}", f"Assistant answer {i}")

    history = mem.get_history()
    # Should retain exactly 3 turns (6 messages)
    assert len(history) == 6
    # Oldest turn 1 should be evicted; oldest remaining is turn 2
    assert history[0].content == "User question 2"
    assert history[-1].content == "Assistant answer 4"


def test_session_memory_manager():
    """Manager creates unique sessions, reuses IDs, and clears properly."""
    mgr = SessionMemoryManager(max_turns_per_session=2)

    # Auto-generate session ID
    sess_id_1, mem_1 = mgr.get_or_create(None)
    assert sess_id_1.startswith("sess_")

    # Reuse session ID
    sess_id_2, mem_2 = mgr.get_or_create(sess_id_1)
    assert sess_id_1 == sess_id_2
    assert mem_1 is mem_2

    mem_1.add_turn("Q", "A")
    assert len(mem_1.get_history()) == 2

    mgr.clear_session(sess_id_1)
    assert len(mem_1.get_history()) == 0


def test_rewrite_query_returns_original_when_empty_history():
    """If no history exists, query is returned immediately without LLM call."""
    rewritten = rewrite_query_with_history("Can you show me its unit test?", [])
    assert rewritten == "Can you show me its unit test?"


def test_rewrite_query_with_mock_llm():
    """Follow-up pronouns are rewritten into standalone search queries using history."""
    history = [
        ChatMessage(role="user", content="Where is user authentication implemented?"),
        ChatMessage(
            role="assistant",
            content="Authentication is implemented in src/auth.ts using Better Auth and prismaAdapter.",
        ),
    ]

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Where are the unit tests for Better Auth authentication in src/auth.ts?"
    mock_client.models.generate_content.return_value = mock_resp

    rewritten = rewrite_query_with_history(
        query="Can you show me its unit test?",
        history=history,
        client=mock_client,
    )

    assert "unit tests for Better Auth authentication" in rewritten
    assert mock_client.models.generate_content.called


def test_multi_turn_api_session_integration(client):
    """POST /ask persists session_id and records turns across sequential calls."""
    session_id = "test-multi-turn-session-xyz"

    headers = {"X-API-Key": settings.api_key}

    # Turn 1
    resp1 = client.post(
        "/ask",
        headers=headers,
        json={"question": "Where is PostgreSQL configured?", "session_id": session_id},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["session_id"] == session_id

    # Turn 2 with follow-up in the same session
    resp2 = client.post(
        "/ask",
        headers=headers,
        json={"question": "What is its port and default user?", "session_id": session_id},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["session_id"] == session_id

