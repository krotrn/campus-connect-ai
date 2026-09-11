import hashlib
import logging
import time
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from tqdm import tqdm

from src.config import settings
from src.ingestion.chunker import CodeAwareChunker, CodeChunk
from src.ingestion.embedding_cache import EmbeddingCache, content_hash

logger = logging.getLogger(__name__)

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


def _point_id(file_path: str, chunk_index: int) -> int:
    """Deterministic Qdrant point ID from (file_path, chunk_index).

    Uses a stable hash so that re-chunking the same logical location
    produces the same point ID, enabling idempotent upserts.
    """
    raw = hashlib.sha256(f"{file_path}::{chunk_index}".encode()).hexdigest()
    # Qdrant accepts unsigned 64-bit int IDs (0 .. 2^63-1 for signed compat)
    return int(raw[:15], 16)


class IngestionPipeline:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            check_compatibility=False,
            timeout=settings.qdrant_timeout,
        )
        self.chunker = CodeAwareChunker()
        self.embedding_model = TextEmbedding(model_name=settings.embedding_model)
        self.cache = EmbeddingCache()

    def init_collection(self, recreate: bool = False):
        collections = [c.name for c in self.client.get_collections().collections]
        if settings.collection_name in collections and recreate:
            logger.info("Recreating collection '%s'...", settings.collection_name)
            self.client.delete_collection(collection_name=settings.collection_name)
            collections.remove(settings.collection_name)

        if settings.collection_name not in collections:
            logger.info(
                "Creating collection '%s' (%d dim, Cosine)...",
                settings.collection_name,
                settings.embedding_dim,
            )
            self.client.create_collection(
                collection_name=settings.collection_name,
                vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
            )

    def scan_files(self, base_dir: Path) -> list[Path]:
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

    @staticmethod
    def _is_ingestable(rel_path: str) -> bool:
        """Check whether a relative path passes extension / ignore filters."""
        p = Path(rel_path)
        if any(part in IGNORE_DIRS for part in p.parts):
            return False
        if p.name in IGNORE_FILES:
            return False
        if p.suffix.lower() not in ALLOWED_EXTENSIONS and p.name not in ALLOWED_FILENAMES:
            return False
        return True

    def _get_embeddings(self, chunks: list[CodeChunk]) -> list[list[float]]:
        """
        Return embeddings for all chunks, using cache where possible.
        Only computes new embeddings for chunks not in the cache.
        """
        embeddings: list[list[float] | None] = [None] * len(chunks)
        hashes = [content_hash(c.content) for c in chunks]
        cached = self.cache.get_many(hashes)

        to_embed: list[tuple[int, str]] = []  # (index, content)
        for i, chunk in enumerate(chunks):
            hit = cached.get(hashes[i])
            if hit is not None:
                embeddings[i] = hit
            else:
                to_embed.append((i, chunk.content))

        logger.info("Embedding cache: %d hits, %d misses", len(chunks) - len(to_embed), len(to_embed))

        if not to_embed:
            return embeddings  # type: ignore[return-value]

        # Embed only the misses, in batches
        texts = [t[1] for t in to_embed]
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

        with tqdm(total=len(to_embed), desc="Computing embeddings", unit="chunk") as pbar:
            for b_idx in range(total_batches):
                batch_texts = texts[b_idx * BATCH_SIZE : (b_idx + 1) * BATCH_SIZE]
                batch_embeddings = list(self.embedding_model.embed(batch_texts))

                new_entries = []
                for j, emb in enumerate(batch_embeddings):
                    global_j = b_idx * BATCH_SIZE + j
                    orig_idx = to_embed[global_j][0]
                    emb_list = emb.tolist()

                    embeddings[orig_idx] = emb_list
                    new_entries.append((hashes[orig_idx], emb_list))

                # Commit each batch so an interrupted run keeps its progress.
                self.cache.put_many(new_entries)
                pbar.update(len(batch_texts))

        return embeddings  # type: ignore[return-value]

    # ─────────────────────────────────────────────────────────────────────────
    # Qdrant point maintenance
    # ─────────────────────────────────────────────────────────────────────────

    def _scroll_point_keys(self) -> list[tuple[int, str, int]]:
        """Return (point_id, file_path, chunk_index) for every indexed point."""
        keys: list[tuple[int, str, int]] = []
        next_offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=settings.collection_name,
                limit=512,
                offset=next_offset,
                with_payload=["file_path", "chunk_index"],
                with_vectors=False,
            )
            for r in records:
                payload = r.payload or {}
                keys.append((r.id, payload.get("file_path", ""), payload.get("chunk_index", -1)))
            if next_offset is None:
                break
        return keys

    def _prune_stale_points(self, live_chunks: list[CodeChunk]) -> int:
        """Delete indexed points that no longer correspond to a current chunk.

        Covers both files deleted from the corpus and files that now produce
        fewer chunks than before — neither of which an upsert-only pass removes.
        """
        live_keys = {(c.file_path, c.chunk_index) for c in live_chunks}
        stale_ids = [
            point_id
            for point_id, file_path, chunk_index in self._scroll_point_keys()
            if (file_path, chunk_index) not in live_keys
        ]

        if stale_ids:
            logger.info("Pruning %d stale points (deleted or re-chunked files).", len(stale_ids))
            self.client.delete(
                collection_name=settings.collection_name,
                points_selector=stale_ids,
            )
        return len(stale_ids)

    def _delete_points_for_file(self, rel_path: str) -> int:
        """Delete all Qdrant points whose ``file_path`` payload matches *rel_path*.

        Returns the number of points deleted.
        """
        ids_to_delete: list[int] = []
        next_offset = None
        while True:
            records, next_offset = self.client.scroll(
                collection_name=settings.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="file_path", match=MatchValue(value=rel_path))]
                ),
                limit=256,
                offset=next_offset,
                with_payload=False,
                with_vectors=False,
            )
            ids_to_delete.extend(r.id for r in records)
            if next_offset is None:
                break

        if ids_to_delete:
            self.client.delete(
                collection_name=settings.collection_name,
                points_selector=ids_to_delete,
            )
        return len(ids_to_delete)

    def _upsert_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]]):
        """Upsert chunks with deterministic point IDs."""
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        with tqdm(total=len(chunks), desc="Uploading to Qdrant", unit="chunk") as pbar:
            for b_idx in range(total_batches):
                batch_start = b_idx * BATCH_SIZE
                batch_end = min(batch_start + BATCH_SIZE, len(chunks))
                batch_chunks = chunks[batch_start:batch_end]
                batch_embeddings = embeddings[batch_start:batch_end]

                points = []
                for chunk, emb in zip(batch_chunks, batch_embeddings):
                    points.append(
                        PointStruct(
                            id=_point_id(chunk.file_path, chunk.chunk_index),
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
                self.client.upsert(
                    collection_name=settings.collection_name,
                    points=points,
                )
                pbar.update(len(points))

    # ─────────────────────────────────────────────────────────────────────────
    # Full (re)ingestion
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, recreate: bool = False):
        """Re-index the whole corpus.

        With ``recreate=False`` (the default) this is a non-destructive sync:
        every chunk is upserted under its deterministic point ID and only then
        are stale points pruned.  The collection stays queryable throughout, so
        a re-ingest no longer blanks out ``/ask`` for its duration.

        ``recreate=True`` drops the collection first.  That means downtime, so
        reserve it for schema changes (e.g. a different embedding dimension).
        """
        start_time = time.time()
        self.init_collection(recreate=recreate)

        corpus_path = settings.corpus_path
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus directory not found at {corpus_path}")

        files = self.scan_files(corpus_path)
        logger.info("Found %d files to ingest from %s", len(files), corpus_path)

        all_chunks: list[CodeChunk] = []
        for file_path in tqdm(files, desc="Parsing files", unit="file"):
            rel_path = str(file_path.relative_to(corpus_path))
            chunks = self.chunker.chunk_file(file_path, rel_path)
            all_chunks.extend(chunks)

        logger.info("Generated %d total chunks. Resolving embeddings...", len(all_chunks))

        all_embeddings = self._get_embeddings(all_chunks)

        # Upsert first, prune second: the collection never has a window where
        # current content is missing.
        self._upsert_chunks(all_chunks, all_embeddings)
        pruned = 0 if recreate else self._prune_stale_points(all_chunks)

        self.cache.save()

        elapsed = time.time() - start_time
        logger.info(
            "Ingestion complete: %d chunks across %d files in %.2fs (%d stale points pruned).",
            len(all_chunks),
            len(files),
            elapsed,
            pruned,
        )
        return {"files": len(files), "chunks": len(all_chunks), "pruned_points": pruned}

    # ─────────────────────────────────────────────────────────────────────────
    # Incremental (delta-only) ingestion
    # ─────────────────────────────────────────────────────────────────────────

    def run_incremental(self, changed_files: list[str]) -> dict:
        """Re-index only the files that changed.

        For each file in *changed_files*:
          1. Delete all existing Qdrant points for that file path.
          2. If the file still exists on disk, re-chunk and upsert.
          3. If the file was deleted, just the deletion above is sufficient.

        Returns ``{"files": N, "chunks": M, "deleted_points": D}``.
        """
        start_time = time.time()
        self.init_collection(recreate=False)

        corpus_path = settings.corpus_path
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus directory not found at {corpus_path}")

        total_deleted = 0
        all_chunks: list[CodeChunk] = []

        for rel_path in changed_files:
            if not self._is_ingestable(rel_path):
                continue

            # 1. Remove stale points for this file
            deleted = self._delete_points_for_file(rel_path)
            total_deleted += deleted

            # 2. Re-chunk if the file still exists
            abs_path = corpus_path / rel_path
            if abs_path.is_file():
                chunks = self.chunker.chunk_file(abs_path, rel_path)
                all_chunks.extend(chunks)

        if all_chunks:
            logger.info(
                "Re-chunking %d chunks from %d changed files...", len(all_chunks), len(changed_files)
            )
            embeddings = self._get_embeddings(all_chunks)
            self._upsert_chunks(all_chunks, embeddings)

        self.cache.save()

        elapsed = time.time() - start_time
        logger.info(
            "Incremental ingestion done in %.2fs: %d files touched, %d stale points removed, "
            "%d chunks upserted.",
            elapsed,
            len(changed_files),
            total_deleted,
            len(all_chunks),
        )
        return {
            "files": len(changed_files),
            "chunks": len(all_chunks),
            "deleted_points": total_deleted,
        }


if __name__ == "__main__":
    import argparse

    from src.logging_config import configure_logging

    configure_logging()

    parser = argparse.ArgumentParser(description="Ingest the target corpus into Qdrant.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and rebuild the collection (causes query downtime; needed for schema changes).",
    )
    args = parser.parse_args()

    pipeline = IngestionPipeline()
    pipeline.run(recreate=args.recreate)
