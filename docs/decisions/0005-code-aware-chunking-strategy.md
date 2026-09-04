# ADR 0005: Code-Aware Chunking Strategy with Exact Line Citations

## Status
Accepted

## Date
2026-09-02

## Context
Standard RAG pipelines often use naive fixed-size chunking (e.g., 500 characters or 256 tokens with arbitrary overlap). When applied to source code, fixed-size chunking breaks functions in half, separates signatures from docstrings and implementations, and obscures semantic scope. Furthermore, to fulfill PRD Goal #1 and Use Case #2 ("Where is authentication implemented?"), the system must provide exact file and line-range citations (`[src/lib/auth.ts#L12-L45]`) rather than arbitrary character offsets.

## Decision
We implement a multi-strategy, language-aware chunker in `src/ingestion/chunker.py`:
1. **TypeScript / TSX (`.ts`, `.tsx`)**:
   - Use language-aware structural splitting (`RecursiveCharacterTextSplitter.from_language(Language.TS)`) which prioritizes splitting on interface, class, function, and export declarations before falling back to statement or line breaks.
   - Calculate exact 1-indexed `start_line` and `end_line` for each chunk by mapping chunk content back to the original source text.
2. **Markdown Documentation (`.md`)**:
   - Split along markdown headers (`#`, `##`, `###`), preserving section titles in chunk metadata so the LLM understands document hierarchy.
3. **Database Schema (`schema.prisma`)**:
   - Split on model, enum, and generator blocks (`model ... { ... }`).
4. **Configuration (`.json`, `.yml`, `.yaml`, `Dockerfile`)**:
   - Kept intact if under max chunk size (1000 tokens), or split cleanly along top-level keys.
5. **Metadata Schema**:
   Every chunk payload in Qdrant stores:
   - `file_path`: relative path within repo (e.g., `src/lib/auth.ts`)
   - `start_line`: integer
   - `end_line`: integer
   - `file_type`: `code` | `markdown` | `schema` | `config`
   - `chunk_index`: integer

```mermaid
flowchart TD
    RawFile["Raw Source File from Corpus"] --> ExtCheck{"File Extension / Path"}

    ExtCheck -->|TypeScript / TSX<br/>.ts, .tsx| TSChunker["RecursiveCharacterTextSplitter<br/>(Language.TS)<br/><i>Splits on classes, interfaces, functions</i>"]
    ExtCheck -->|Markdown<br/>.md| MDChunker["Markdown Header Splitter<br/><i>Splits on #, ##, ### headers</i>"]
    ExtCheck -->|Database Schema<br/>schema.prisma| PrismaChunker["Prisma Schema Splitter<br/><i>Splits on model & enum blocks</i>"]
    ExtCheck -->|Config / YAML / Dotenv<br/>compose*.yml, .env.example, .sql| PrefixChunker["Semantic Prefix Injector<br/><i>Injects natural-language purpose context</i>"]

    TSChunker --> LineTracker["Line Tracker & Citation Resolver<br/><i>Computes exact 1-indexed start_line & end_line</i>"]
    MDChunker --> LineTracker
    PrismaChunker --> LineTracker
    PrefixChunker --> LineTracker

    LineTracker --> ChunkPayload["CodeChunk Object<br/><code>{file_path, start_line, end_line, file_type, content}</code>"]
    ChunkPayload --> Qdrant[("Qdrant Vector DB<br/>(384-dim Dense Vector + Payload)")]

    style RawFile fill:#f0f7ff,stroke:#2563eb,stroke-width:2px
    style ExtCheck fill:#fdf4ff,stroke:#c026d3,stroke-width:2px
    style ChunkPayload fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    style Qdrant fill:#fef3c7,stroke:#d97706,stroke-width:2px
```

## Consequences
- **Positive**: LLM answers can directly cite precise, clickable line ranges (`file.ts#L20-L45`), fulfilling core PRD requirements.
- **Positive**: Code semantics are preserved without needing a heavy compilation step.
- **Negative**: Language-aware heuristics may occasionally produce variable chunk sizes compared to strict fixed-token windows.

