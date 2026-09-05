"""Tests for syntax-aware structural chunkers (Tree-Sitter, Prisma, YAML, Markdown, SQL)."""

from pathlib import Path
from src.ingestion.ast_chunker import TreeSitterCodeParser
from src.ingestion.block_parsers import (
    MarkdownSectionParser,
    PrismaBlockParser,
    SqlStatementParser,
    YamlBlockParser,
)
from src.ingestion.chunker import CodeAwareChunker


def test_typescript_ast_chunking():
    """Tree-Sitter extracts functions, classes, and interfaces as discrete chunks."""
    ts_code = """
import { Request, Response } from "express";

export interface UserDTO {
  id: string;
  name: string;
  email: string;
}

export class UserService {
  getUser(id: string): UserDTO {
    return { id, name: "Alice", email: "alice@example.com" };
  }
}

export function validateUser(user: UserDTO): boolean {
  return user.email.includes("@");
}
"""
    parser = TreeSitterCodeParser()
    chunks = parser.parse(ts_code, Path("test.ts"))

    assert len(chunks) >= 3
    contents = [c.content for c in chunks]

    # Interface is retained intact
    assert any("interface UserDTO" in c for c in contents)
    # Class is retained intact
    assert any("class UserService" in c for c in contents)
    # Function is retained intact
    assert any("function validateUser" in c for c in contents)

    # Line numbers are accurate
    for c in chunks:
        assert c.start_line > 0
        assert c.end_line >= c.start_line


def test_tsx_ast_chunking():
    """Tree-Sitter parses TSX component definitions."""
    tsx_code = """
import React from "react";

export const Header = () => {
  return <header><h1>Campus Connect</h1></header>;
};

export function Footer() {
  return <footer><p>Footer content</p></footer>;
}
"""
    parser = TreeSitterCodeParser()
    chunks = parser.parse(tsx_code, Path("Header.tsx"))

    assert len(chunks) >= 2
    contents = [c.content for c in chunks]
    assert any("Header" in c for c in contents)
    assert any("Footer" in c for c in contents)


def test_prisma_block_chunking():
    """Prisma parser chunks complete model and enum blocks."""
    prisma_code = """
datasource db {
  provider = "postgresql"
}

enum Role {
  USER
  ADMIN
  VENDOR
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  role      Role     @default(USER)
  createdAt DateTime @default(now())
}

model Order {
  id        String   @id @default(cuid())
  userId    String
  status    String
}
"""
    parser = PrismaBlockParser()
    blocks = parser.parse(prisma_code)

    assert len(blocks) == 4
    identifiers = [b.identifier for b in blocks]
    assert "db" in identifiers
    assert "Role" in identifiers
    assert "User" in identifiers
    assert "Order" in identifiers

    # Verify User model contains all fields
    user_block = next(b for b in blocks if b.identifier == "User")
    assert "createdAt" in user_block.content
    assert "id" in user_block.content
    assert user_block.start_line > 0


def test_yaml_compose_chunking():
    """YAML parser extracts top-level services in Docker Compose files."""
    yaml_code = """
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: campus_connect
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
"""
    parser = YamlBlockParser()
    blocks = parser.parse(yaml_code, rel_path="compose.yml")

    identifiers = [b.identifier for b in blocks]
    assert "postgres" in identifiers
    assert "redis" in identifiers

    # The postgres block should contain all its environment keys
    pg_block = next(b for b in blocks if b.identifier == "postgres")
    assert "POSTGRES_DB: campus_connect" in pg_block.content
    assert "5432:5432" in pg_block.content


def test_markdown_section_chunking():
    """Markdown parser chunks by headings."""
    md_code = """# Campus Connect Architecture

The system uses Next.js and Prisma.

## Database Schema

We use PostgreSQL with row-level security.

## Background Workers

BullMQ processes repeat orders every 15 minutes.
"""
    parser = MarkdownSectionParser()
    blocks = parser.parse(md_code)

    assert len(blocks) == 3
    assert blocks[0].identifier == "Campus Connect Architecture"
    assert blocks[1].identifier == "Database Schema"
    assert blocks[2].identifier == "Background Workers"


def test_sql_statement_chunking():
    """SQL parser chunks complete DDL statements."""
    sql_code = """
-- Drop old index
DROP INDEX IF EXISTS "Product_brand_idx";

-- Create brand table
CREATE TABLE "Brand" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    CONSTRAINT "Brand_pkey" PRIMARY KEY ("id")
);

-- Add index
CREATE INDEX "Brand_name_idx" ON "Brand"("name");
"""
    parser = SqlStatementParser()
    blocks = parser.parse(sql_code)

    assert len(blocks) == 3
    assert any("CREATE TABLE" in b.content for b in blocks)
    assert any("DROP INDEX" in b.content for b in blocks)
    assert any("CREATE INDEX" in b.content for b in blocks)


def test_code_aware_chunker_integration(tmp_path):
    """CodeAwareChunker correctly delegates to appropriate syntax parsers."""
    chunker = CodeAwareChunker()

    # 1. TypeScript file
    ts_file = tmp_path / "service.ts"
    ts_file.write_text("export function computeHash(val: string): string { return val; }")
    ts_chunks = chunker.chunk_file(ts_file, "service.ts")
    assert len(ts_chunks) >= 1
    assert ts_chunks[0].file_type == "code"

    # 2. Prisma file
    prisma_file = tmp_path / "schema.prisma"
    prisma_file.write_text("model Item { id String @id }")
    prisma_chunks = chunker.chunk_file(prisma_file, "schema.prisma")
    assert len(prisma_chunks) >= 1
    assert prisma_chunks[0].file_type == "schema"

    # 3. YAML compose file
    yaml_file = tmp_path / "compose.yml"
    yaml_file.write_text("services:\n  worker:\n    image: node:20\n")
    yaml_chunks = chunker.chunk_file(yaml_file, "compose.yml")
    assert len(yaml_chunks) >= 1
    assert yaml_chunks[0].file_type == "config"

