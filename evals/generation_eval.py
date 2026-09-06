"""
RAG Triad Generation Evaluation Suite for AEIA.

Measures the 3 essential dimensions of RAG generation quality:
1. Faithfulness (Groundedness): Are all claims in the answer strictly entailed by the retrieved context? (Hallucination rate = 1 - Faithfulness)
2. Answer Relevance: Does the generated answer directly address the user's question without extraneous filler?
3. Context Precision: Were the retrieved chunks actually relevant and necessary to synthesize the answer?

Uses Google Gemini (gemini-3.6-flash) as an automated LLM-as-a-Judge.
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import types

from src.config import settings
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import RetrievedChunk, Retriever

JUDGE_SYSTEM_PROMPT = """You are an impartial, expert AI benchmark judge evaluating a RAG (Retrieval-Augmented Generation) system for a codebase intelligence tool.

You will be given:
1. [User Question]: The software engineering question.
2. [Retrieved Context Chunks]: The code and configuration chunks retrieved by the search engine.
3. [Generated Answer]: The answer synthesized by the RAG model.
4. [Reference Summary]: A ground-truth summary of what a correct answer must cover.

Evaluate the generation across the RAG Triad:

1. FAITHFULNESS (Groundedness / Hallucination Check):
   - Break the Generated Answer into atomic claims/statements.
   - Check whether each claim is strictly supported by the [Retrieved Context Chunks].
   - If a claim mentions a file, function, or fact not found in the context, it is UNSUPPORTED.
   - faithfulness_score = (supported_claims / total_claims). If answer admits no info, score is 1.0.

2. ANSWER RELEVANCE:
   - Score from 0.0 to 1.0 how directly, concisely, and completely the answer addresses the [User Question] compared to the [Reference Summary].
   - 1.0: Directly answers the question with accurate code references.
   - 0.5: Vague, partially answers, or includes extraneous filler.
   - 0.0: Irrelevant or completely fails to answer.

3. CONTEXT PRECISION:
   - Identify which of the provided chunks (1 to N) contained information directly useful for answering the question.
   - context_precision_score = (count of useful chunks / total chunks evaluated).

Respond ONLY with valid JSON in this exact structure:
{
  "claims": [
    {"statement": "...", "supported": true, "evidence": "chunk citation or reason"}
  ],
  "faithfulness_score": 1.0,
  "faithfulness_reason": "...",
  "answer_relevance_score": 0.95,
  "answer_relevance_reason": "...",
  "useful_chunk_indices": [1, 2],
  "context_precision_score": 0.67
}
"""


@dataclass
class TriadEvaluationResult:
    id: str
    category: str
    question: str
    faithfulness: float
    answer_relevance: float
    context_precision: float
    unsupported_claims_count: int
    retrieval_latency_ms: float
    generation_latency_ms: float
    route: str = "direct_rag"


class RAGTriadJudge:
    def __init__(self, judge_model: str = "gemini-3.6-flash"):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.judge_model = judge_model

    def evaluate(
        self,
        question: str,
        retrieved_chunks: List[RetrievedChunk],
        generated_answer: str,
        expected_summary: str,
    ) -> Dict[str, Any]:
        """Judge a single question-generation pair against retrieved context."""
        context_str = "\n\n".join(
            f"[Chunk {i+1}] ({c.citation}):\n{c.content}"
            for i, c in enumerate(retrieved_chunks)
        )

        user_prompt = f"""[User Question]
{question}

[Retrieved Context Chunks]
{context_str}

[Generated Answer]
{generated_answer}

