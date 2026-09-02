import time
from pathlib import Path
from typing import List
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from src.config import settings
from src.ingestion.chunker import CodeAwareChunker, CodeChunk

IGNORE_DIRS = {
    "node_modules",
    ".next",
    ".git",
    "dist",
    "build",
    "backup",
    "public",
    ".vscode",
    ".husky",
}

ALLOWED_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".md",
    ".prisma",
    ".json",
    ".yml",
    ".yaml",
    ".sql",
}

IGNORE_FILES = {"pnpm-lock.yaml", "package-lock.json", "yarn.lock"}

BATCH_SIZE = 128


class IngestionPipeline:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.chunker = CodeAwareChunker()
        self.embedding_model = TextEmbedding(model_name=settings.embedding_model)

    def init_collection(self, recreate: bool = False):
        collections = [c.name for c in self.client.get_collections().collections]
        if settings.collection_name in collections and recreate:
            print(f"Recreating connection '{settings.collection_name}'...")
            self.client.delete_collection(collection_name=settings.collection_name)
            collections.remove(settings.collection_name)


        if settings.collection_name not in collections:
            print(f"Creating collection '{settings.collection_name}' ({settings.embedding_dim} dim, Cosine)...")
            self.client.create_collection(
                collection_name=settings.collection_name,
                vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
            )

    def scan_files(self, base_dir:Path) -> List[Path]:
        files_to_process = []
        for p in base_dir.rglob("*"):
            if p.is_file():
                if any(part in IGNORE_DIRS for part in p.parts):
                    continue
                if p.name in IGNORE_FILES:
                    continue
                if p.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue
                files_to_process.append(p)
        return files_to_process


    def run(self, recreate: bool = False):
        start_time = time.time()
        self.init_collection(recreate=recreate)

        corpus_path = settings.corpus_path
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus directory not found at {corpus_path}")

        files = self.scan_files(corpus_path)
        print(f"Found {len(files)} files to ingest from {corpus_path}")

        all_chunks:List[CodeChunk] = []
        for file_path in files:
            rel_path = str(file_path.relative_to(corpus_path))
            chunks = self.chunker.chunk_file(file_path, rel_path)
            all_chunks.extend(chunks)

        print(f"Generated {len(all_chunks)} total chunks. Generating embeddings...")

        bath_size = BATCH_SIZE
        total_batches = (len(all_chunks) + bath_size - 1) // bath_size
        point_id = 0
        for b_idx in range(total_batches):
            batch = all_chunks[b_idx * bath_size : (b_idx + 1) * bath_size]
            texts = [c.content for c in batch]

            embeddings = list(self.embedding_model.embed(texts))

            points = []

            for  chunk, emb in zip(batch, embeddings):
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=emb.tolist(),
                        payload={
                            "content": chunk.content,
                            "file_path": chunk.file_path,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "file_type": chunk.file_type,
                            "chunk_index": chunk.chunk_index,
                        },
                    )
                )
                point_id += 1
            self.client.upsert(
                collection_name=settings.collection_name,
                points=points,
            )
            print(f"Upserted batch {b_idx + 1}/{total_batches} ({len(points)} points)")
        elapsed = time.time() - start_time
        print(f"\nIngestion Complete! Ingested {len(all_chunks)} chunks across {len(files)} files in {elapsed:.2f}s.")

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run(recreate=True)