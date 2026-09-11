"""Content-addressed embedding cache backed by SQLite.

Embeddings are keyed by the SHA-256 of the chunk content, so re-ingesting an
unchanged file costs a cheap lookup instead of a forward pass.

This replaces an earlier single-JSON-file cache.  That format had to decode the
entire corpus of vectors into Python floats on construction — tens of seconds
and hundreds of megabytes of RAM for a corpus this size — and rewrote the whole
file on every save, so an interrupted write lost the lot.  Here vectors are
stored as float32 blobs, read back only for the hashes actually requested, and
committed per batch.
"""

import hashlib
import logging
import sqlite3
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache")
EMBEDDING_CACHE_DB = CACHE_DIR / "embeddings.sqlite3"
LEGACY_JSON_CACHE = CACHE_DIR / "embedding_cache.json"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    hash TEXT PRIMARY KEY,
    dim  INTEGER NOT NULL,
    vec  BLOB NOT NULL
);
"""


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """SQLite-backed embedding cache keyed by content hash."""

    def __init__(self, cache_path: Path = EMBEDDING_CACHE_DB, migrate_legacy: bool = True):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.cache_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

        if migrate_legacy:
            self._migrate_legacy_json()

        logger.info("Embedding cache ready: %d entries at %s", len(self), self.cache_path)

    # ── Legacy migration ─────────────────────────────────────────────────────

    def _migrate_legacy_json(self):
        """One-time import of the old embedding_cache.json, if present."""
        if not LEGACY_JSON_CACHE.exists() or len(self) > 0:
            return

        import json

        logger.info("Migrating legacy JSON embedding cache (this runs once)...")
        try:
            raw = json.loads(LEGACY_JSON_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Legacy cache unreadable, skipping migration: %s", e)
            return

        self.put_many((h, vec) for h, vec in raw.items() if vec)
        logger.info(
            "Migrated %d embeddings. The legacy file at %s can now be deleted.",
            len(self),
            LEGACY_JSON_CACHE,
        )

    # ── Reads ────────────────────────────────────────────────────────────────

    def get(self, content: str) -> list[float] | None:
        row = self._conn.execute(
            "SELECT vec FROM embeddings WHERE hash = ?", (content_hash(content),)
        ).fetchone()
        return np.frombuffer(row[0], dtype=np.float32).tolist() if row else None

    def get_many(self, hashes: list[str]) -> dict[str, list[float]]:
        """Look up many hashes at once, chunked to stay under SQLite's variable limit."""
        found: dict[str, list[float]] = {}
        batch = 512
        for i in range(0, len(hashes), batch):
            window = hashes[i : i + batch]
            placeholders = ",".join("?" * len(window))
            rows = self._conn.execute(
                f"SELECT hash, vec FROM embeddings WHERE hash IN ({placeholders})", window
            ).fetchall()
            for h, blob in rows:
                found[h] = np.frombuffer(blob, dtype=np.float32).tolist()
        return found

    # ── Writes ───────────────────────────────────────────────────────────────

    def put(self, content: str, embedding: list[float]):
        self.put_many([(content_hash(content), embedding)])

    def put_many(self, items):
        """Insert (hash, embedding) pairs. Existing hashes are left untouched."""
        rows = []
        for h, embedding in items:
            vec = np.asarray(embedding, dtype=np.float32)
            rows.append((h, int(vec.size), vec.tobytes()))
        if not rows:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO embeddings (hash, dim, vec) VALUES (?, ?, ?)", rows
        )
        self._conn.commit()

    def save(self):
        """Kept for API compatibility; writes are committed as they happen."""
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __len__(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
