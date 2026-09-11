"""Shared test fixtures.

By default the suite runs fully offline against in-memory fakes: no Qdrant, no
Gemini, no API quota spent, no multi-second model downloads.  This keeps the
tests runnable in CI and on a laptop with the stack shut down.

To exercise the real stack instead, run with::

    AEIA_TEST_MODE=integration uv run pytest

which requires a populated Qdrant and a valid GEMINI_API_KEY.
"""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

INTEGRATION = os.getenv("AEIA_TEST_MODE", "").lower() == "integration"

# Deterministic corpus stand-in used by the fake retriever.
FAKE_CHUNKS = [
    {
        "content": "export async function authorize(credentials) { /* ... */ }",
        "file_path": "src/lib/auth.ts",
        "start_line": 10,
        "end_line": 42,
        "file_type": "code",
        "score": 0.91,
    },
    {
        "content": "model User {\n  id String @id\n  email String @unique\n}",
        "file_path": "prisma/schema.prisma",
        "start_line": 1,
        "end_line": 12,
        "file_type": "schema",
        "score": 0.77,
    },
    {
        "content": "redis:\n  image: redis:8.2.1-alpine\n  ports:\n    - '6379:6379'",
        "file_path": "compose.yml",
        "start_line": 30,
        "end_line": 40,
        "file_type": "config",
        "score": 0.64,
    },
]

FAKE_ANSWER = "Authentication is handled in `authorize` [src/lib/auth.ts#L10-L42]."


def _fake_chunk_objects():
    from src.retrieval.retriever import RetrievedChunk

    return [RetrievedChunk(**c) for c in FAKE_CHUNKS]


class FakeQdrantClient:
    """Minimal stand-in for the bits of QdrantClient the API touches."""

    def __init__(self, points_count: int = len(FAKE_CHUNKS)):
        self.points_count = points_count

    def get_collection(self, collection_name: str):
        return SimpleNamespace(points_count=self.points_count)

    def scroll(self, *args, **kwargs):
        return [], None


class FakeRetriever:
    """Returns canned chunks without touching Qdrant or loading an embedder."""

    def __init__(self, *args, **kwargs):
        self.client = FakeQdrantClient()
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, top_k: int = 5):
        self.calls.append((query, top_k))
        return _fake_chunk_objects()[:top_k]

    def reload_bm25(self):
        return None


class FakeGenerator:
    """Deterministic generator that never calls the Gemini API."""

    def __init__(self, *args, **kwargs):
        from src.config import settings

        self.model_name = settings.gemini_model
        self.client = None
        self.raise_on_quota = False

    @staticmethod
    def _sources(chunks):
        from src.generation.generator import SourceCitation

        return [
            SourceCitation(
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                citation=c.citation,
                content=c.content,
                score=c.score,
            )
            for c in chunks
        ]

    def generate(self, question, chunks, history=None, api_key=None):
        from src.generation.generator import AnswerResponse

        return AnswerResponse(
            question=question,
            answer=FAKE_ANSWER,
            sources=self._sources(chunks),
            model_used=self.model_name,
        )

    def generate_from_tool_output(self, question, tool_output, route, api_key=None):
        return f"Summary for {route}:\n\n```text\n{tool_output}\n```"

    def generate_stream(self, question, chunks, history=None, api_key=None):
        sources = self._sources(chunks)
        yield {"type": "sources", "sources": [s.model_dump() for s in sources]}
        for word in FAKE_ANSWER.split(" "):
            yield {"type": "token", "text": word + " "}
        yield {"type": "done", "answer": FAKE_ANSWER, "model": self.model_name}


@pytest.fixture(autouse=True)
def offline_services():
    """Patch the heavy service constructors unless running in integration mode."""
    if INTEGRATION:
        yield
        return

    with (
        patch("src.api.main.Retriever", FakeRetriever),
        patch("src.api.main.AnswerGenerator", FakeGenerator),
        patch("src.mcp.server.Retriever", FakeRetriever),
        patch("src.mcp.server.AnswerGenerator", FakeGenerator),
    ):
        yield


@pytest.fixture(autouse=True)
def offline_routing(request):
    """Keep the LLM router out of unit tests; rule-based routing still applies.

    Tests that exercise the router itself opt out with @pytest.mark.real_router.
    """
    if INTEGRATION or request.node.get_closest_marker("real_router"):
        yield
        return

    from src.agent import router as router_module

    def _no_llm(question: str, api_key: str | None = None):
        return ("direct_rag", "Defaulted to direct RAG (routing stubbed in tests).", "")

    with (
        patch.object(router_module, "classify_route_llm", _no_llm),
        patch("src.agent.graph.route_query", router_module.route_query),
    ):
        yield


@pytest.fixture(autouse=True)
def offline_query_rewrite():
    """Coreference rewriting is an LLM call; pass the query through untouched."""
    if INTEGRATION:
        yield
        return

    with patch("src.api.main.rewrite_query_with_history", lambda q, h, client=None: q):
        yield


@pytest.fixture
def client():
    """TestClient with the app lifespan run (services populated)."""
    from fastapi.testclient import TestClient

    from src.api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    from src.config import settings

    return {"X-API-Key": settings.api_key}


@pytest.fixture
def fake_chunks():
    return _fake_chunk_objects()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: requires a live Qdrant and Gemini API key"
    )
    config.addinivalue_line(
        "markers", "real_router: exercise the real LLM router instead of the test stub"
    )


def pytest_collection_modifyitems(config, items):
    if INTEGRATION:
        return
    skip = pytest.mark.skip(reason="needs live Qdrant/Gemini; set AEIA_TEST_MODE=integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
