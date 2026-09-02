import sys
from dataclasses import dataclass
from typing import List
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from src.config import settings

@dataclass
class RetrievedChunk:
    content:str
    file_path:str
    start_line:int
    end_line:int
    file_type:str
    score:float

    @property
    def citation(self) -> str:
        return f"{self.file_path}#L{self.start_line}-L{self.end_line}"


class Retriever:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.embedding_model = TextEmbedding(model_name=settings.embedding_model)

    def retrieve(self, query:str, top_k:int=5) -> List[RetrievedChunk]:
        query_vector = list(self.embedding_model.embed(query))[0].tolist()

        results = self.client.query_points(
            collection_name=settings.collection_name,
            query=query_vector,
            limit=top_k
        )
        retrieved_chunks:List[RetrievedChunk] = []
        for point in results.points:
            payload = point.payload or {}
            retrieved_chunks.append(
                RetrievedChunk(
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    file_type=payload.get("file_type", ""),
                    score=point.score
                )
            )
        return retrieved_chunks

if __name__ == "__main__":
    test_query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Where is authentication implemented?"
    )
    print(f"\nSearching for: {test_query}\n")
    retriever = Retriever()

    chunks = retriever.retrieve(test_query, top_k=5)

    for i, c in enumerate(chunks):
        print(f"[{i+1}] Score: {c.score:.4f} | Citation: {c.citation}")
        print(f"    Type: {c.file_type}")
        print(f"    Snippet: {c.content.strip()[:120]}...\n")
