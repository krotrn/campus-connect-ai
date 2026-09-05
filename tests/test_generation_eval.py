"""Unit tests for the RAG Triad generation evaluation suite."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evals.generation_eval import RAGTriadJudge, run_generation_evaluation
from src.retrieval.retriever import RetrievedChunk


@pytest.fixture
def mock_chunks():
    return [
        RetrievedChunk(
            content="export function loginUser(email, password) { return verify(email, password); }",
            file_path="src/auth/login.ts",
            start_line=1,
            end_line=5,
            file_type="code",
            score=0.92,
        ),
        RetrievedChunk(
            content="export const authConfig = { secret: process.env.AUTH_SECRET };",
            file_path="src/config/auth.ts",
            start_line=1,
            end_line=3,
            file_type="code",
            score=0.85,
        ),
    ]


def test_judge_faithful_evaluation(mock_chunks):
    """When judge confirms all claims are supported, Faithfulness is 1.0."""
    judge = RAGTriadJudge()

    mock_llm_response = MagicMock()
    mock_llm_response.text = json.dumps({
        "claims": [
            {"statement": "Login is in src/auth/login.ts", "supported": True, "evidence": "Chunk 1"},
            {"statement": "Auth config is in src/config/auth.ts", "supported": True, "evidence": "Chunk 2"},
        ],
        "faithfulness_score": 1.0,
        "faithfulness_reason": "All claims directly present in context",
        "answer_relevance_score": 0.95,
        "answer_relevance_reason": "Directly answers the authentication question",
        "useful_chunk_indices": [1, 2],
        "context_precision_score": 1.0,
    })

    with patch.object(judge.client.models, "generate_content", return_value=mock_llm_response):
        result = judge.evaluate(
            question="Where is login defined?",
            retrieved_chunks=mock_chunks,
            generated_answer="Login is in src/auth/login.ts and auth config is in src/config/auth.ts.",
            expected_summary="Login and auth config locations",
        )

    assert result["faithfulness"] == 1.0
    assert result["answer_relevance"] == 0.95
    assert result["context_precision"] == 1.0
    assert len(result["unsupported_claims"]) == 0


def test_judge_hallucination_detection(mock_chunks):
    """When an unsupported claim is introduced, Faithfulness drops and unsupported claim is flagged."""
    judge = RAGTriadJudge()

    mock_llm_response = MagicMock()
    mock_llm_response.text = json.dumps({
        "claims": [
            {"statement": "Login is in src/auth/login.ts", "supported": True, "evidence": "Chunk 1"},
            {"statement": "Uses OAuth2 with Google and GitHub", "supported": False, "evidence": "Not in context"},
        ],
        "faithfulness_score": 0.5,
        "faithfulness_reason": "OAuth claim is unsubstantiated by context",
        "answer_relevance_score": 0.8,
        "answer_relevance_reason": "Answers the question but hallucinated providers",
        "useful_chunk_indices": [1],
        "context_precision_score": 0.5,
    })

    with patch.object(judge.client.models, "generate_content", return_value=mock_llm_response):
        result = judge.evaluate(
            question="Where is login defined?",
            retrieved_chunks=mock_chunks,
            generated_answer="Login is in src/auth/login.ts and uses OAuth2 with Google and GitHub.",
            expected_summary="Login location",
        )

    assert result["faithfulness"] == 0.5
    assert len(result["unsupported_claims"]) == 1
    assert result["unsupported_claims"][0]["statement"] == "Uses OAuth2 with Google and GitHub"


def test_run_generation_evaluation_end_to_end(tmp_path, mock_chunks):
    """run_generation_evaluation aggregates metrics and writes benchmark report."""
    dataset_file = tmp_path / "test_dataset.json"
    output_file = tmp_path / "benchmark_out.json"

    dataset_file.write_text(
        json.dumps([
            {
                "id": "t001",
                "category": "auth",
                "question": "Where is login?",
                "expected_sources": ["src/auth/login.ts"],
                "expected_answer_summary": "Login in src/auth/login.ts",
            }
        ])
    )

    with patch("evals.generation_eval.Retriever") as MockRetriever, \
         patch("evals.generation_eval.AnswerGenerator") as MockGenerator, \
         patch("evals.generation_eval.RAGTriadJudge") as MockJudge:

        mock_ret_instance = MockRetriever.return_value
        mock_ret_instance.retrieve.return_value = mock_chunks

        mock_gen_instance = MockGenerator.return_value
        mock_resp = MagicMock()
        mock_resp.answer = "Login is defined in src/auth/login.ts."
        mock_gen_instance.generate.return_value = mock_resp

        mock_judge_instance = MockJudge.return_value
        mock_judge_instance.evaluate.return_value = {
            "faithfulness": 1.0,
            "answer_relevance": 0.95,
            "context_precision": 0.8,
            "unsupported_claims": [],
        }

        report = run_generation_evaluation(
            dataset_path=dataset_file,
            limit=1,
            output_path=output_file,
        )

    assert report["total_evaluated"] == 1
    assert report["overall_metrics"]["faithfulness"] == 1.0
    assert report["overall_metrics"]["answer_relevance"] == 0.95
    assert report["overall_metrics"]["context_precision"] == 0.8
    assert output_file.exists()

