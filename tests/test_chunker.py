import tempfile
from pathlib import Path
import pytest
from src.ingestion.chunker import CodeAwareChunker


@pytest.fixture
def chunker():
    return CodeAwareChunker(chunk_size=300, chunk_overlap=50)


def test_chunk_typescript_preserves_lines_and_type(chunker):
    sample_code = """// Authentication module
export interface AuthUser {
    id: string;
    email: string;
}

export function verifySession(token: string): boolean {
    if (!token) {
        return false;
    }
    return token.startsWith("valid_");
}
"""
    with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False) as tmp:
        tmp.write(sample_code)
        tmp_path = Path(tmp.name)

    try:
        chunks = chunker.chunk_file(tmp_path, "src/auth/session.ts")
        assert len(chunks) >= 1
        first = chunks[0]

        assert first.file_path == "src/auth/session.ts"
        assert first.file_type == "code"
        assert first.start_line == 1
        assert first.end_line >= 1
        assert "export" in first.content
    finally:
        tmp_path.unlink(missing_ok=True)


def test_chunk_markdown_file(chunker):
    sample_md = """# Architecture Overview

This is the system architecture documentation.

## Database Layer

The database utilizes PostgreSQL via Prisma.
"""
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tmp:
        tmp.write(sample_md)
        tmp_path = Path(tmp.name)

    try:
        chunks = chunker.chunk_file(tmp_path, "docs/architecture.md")
        assert len(chunks) >= 1
        assert chunks[0].file_type == "markdown"
        assert chunks[0].file_path == "docs/architecture.md"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_chunk_empty_file(chunker):
    with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)

    try:
        chunks = chunker.chunk_file(tmp_path, "empty.ts")
        assert chunks == []
    finally:
        tmp_path.unlink(missing_ok=True)

