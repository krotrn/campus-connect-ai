import re
import sys
from dataclasses import dataclass
from typing import List, Dict, Tuple

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest

from src.config import settings
from src.errors import VectorDBUnavailableError

RRF_K = 60  # standard constant for Reciprocal Rank Fusion
DENSE_WEIGHT = 0.7
SPARSE_WEIGHT = 0.3


@dataclass
class RetrievedChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    file_type: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.file_path}#L{self.start_line}-L{self.end_line}"


class Retriever:
    def __init__(self, rerank: bool = False):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.embedding_model = TextEmbedding(model_name=settings.embedding_model)
        self.rerank = rerank

        # ── Build BM25 index from Qdrant payload ──────────────────────────────
        print("📚 Building BM25 index from Qdrant collection...")
        self._all_chunks: List[dict] = self._scroll_all_payloads()
        tokenized = [self._tokenize(c["content"]) for c in self._all_chunks]
        self._bm25 = BM25Okapi(tokenized)
        print(f"   BM25 index built over {len(self._all_chunks)} chunks.")

        # ── Load cross-encoder reranker ───────────────────────────────────────
        if self.rerank:
            print("⚡ Loading FlashRank cross-encoder...")
            self._ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
            print("   Reranker ready.")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """
        Hybrid retrieval: dense vector + BM25 fused with RRF,
        then optionally reranked by a cross-encoder.
        """
        candidate_k = max(top_k * 4, 20)  # fetch more candidates for reranking

        dense_results = self._retrieve_dense(query, top_k=candidate_k)
        sparse_results = self._retrieve_bm25(query, top_k=candidate_k)

        fused = self._reciprocal_rank_fusion(dense_results, sparse_results)

        # Take top candidates for reranking
        candidates = fused[:candidate_k]

        if self.rerank and candidates:
            candidates = self._rerank(query, candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]

        return candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Dense retrieval
    # ─────────────────────────────────────────────────────────────────────────

    def _retrieve_dense(self, query: str, top_k: int) -> List[RetrievedChunk]:
        try:
            query_vector = list(self.embedding_model.embed(query))[0].tolist()
            results = self.client.query_points(
                collection_name=settings.collection_name,
                query=query_vector,
                limit=top_k,
            )
        except Exception as e:
            raise VectorDBUnavailableError(f"Qdrant vector query failed: {str(e)}") from e

        chunks = []
        for point in results.points:
            payload = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    file_type=payload.get("file_type", ""),
                    score=point.score,
                )
            )
        return chunks

    # ─────────────────────────────────────────────────────────────────────────
    # Sparse / BM25 retrieval
    # ─────────────────────────────────────────────────────────────────────────

    def _retrieve_bm25(self, query: str, top_k: int) -> List[RetrievedChunk]:
        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)

        # Get top_k indices sorted by descending score
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        chunks = []
        for idx in top_indices:
            payload = self._all_chunks[idx]
            chunks.append(
                RetrievedChunk(
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    file_type=payload.get("file_type", ""),
                    score=float(scores[idx]),
                )
            )
        return chunks

    # ─────────────────────────────────────────────────────────────────────────
    # Reciprocal Rank Fusion
    # ─────────────────────────────────────────────────────────────────────────

    def _reciprocal_rank_fusion(
        self,
        dense: List[RetrievedChunk],
        sparse: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Merge two ranked lists using RRF.
        Score = Σ 1 / (k + rank)  for each list the document appears in.
        """
        # Use (file_path, start_line) as a stable dedup key
        rrf_scores: Dict[Tuple[str, int], float] = {}
        chunk_map: Dict[Tuple[str, int], RetrievedChunk] = {}

        for rank, chunk in enumerate(dense, start=1):
            key = (chunk.file_path, chunk.start_line)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + DENSE_WEIGHT / (RRF_K + rank)
            chunk_map[key] = chunk


        for rank, chunk in enumerate(sparse, start=1):
            key = (chunk.file_path, chunk.start_line)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + SPARSE_WEIGHT / (RRF_K + rank)
            if key not in chunk_map:
                chunk_map[key] = chunk


        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

        return [
            RetrievedChunk(
                content=chunk_map[k].content,
                file_path=chunk_map[k].file_path,
                start_line=chunk_map[k].start_line,
                end_line=chunk_map[k].end_line,
                file_type=chunk_map[k].file_type,
                score=rrf_scores[k],
            )
            for k in sorted_keys
        ]


    # ─────────────────────────────────────────────────────────────────────────
    # Cross-encoder reranking
    # ─────────────────────────────────────────────────────────────────────────

    def _rerank(
        self, query: str, candidates: List[RetrievedChunk], top_k: int
    ) -> List[RetrievedChunk]:
        passages = [{"id": i, "text": c.content} for i, c in enumerate(candidates)]
        request = RerankRequest(query=query, passages=passages)
        results = self._ranker.rerank(request)

        reranked = []
        for r in results[:top_k]:
            original = candidates[r["id"]]
            reranked.append(
                RetrievedChunk(
                    content=original.content,
                    file_path=original.file_path,
                    start_line=original.start_line,
                    end_line=original.end_line,
                    file_type=original.file_type,
                    score=r["score"],
                )
            )
        return reranked

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _scroll_all_payloads(self) -> List[dict]:
        """Fetch every point payload from Qdrant to build the BM25 corpus."""
        all_payloads = []
        next_offset = None
        try:
            while True:
                records, next_offset = self.client.scroll(
                    collection_name=settings.collection_name,
                    limit=256,
                    offset=next_offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for r in records:
                    all_payloads.append(r.payload or {})
                if next_offset is None:
                    break
            return all_payloads
        except Exception as e:
            raise VectorDBUnavailableError(f"Failed to scroll Qdrant payloads: {str(e)}") from e

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Code-aware tokenizer: splits camelCase, snake_case, dots, slashes."""
        # Split on non-alphanumeric first
        tokens = re.split(r'[^a-zA-Z0-9]+', text)
        expanded = []
        for token in tokens:
            if not token:
                continue
            # Split camelCase: getUserProfile → get, User, Profile
            parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', token).split()
            expanded.extend(p.lower() for p in parts if p)
        return expanded



# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke-test:  uv run python -m src.retrieval.retriever "your query"
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_query = (
        sys.argv[1] if len(sys.argv) > 1 else "Where is authentication implemented?"
    )
    print(f"\nSearching for: {test_query}\n")
    retriever = Retriever(rerank=True)

    chunks = retriever.retrieve(test_query, top_k=5)

    for i, c in enumerate(chunks):
        print(f"[{i+1}] Score: {c.score:.4f} | Citation: {c.citation}")
        print(f"    Type: {c.file_type}")
        print(f"    Snippet: {c.content.strip()[:120]}...\n")
