"""Regression tests for previously-fixed defects.

Each test here pins a specific bug that shipped once. They are deliberately
narrow: they assert the fixed behaviour, not the surrounding feature.
"""

import json
from unittest.mock import patch

import pytest

from src.api import tasks
from src.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# /ask/stream used to call the rate-limited /ask handler, spending two tokens
# from the caller's budget for a single request.
# ─────────────────────────────────────────────────────────────────────────────
def test_stream_does_not_reenter_the_rate_limited_ask_handler(client, auth_headers):
    """One HTTP request must hit the shared impl exactly once.

    The old /ask/stream called the decorated ask_question(), so slowapi counted
    the request twice and halved the caller's effective budget.
    """
    import src.api.main as main

    calls: list[str] = []
    real_impl = main._ask_impl

    def counting_impl(request, body):
        calls.append(body.question)
        return real_impl(request, body)

    with patch.object(main, "_ask_impl", counting_impl):
        response = client.post(
            "/ask/stream",
            json={"question": "Where is auth implemented?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert len(calls) == 1


def test_ask_stream_route_does_not_call_ask_route():
    """Static guard: the streaming route must not delegate to the decorated one."""
    import inspect

    from src.api import main

    source = inspect.getsource(main.ask_question_stream)
    assert "_ask_impl" in source
    assert "ask_question(" not in source


# ─────────────────────────────────────────────────────────────────────────────
# The router used to run twice for agent-routed queries: once in the API layer
# and again inside the graph's router node.
# ─────────────────────────────────────────────────────────────────────────────
def test_agent_reuses_preresolved_route():
    from src.agent.graph import create_agent_graph
    from tests.conftest import FakeGenerator, FakeRetriever

    graph = create_agent_graph(FakeRetriever(), FakeGenerator())

    with patch("src.agent.graph.route_query") as route_query:
        state = graph.invoke({
            "question": "Which files changed in commit abc1234?",
            "top_k": 3,
            "route": "git_commit",
            "route_reasoning": "pre-resolved by the API layer",
            "target": "abc1234",
            "steps_taken": ["received_query"],
        })

    route_query.assert_not_called()
    assert state["route"] == "git_commit"
    assert any(step.startswith("reused_route") for step in state["steps_taken"])


def test_agent_routes_itself_when_no_route_supplied():
    from src.agent.graph import create_agent_graph
    from tests.conftest import FakeGenerator, FakeRetriever

    graph = create_agent_graph(FakeRetriever(), FakeGenerator())
    state = graph.invoke({
        "question": "Show me the diff for commit abc1234",
        "top_k": 3,
        "steps_taken": ["received_query"],
    })

    assert state["route"] == "git_commit"
    assert any(step.startswith("routed_to") for step in state["steps_taken"])


# ─────────────────────────────────────────────────────────────────────────────
# Tool output used to be dumped raw into a code fence, never reaching the model.
# ─────────────────────────────────────────────────────────────────────────────
def test_tool_output_is_synthesized_by_the_generator():
    from src.agent.graph import create_agent_graph
    from tests.conftest import FakeGenerator, FakeRetriever

    generator = FakeGenerator()
    graph = create_agent_graph(FakeRetriever(), generator)

    with patch("src.agent.graph.get_git_commit_history", return_value="abc1234 - dev, 2h ago : fix auth"):
        state = graph.invoke({
            "question": "What are the recent commits?",
            "route": "git_history",
            "route_reasoning": "explicit history request",
            "steps_taken": [],
        })

    # FakeGenerator.generate_from_tool_output prefixes with "Summary for <route>"
    assert "Summary for git_history" in state["answer"]
    assert "abc1234" in state["answer"]


# ─────────────────────────────────────────────────────────────────────────────
# Concurrent /ingest calls could both pass the status check and start a run.
# ─────────────────────────────────────────────────────────────────────────────
def test_ingestion_claim_is_atomic():
    tasks._update_state(status=tasks.IngestionStatus.IDLE, error=None)
    assert tasks._claim_run() is True
    assert tasks._claim_run() is False
    tasks._update_state(status=tasks.IngestionStatus.IDLE, error=None)


@pytest.mark.asyncio
async def test_second_concurrent_ingest_is_rejected():
    tasks._update_state(status=tasks.IngestionStatus.IDLE, error=None)
    try:
        with patch.object(tasks, "_run_full_in_background", return_value=None):
            first = await tasks.trigger_ingestion()
            second = await tasks.trigger_ingestion()
        assert first is True
        assert second is False
    finally:
        tasks._update_state(status=tasks.IngestionStatus.IDLE, error=None)


# ─────────────────────────────────────────────────────────────────────────────
# Streaming errors used to echo raw exception text (internal hosts, key
# fragments) straight to the browser.
# ─────────────────────────────────────────────────────────────────────────────
def test_stream_error_does_not_leak_internals(client, auth_headers):
    from src.api.main import services

    secret = "postgres://admin:hunter2@internal-db:5432"

    with patch.object(services["retriever"], "retrieve", side_effect=RuntimeError(secret)):
        response = client.post(
            "/ask/stream",
            json={"question": "Where is auth implemented?"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    events = [
        json.loads(line[5:].strip())
        for line in response.text.split("\n")
        if line.strip().startswith("data:") and line[5:].strip()
    ]
    errors = [e for e in events if e.get("type") == "error"]
    assert errors, "expected an error event"
    assert secret not in response.text
    assert errors[0]["error"] == "An internal error occurred while generating the answer."


# ─────────────────────────────────────────────────────────────────────────────
# A domain error should still reach the client as a useful, non-leaking message.
# ─────────────────────────────────────────────────────────────────────────────
def test_stream_surfaces_domain_errors(client, auth_headers):
    from src.api.main import services
    from src.errors import VectorDBUnavailableError

    with patch.object(
        services["retriever"], "retrieve", side_effect=VectorDBUnavailableError()
    ):
        response = client.post(
            "/ask/stream",
            json={"question": "Where is auth implemented?"},
            headers=auth_headers,
        )

    events = [
        json.loads(line[5:].strip())
        for line in response.text.split("\n")
        if line.strip().startswith("data:") and line[5:].strip()
    ]
    errors = [e for e in events if e.get("type") == "error"]
    assert errors and errors[0]["code"] == "VECTOR_DB_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# The API key was compared with `!=`, and a missing header produced a 422.
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_api_key_is_unauthorized(client):
    assert client.post("/ask", json={"question": "anything at all"}).status_code == 401


def test_wrong_api_key_is_unauthorized(client):
    response = client.post(
        "/ask",
        json={"question": "anything at all"},
        headers={"X-API-Key": "definitely-not-the-key"},
    )
    assert response.status_code == 401


def test_api_key_comparison_is_constant_time():
    import inspect

    from src.api import main

    source = inspect.getsource(main._api_key_matches)
    assert "compare_digest" in source


# ─────────────────────────────────────────────────────────────────────────────
# Langfuse v2 API calls raised AttributeError against the pinned v4 SDK, and
# the failure surfaced as a 500 on /ask.
# ─────────────────────────────────────────────────────────────────────────────
def test_tracing_failure_falls_back_to_untraced(fake_chunks):
    from src import observability
    from tests.conftest import FAKE_ANSWER, FakeGenerator, FakeRetriever

    class BrokenLangfuse:
        def start_as_current_observation(self, **kwargs):
            raise AttributeError("'Langfuse' object has no attribute 'trace'")

    with patch.object(observability, "_langfuse", BrokenLangfuse()):
        result = observability.traced_ask(
            "Where is auth?", 3, FakeRetriever(), FakeGenerator()
        )

    assert result["answer"] == FAKE_ANSWER
    assert result["trace_id"] is None


def test_observability_uses_v4_api_surface():
    """Guards against reintroducing the removed v2 client methods."""
    import inspect

    from src import observability

    source = inspect.getsource(observability)
    assert "start_as_current_observation" in source
    assert "_langfuse.trace(" not in source


# ─────────────────────────────────────────────────────────────────────────────
# Routing ignored a client-supplied Gemini key, so client-key users always got
# direct_rag regardless of their question.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.real_router
def test_llm_router_uses_client_supplied_key():
    from src.agent import router

    captured = {}

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = self

        def generate_content(self, **kwargs):
            captured["model"] = kwargs.get("model")
            return type("R", (), {"text": "ROUTE: git_history\nREASON: test\nTARGET: NONE"})()

    with patch.object(router.genai, "Client", FakeClient):
        route, _, _ = router.classify_route_llm("tell me about the repo", api_key="client-key-123")

    assert captured["api_key"] == "client-key-123"
    assert captured["model"] == settings.gemini_model
    assert route == "git_history"


@pytest.mark.real_router
def test_llm_router_without_any_key_defaults_to_rag():
    from src.agent import router

    with patch.object(type(settings), "has_gemini_key", property(lambda self: False)):
        route, reason, _ = router.classify_route_llm("tell me about the repo", api_key=None)

    assert route == "direct_rag"
    assert "no Gemini API key" in reason


# ─────────────────────────────────────────────────────────────────────────────
# Non-retryable upstream errors used to burn one round trip per fallback model.
# ─────────────────────────────────────────────────────────────────────────────
def test_non_retryable_error_stops_model_fallback(fake_chunks):
    from google.genai.errors import ClientError

    from src.generation.generator import AnswerGenerator

    generator = AnswerGenerator.__new__(AnswerGenerator)
    generator.model_name = settings.gemini_model
    generator.raise_on_quota = False
    generator.client = object()

    attempts: list[str] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs["model"])
            raise ClientError(
                400, {"error": {"message": "API key not valid", "code": 400}}, None
            )

    class FakeClient:
        models = FakeModels()

    with patch.object(AnswerGenerator, "_resolve_client", lambda self, key=None: (FakeClient(), False)):
        result = generator.generate("Where is auth?", fake_chunks)

    assert len(attempts) == 1, f"expected one attempt for a 400, got {attempts}"
    assert "AI Service Warning" in result.answer


def test_quota_error_does_try_fallback_models(fake_chunks):
    from src.generation.generator import AnswerGenerator

    generator = AnswerGenerator.__new__(AnswerGenerator)
    generator.model_name = settings.gemini_model
    generator.raise_on_quota = False
    generator.client = object()

    attempts: list[str] = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs["model"])
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    class FakeClient:
        models = FakeModels()

    with patch.object(AnswerGenerator, "_resolve_client", lambda self, key=None: (FakeClient(), False)):
        result = generator.generate("Where is auth?", fake_chunks)

    assert attempts == generator.model_candidates
    assert "Quota Exceeded" in result.answer
