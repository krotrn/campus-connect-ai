from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)

from src.ingestion.ast_chunker import TreeSitterCodeParser
from src.ingestion.block_parsers import (
    MarkdownSectionParser,
    PrismaBlockParser,
    SqlStatementParser,
    YamlBlockParser,
)


@dataclass
class CodeChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    file_type: str
    chunk_index: int


class CodeAwareChunker:
    """Multi-format syntax-aware code and configuration chunker.

    Uses AST and structural block parsers for:
    - TypeScript / TSX: Tree-Sitter AST (functions, classes, interfaces, types)
    - Prisma: Model and Enum block parser
    - YAML: Top-level service/job block parser
    - Markdown: Header-hierarchical section parser
    - SQL: DDL statement-boundary parser

    Falls back to recursive character splitting when files are unparsed or unstructured.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Structural parsers
        self.ast_parser = TreeSitterCodeParser()
        self.prisma_parser = PrismaBlockParser()
        self.yaml_parser = YamlBlockParser()
        self.markdown_parser = MarkdownSectionParser()
        self.sql_parser = SqlStatementParser()

        # Fallback character splitters
        self.ts_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.TS,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        self.md_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        self.generic_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def _find_line_number(self, full_text: str, chunk_text: str, search_from: int = 0):
        """Finds 1-indexed start and end line numbers for a chunk within full_text."""
        idx = full_text.find(chunk_text.strip()[:60], search_from)
        if idx == -1:
            idx = search_from

        start_line = full_text.count("\n", 0, idx) + 1
        end_line = start_line + chunk_text.count("\n")
        next_search = idx + len(chunk_text.strip()[:60])
        return start_line, end_line, next_search

    @staticmethod
    def _build_semantic_prefix(file_path: Path, rel_path: str) -> str:
        """
        Generate a human-readable preamble for config files.

        Embedding models (like BGE-small) understand prose but struggle
        with raw YAML service blocks, SQL DDL, and KEY=VALUE env files.
        Prepending a short natural-language description lets the model
        connect queries like "What depends on Redis?" to a YAML chunk
        that only says `redis: image: redis:8.2.1-alpine`.
        """
        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        # Docker Compose files — describe the infrastructure services defined
        if name.startswith("compose") and ext in (".yml", ".yaml"):
            label = name.replace(".yml", "").replace(".yaml", "")
            return (
                f"# Docker Compose infrastructure definition: {rel_path}\n"
                f"# This file ({label}) defines the services, networks, and volumes\n"
                f"# for the application stack including databases, caches, object storage, and workers.\n\n"
            )

        # SQL migration files
        if ext == ".sql" and "migration" in rel_path.lower():
            migration_dir = file_path.parent.name
            return (
                f"-- Database migration file: {rel_path}\n"
                f"-- Migration: {migration_dir}\n"
                f"-- This SQL migration creates or alters database tables, columns, indexes, and constraints.\n\n"
            )

        # Dotenv files
        if name.startswith(".env"):
            return (
                f"# Environment variables configuration file: {rel_path}\n"
                f"# This file lists all required environment variables for the application.\n\n"
            )

        return ""

    def chunk_file(self, file_path: Path, rel_path: str) -> list[CodeChunk]:
        try:
            full_text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        if not full_text.strip():
            return []

        ext = file_path.suffix.lower()
        prefix = self._build_semantic_prefix(file_path, rel_path)

        # ── 1. TypeScript & TSX: Tree-Sitter AST parser ───────────────────────
        if ext in (".ts", ".tsx"):
            ast_chunks = self.ast_parser.parse(full_text, file_path)
            if ast_chunks:
                return [
                    CodeChunk(
                        content=c.content,
                        file_path=rel_path,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        file_type="code",
                        chunk_index=i,
                    )
                    for i, c in enumerate(ast_chunks)
                ]
            # Fallback to recursive language splitter if AST parser yielded no nodes
            raw_chunks = self.ts_splitter.split_text(full_text)
            file_type = "code"

        # ── 2. Prisma: Model and Enum block parser ────────────────────────────
        elif ext == ".prisma":
            prisma_blocks = self.prisma_parser.parse(full_text)
            if prisma_blocks:
                return [
                    CodeChunk(
                        content=b.content,
                        file_path=rel_path,
                        start_line=b.start_line,
                        end_line=b.end_line,
                        file_type="schema",
                        chunk_index=i,
                    )
                    for i, b in enumerate(prisma_blocks)
                ]
            raw_chunks = self.generic_splitter.split_text(full_text)
            file_type = "schema"

        # ── 3. YAML: Top-level service / job block parser ─────────────────────
        elif ext in (".yml", ".yaml"):
            yaml_blocks = self.yaml_parser.parse(full_text, rel_path)
            if yaml_blocks:
                header_prefix = f"# Infrastructure definition: {rel_path}\n" if "compose" in rel_path.lower() else ""
                return [
                    CodeChunk(
                        content=(prefix + b.content) if (i == 0 and prefix) else (header_prefix + b.content),
                        file_path=rel_path,
                        start_line=b.start_line,
                        end_line=b.end_line,
                        file_type="config",
                        chunk_index=i,
                    )
                    for i, b in enumerate(yaml_blocks)
                ]
            text_to_split = prefix + full_text if prefix else full_text
            raw_chunks = self.generic_splitter.split_text(text_to_split)
            file_type = "config"

        # ── 4. Markdown: Header-hierarchical section parser ───────────────────
        elif ext == ".md":
            md_blocks = self.markdown_parser.parse(full_text)
            if md_blocks:
                return [
                    CodeChunk(
                        content=b.content,
                        file_path=rel_path,
                        start_line=b.start_line,
                        end_line=b.end_line,
                        file_type="markdown",
                        chunk_index=i,
                    )
                    for i, b in enumerate(md_blocks)
                ]
            raw_chunks = self.md_splitter.split_text(full_text)
            file_type = "markdown"

        # ── 5. SQL: DDL statement-boundary parser ────────────────────────────
        elif ext == ".sql":
            sql_blocks = self.sql_parser.parse(full_text)
            if sql_blocks:
                return [
                    CodeChunk(
                        content=(prefix + b.content) if (i == 0 and prefix) else b.content,
                        file_path=rel_path,
                        start_line=b.start_line,
                        end_line=b.end_line,
                        file_type="migration",
                        chunk_index=i,
                    )
                    for i, b in enumerate(sql_blocks)
                ]
            text_to_split = prefix + full_text if prefix else full_text
            raw_chunks = self.generic_splitter.split_text(text_to_split)
            file_type = "migration"

        # ── 6. Generic fallback (e.g. .json, .env) ───────────────────────────
        else:
            text_to_split = prefix + full_text if prefix else full_text
            raw_chunks = self.generic_splitter.split_text(text_to_split)
            file_type = "config"

        # Apply fallback line finding
        # Use the original full_text (without prefix) for line number lookup
        chunks: list[CodeChunk] = []
        search_pos = 0
        for i, text in enumerate(raw_chunks):
            if not text.strip():
                continue
            # Strip the prefix from the chunk text before searching in original file
            search_text = text
            if prefix and text.startswith(prefix):
                search_text = text[len(prefix):]
            start_l, end_l, search_pos = self._find_line_number(full_text, search_text, search_pos)
            chunks.append(
                CodeChunk(
                    content=text,
                    file_path=rel_path,
                    start_line=start_l,
                    end_line=end_l,
                    file_type=file_type,
                    chunk_index=i,
                )
            )
        return chunks
