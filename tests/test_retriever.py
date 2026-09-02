import pytest
from src.retrieval.retriever import Retriever


@pytest.fixture
def retriever():
    return Retriever()


def test_retriever_returns_top_k_chunks(retriever):
    query = "Where is authentication implemented?"
    top_k = 3
    results = retriever.retrieve(query, top_k=top_k)

    assert len(results) == top_k
    for chunk in results:
        assert chunk.file_path != ""
        assert chunk.content != ""
        assert chunk.start_line > 0
        assert chunk.end_line >= chunk.start_line
        assert chunk.score > 0.0
        assert "#L" in chunk.citation


def test_retriever_respects_custom_top_k(retriever):
    query = "database schema"
    results_1 = retriever.retrieve(query, top_k=1)
    results_5 = retriever.retrieve(query, top_k=5)

    assert len(results_1) == 1
    assert len(results_5) == 5

