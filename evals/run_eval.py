import json
import sys
import time
from pathlib import Path
from typing import Dict

# Ensure project root is on sys.path when executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.retrieval.retriever import Retriever


def evaluate_retrieval(dataset_path: Path = Path("evals/dataset.json")):
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    retriever = Retriever()
    print(f"📊 Running Retrieval Evaluation Suite on {len(data)} test cases...\n")

    top_k_eval = 10
    total = len(data)

    hits_at_5 = 0
    hits_at_10 = 0
    reciprocal_ranks = []
    latencies = []

    category_stats: Dict[str, Dict[str, int]] = {}

    for item in data:
        qid = item["id"]
        question = item["question"]
        expected_sources = set(item["expected_sources"])
        category = item.get("category", "general")

        if category not in category_stats:
            category_stats[category] = {"total": 0, "hits_5": 0, "hits_10": 0}
        category_stats[category]["total"] += 1

        t0 = time.time()
        chunks = retriever.retrieve(question, top_k=top_k_eval)
        latencies.append((time.time() - t0) * 1000)

        retrieved_files = [c.file_path for c in chunks]

        # Calculate Rank of first expected hit
        first_hit_rank = None
        for rank, file_path in enumerate(retrieved_files, start=1):
            if any(exp in file_path or file_path in exp for exp in expected_sources):
                first_hit_rank = rank
                break

        if first_hit_rank is not None:
            reciprocal_ranks.append(1.0 / first_hit_rank)
            if first_hit_rank <= 5:
                hits_at_5 += 1
                category_stats[category]["hits_5"] += 1
            if first_hit_rank <= 10:
                hits_at_10 += 1
                category_stats[category]["hits_10"] += 1
        else:
            reciprocal_ranks.append(0.0)

        status_emoji = "✅" if first_hit_rank and first_hit_rank <= 5 else ("⚠️" if first_hit_rank else "❌")
        rank_str = f"Rank {first_hit_rank}" if first_hit_rank else "MISSED"
        print(f"{status_emoji} [{qid}] ({category:<22}) {rank_str:<10} | Q: {question[:48]}...")

    recall_5 = (hits_at_5 / total) * 100
    recall_10 = (hits_at_10 / total) * 100
    mrr = (sum(reciprocal_ranks) / total)
    avg_latency = sum(latencies) / len(latencies)

    print(f"\n{'=' * 60}")
    print("📈 RETRIEVAL EVALUATION RESULTS (V2 — HYBRID + RERANK)")
    print("=" * 60)
    print(f"Total Test Cases:       {total}")
    print(f"Recall@5:               {recall_5:.1f}% ({hits_at_5}/{total})")
    print(f"Recall@10:              {recall_10:.1f}% ({hits_at_10}/{total})")
    print(f"Mean Reciprocal Rank:   {mrr:.4f}")
    print(f"Average Search Latency: {avg_latency:.2f} ms")
    print("=" * 60)

    print("\n📂 Category Breakdown:")
    print(f"{'Category':<24} | {'Count':<5} | {'Recall@5':<10} | {'Recall@10':<10}")
    print("-" * 58)
    for cat, stats in category_stats.items():
        c_total = stats["total"]
        r5 = (stats["hits_5"] / c_total) * 100
        r10 = (stats["hits_10"] / c_total) * 100
        print(f"{cat:<24} | {c_total:<5} | {r5:>8.1f}% | {r10:>8.1f}%")
    print("-" * 58)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AEIA Evaluation Suite")
    parser.add_argument("--generation", action="store_true", help="Also run RAG Triad generation evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries evaluated")
    args = parser.parse_args()

    evaluate_retrieval()

    if args.generation:
        from evals.generation_eval import run_generation_evaluation

        run_generation_evaluation(limit=args.limit)