[Reference Summary]
{expected_summary}
"""

        candidates = [self.judge_model]
        for alt in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
            if alt not in candidates:
                candidates.append(alt)

        last_error = None
        for model in candidates:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=JUDGE_SYSTEM_PROMPT,
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                raw = (response.text or "").strip()
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\n?", "", raw)
                    raw = re.sub(r"\n?```$", "", raw)

                parsed = json.loads(raw)
                return {
                    "faithfulness": float(parsed.get("faithfulness_score", 1.0)),
                    "answer_relevance": float(parsed.get("answer_relevance_score", 1.0)),
                    "context_precision": float(parsed.get("context_precision_score", 1.0)),
                    "unsupported_claims": [c for c in parsed.get("claims", []) if not c.get("supported", True)],
                    "details": parsed,
                }
            except Exception as e:
                last_error = e
                continue
        print(f"⚠️ Judge evaluation FAILED — recording 0.0 scores ({last_error})")
        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_precision": 0.0,
            "unsupported_claims": [],
            "error": str(last_error),
        }


def run_generation_evaluation(
    dataset_path: Path = Path("evals/dataset.json"),
    limit: Optional[int] = None,
    output_path: Path = Path("evals/generation_benchmark.json"),
    top_k: int = 5,
) -> Dict[str, Any]:
    """Run full RAG Triad evaluation over the golden dataset."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    print(f"\n=======================================================")
    print(f"⚖️  RAG Triad Generation Evaluation ({len(data)} test cases)")
    print(f"=======================================================\n")

    retriever = Retriever()
    generator = AnswerGenerator()
    judge = RAGTriadJudge()

    results: List[TriadEvaluationResult] = []
    category_metrics: Dict[str, Dict[str, List[float]]] = {}

    for idx, item in enumerate(data, start=1):
        qid = item["id"]
        cat = item.get("category", "general")
        question = item["question"]
        expected_summary = item.get("expected_answer_summary", "")

        # 1. Retrieval
        t_ret_0 = time.time()
        chunks = retriever.retrieve(question, top_k=top_k)
        ret_latency = (time.time() - t_ret_0) * 1000

        # 2. Generation
        t_gen_0 = time.time()
        resp = generator.generate(question, chunks)
        gen_latency = (time.time() - t_gen_0) * 1000

        # 3. Judge Evaluation
        judge_res = judge.evaluate(
            question=question,
            retrieved_chunks=chunks,
            generated_answer=resp.answer,
            expected_summary=expected_summary,
        )

        faith = judge_res["faithfulness"]
        relevance = judge_res["answer_relevance"]
        precision = judge_res["context_precision"]
        unsupported = len(judge_res["unsupported_claims"])

        results.append(
            TriadEvaluationResult(
                id=qid,
                category=cat,
                question=question,
                faithfulness=faith,
                answer_relevance=relevance,
                context_precision=precision,
                unsupported_claims_count=unsupported,
                retrieval_latency_ms=ret_latency,
                generation_latency_ms=gen_latency,
            )
        )

        if cat not in category_metrics:
            category_metrics[cat] = {
                "faithfulness": [],
                "relevance": [],
                "precision": [],
            }
        category_metrics[cat]["faithfulness"].append(faith)
        category_metrics[cat]["relevance"].append(relevance)
        category_metrics[cat]["precision"].append(precision)

        status_flag = "✅" if faith >= 0.9 and relevance >= 0.85 else "⚠️"
        print(
            f"{status_flag} [{idx:02d}/{len(data):02d}] {qid} ({cat:<22}) | "
            f"Faith: {faith*100:5.1f}% | Rel: {relevance*100:5.1f}% | Prec: {precision*100:5.1f}%"
        )

    # Calculate overall aggregates
    avg_faithfulness = sum(r.faithfulness for r in results) / len(results)
    avg_relevance = sum(r.answer_relevance for r in results) / len(results)
    avg_precision = sum(r.context_precision for r in results) / len(results)
    hallucination_rate = (1.0 - avg_faithfulness) * 100

    print("\n" + "=" * 70)
    print("📊 RAG TRIAD GENERATION EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  • Total Test Cases Evaluated : {len(results)}")
    print(f"  • Average Faithfulness       : {avg_faithfulness * 100:.2f}% (Groundedness)")
    print(f"  • Hallucination Rate         : {hallucination_rate:.2f}%")
    print(f"  • Average Answer Relevance   : {avg_relevance * 100:.2f}%")
    print(f"  • Average Context Precision  : {avg_precision * 100:.2f}%")
    print("-" * 70)
    print(f"{'Category':<26} {'Faithfulness':<14} {'Relevance':<14} {'Context Prec':<14}")
    print("-" * 70)

    cat_breakdown = {}
    for cat, vals in category_metrics.items():
        c_faith = sum(vals["faithfulness"]) / len(vals["faithfulness"]) * 100
        c_rel = sum(vals["relevance"]) / len(vals["relevance"]) * 100
        c_prec = sum(vals["precision"]) / len(vals["precision"]) * 100
        cat_breakdown[cat] = {
            "faithfulness": round(c_faith, 2),
            "relevance": round(c_rel, 2),
            "precision": round(c_prec, 2),
        }
        print(f"{cat:<26} {c_faith:6.1f}%        {c_rel:6.1f}%        {c_prec:6.1f}%")
    print("=" * 70 + "\n")

    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_evaluated": len(results),
        "overall_metrics": {
            "faithfulness": round(avg_faithfulness, 4),
            "hallucination_rate": round(hallucination_rate / 100.0, 4),
            "answer_relevance": round(avg_relevance, 4),
            "context_precision": round(avg_precision, 4),
        },
        "category_breakdown": cat_breakdown,
        "results": [asdict(r) for r in results],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"💾 Saved generation benchmark report to {output_path}")

    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG Triad Generation Evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries evaluated")
    parser.add_argument("--dataset", type=Path, default=Path("evals/dataset.json"), help="Path to golden dataset")
    parser.add_argument("--output", type=Path, default=Path("evals/generation_benchmark.json"), help="Path to output JSON")
    args = parser.parse_args()

    run_generation_evaluation(dataset_path=args.dataset, limit=args.limit, output_path=args.output)
