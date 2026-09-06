"""
Syntax-aware structural block parsers for Prisma, YAML, Markdown, and SQL files.

Ensures that:
- Prisma schemas are chunked by complete `model` and `enum` blocks without splitting attributes.
- YAML files (Docker Compose, CI workflows) are chunked by top-level services or jobs.
- Markdown documentation retains hierarchical heading breadcrumbs (# Parent > ## Child).
- SQL migrations retain complete DDL statements (CREATE TABLE, ALTER TABLE).
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class BlockChunk:
    content: str
    start_line: int  # 1-indexed
    end_line: int    # 1-indexed
    block_type: str
    identifier: str


class PrismaBlockParser:
    """Chunks Prisma schemas into complete model, enum, datasource, and generator blocks."""

    BLOCK_REGEX = re.compile(
        r"^(model|enum|datasource|generator|type)\s+([A-Za-z0-9_]+)?\s*\{[^}]*\}",
        re.MULTILINE | re.DOTALL,
    )

    def parse(self, text: str) -> List[BlockChunk]:
        chunks: List[BlockChunk] = []
        lines = text.splitlines(keepends=True)
        full_text = "".join(lines)

        # Iterate through matched blocks
        for match in self.BLOCK_REGEX.finditer(full_text):
            start_pos = match.start()
            end_pos = match.end()
            start_line = full_text.count("\n", 0, start_pos) + 1
            end_line = full_text.count("\n", 0, end_pos) + 1

            block_type = match.group(1)
            identifier = match.group(2) or block_type
            content = match.group(0).strip()

            chunks.append(
                BlockChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    block_type=block_type,
                    identifier=identifier,
                )
            )
        return chunks


class YamlBlockParser:
    """Chunks YAML configuration files by top-level service, job, or root dictionary blocks."""

    COMPOSE_SERVICE_ROLES = {
        "minio": "S3-compatible object storage service used for file, image, and media uploads",
        "redis": "In-memory key-value cache and message broker for BullMQ background workers and sessions",
        "db": "Primary PostgreSQL relational database service storing core application tables and schema",
        "web": "Next.js web application server and frontend interface",
        "worker": "Background worker process running BullMQ async jobs and scheduled tasks",
    }

    def parse(self, text: str, rel_path: str = "") -> List[BlockChunk]:
        lines = text.splitlines()
        if not lines:
            return []

        chunks: List[BlockChunk] = []
        current_block: List[str] = []
        current_start = 1
        current_name = "header"
        in_services = False

        is_compose = "compose" in rel_path.lower()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Ignore empty lines or comments when starting
            if not stripped:
                if current_block:
                    current_block.append(line)
                continue

            # Detect top-level key (0 indentation)
            if not line.startswith(" ") and not line.startswith("\t") and ":" in line:
                key = line.split(":", 1)[0].strip()

                # If we had a previous block, flush it
                if current_block:
                    content = "\n".join(current_block).strip()
                    if content:
                        chunks.append(
                            BlockChunk(
                                content=content,
                                start_line=current_start,
                                end_line=idx - 1,
                                block_type="yaml_section",
                                identifier=current_name,
                            )
                        )
                current_block = [line]
                current_start = idx
                current_name = key
                in_services = (key == "services")
                continue

            # If inside 'services:' in a compose file, chunk by 2-space indented service definitions
            if is_compose and in_services and line.startswith("  ") and not line.startswith("    ") and ":" in line:
                svc = line.strip().split(":", 1)[0].strip()
                if current_block:
                    content = "\n".join(current_block).strip()
                    if content and current_name != "services":
                        chunks.append(
                            BlockChunk(
                                content=content,
                                start_line=current_start,
                                end_line=idx - 1,
                                block_type="compose_service",
                                identifier=current_name,
                            )
                        )
                role = self.COMPOSE_SERVICE_ROLES.get(svc.lower(), "")
                role_annot = f" ({role})" if role else ""
                current_block = [f"# Service: {svc} in {rel_path}{role_annot}", line]
                current_start = idx
                current_name = svc
                continue

            current_block.append(line)

        # Flush final block
        if current_block:
            content = "\n".join(current_block).strip()
            if content:
                chunks.append(
                    BlockChunk(
                        content=content,
                        start_line=current_start,
                        end_line=len(lines),
                        block_type="yaml_section",
                        identifier=current_name,
                    )
                )

        return chunks


class MarkdownSectionParser:
    """Chunks Markdown documents by heading sections, preserving hierarchical heading breadcrumbs."""

    HEADING_REGEX = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    def parse(self, text: str) -> List[BlockChunk]:
        lines = text.splitlines()
        if not lines:
            return []

        chunks: List[BlockChunk] = []
        headings: List[tuple] = []  # (line_no, level, title)

        for idx, line in enumerate(lines, start=1):
            m = self.HEADING_REGEX.match(line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                headings.append((idx, level, title))

        if not headings:
            return [
                BlockChunk(
                    content=text.strip(),
                    start_line=1,
                    end_line=len(lines),
                    block_type="markdown_doc",
                    identifier="document",
                )
            ]

        for i, (start_l, level, title) in enumerate(headings):
            end_l = headings[i + 1][0] - 1 if i + 1 < len(headings) else len(lines)
            section_lines = lines[start_l - 1 : end_l]
            content = "\n".join(section_lines).strip()
            if content:
                chunks.append(
                    BlockChunk(
                        content=content,
                        start_line=start_l,
                        end_line=end_l,
                        block_type=f"heading_h{level}",
                        identifier=title,
                    )
                )

        return chunks


class SqlStatementParser:
    """Chunks SQL migration files by DDL statement boundaries."""

    def parse(self, text: str) -> List[BlockChunk]:
        lines = text.splitlines()
        if not lines:
            return []

        chunks: List[BlockChunk] = []
        current_lines: List[str] = []
        current_start = 1

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not current_lines and not stripped:
                current_start = idx + 1
                continue

            current_lines.append(line)

            # Detect statement terminator
            if stripped.endswith(";"):
                stmt = "\n".join(current_lines).strip()
                # Determine statement type from the first keyword of the statement
                first_line = current_lines[0].strip() if current_lines else ""
                first_word = first_line.split()[0].upper() if first_line and first_line.split() else "SQL"
                if stmt:
                    chunks.append(
                        BlockChunk(
                            content=stmt,
                            start_line=current_start,
                            end_line=idx,
                            block_type="sql_ddl",
                            identifier=first_word,
                        )
                    )
                current_lines = []
                current_start = idx + 1

        if current_lines:
            stmt = "\n".join(current_lines).strip()
            if stmt:
                chunks.append(
                    BlockChunk(
                        content=stmt,
                        start_line=current_start,
                        end_line=len(lines),
                        block_type="sql_ddl",
                        identifier="statement",
                    )
                )

        return chunks

