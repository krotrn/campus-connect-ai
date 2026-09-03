import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
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

# Dotfiles with no extension that should still be ingested
ALLOWED_FILENAMES = {
    ".env.example",
    ".env.local.example",
    ".env.sample",
}

IGNORE_FILES = {"pnpm-lock.yaml", "package-lock.json", "yarn.lock"}

BATCH_SIZE = 128
CACHE_DIR = Path(".cache")
EMBEDDING_CACHE_FILE = CACHE_DIR / "embedding_cache.json"


class EmbeddingCache:
    """
    Caches embeddings keyed by SHA-256 hash of chunk content.
    On re-ingestion, only chunks with new/changed content are embedded.
    """

    def __init__(self, cache_path: Path = EMBEDDING_CACHE_FILE):
        self.cache_path = cache_path
        self._cache: Dict[str, List[float]] = {}
        self._load()

    def _load(self):
        if self.cache_path.exists():
            try:
                raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
                self._cache = raw
                print(f"📦 Loaded embedding cache: {len(self._cache)} entries")
            except (json.JSONDecodeError, OSError):
                print("⚠️  Cache file corrupted, starting fresh")
                self._cache = {}
        else:
            print("📦 No embedding cache found, will create one after ingestion")

    def save(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache), encoding="utf-8"
        )
        print(f"💾 Saved embedding cache: {len(self._cache)} entries")

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, content: str) -> List[float] | None:
        return self._cache.get(self._hash(content))

    def put(self, content: str, embedding: List[float]):
        self._cache[self._hash(content)] = embedding

    def __len__(self):
        return len(self._cache)


class IngestionPipeline:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.chunker = CodeAwareChunker()
        self.embedding_model = TextEmbedding(model_name=settings.embedding_model)
        self.cache = EmbeddingCache()

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
                if p.suffix.lower() not in ALLOWED_EXTENSIONS and p.name not in ALLOWED_FILENAMES:
                    continue
                files_to_process.append(p)
        return files_to_process

    def _get_embeddings(self, chunks: List[CodeChunk]) -> List[List[float]]:
        """
        Return embeddings for all chunks, using cache where possible.
        Only computes new embeddings for chunks not in the cache.
        """
        embeddings: List[List[float] | None] = [None] * len(chunks)
        to_embed: List[Tuple[int, str]] = []  # (index, content)

        # Check cache first
        cache_hits = 0
        for i, chunk in enumerate(chunks):
            cached = self.cache.get(chunk.content)
            if cached is not None:
                embeddings[i] = cached
                cache_hits += 1
            else:
                to_embed.append((i, chunk.content))

        print(f"   Cache: {cache_hits} hits, {len(to_embed)} misses")

        if not to_embed:
            return embeddings  # type: ignore

        # Embed only the misses, in batches
        texts = [t[1] for t in to_embed]
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

        for b_idx in range(total_batches):
            batch_texts = texts[b_idx * BATCH_SIZE : (b_idx + 1) * BATCH_SIZE]
            batch_embeddings = list(self.embedding_model.embed(batch_texts))

            for j, emb in enumerate(batch_embeddings):
                global_j = b_idx * BATCH_SIZE + j
                orig_idx = to_embed[global_j][0]
                content = to_embed[global_j][1]
                emb_list = emb.tolist()

                embeddings[orig_idx] = emb_list
                self.cache.put(content, emb_list)

            print(f"   Embedded batch {b_idx + 1}/{total_batches} ({len(batch_texts)} chunks)")

        return embeddings  # type: ignore


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

        print(f"Generated {len(all_chunks)} total chunks. Resolving embeddings...")

        # Get embeddings (cached + newly computed)
        all_embeddings = self._get_embeddings(all_chunks)

        # Upload to Qdrant in batches
        total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        point_id = 0
        for b_idx in range(total_batches):
            batch_start = b_idx * BATCH_SIZE
            batch_end = min(batch_start + BATCH_SIZE, len(all_chunks))
            batch_chunks = all_chunks[batch_start:batch_end]
            batch_embeddings = all_embeddings[batch_start:batch_end]

            points = []
            for chunk, emb in zip(batch_chunks, batch_embeddings):
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=emb,
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

        # Save cache after successful ingestion
        self.cache.save()

        elapsed = time.time() - start_time
        print(f"\nIngestion Complete! Ingested {len(all_chunks)} chunks across {len(files)} files in {elapsed:.2f}s.")

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run(recreate=True)