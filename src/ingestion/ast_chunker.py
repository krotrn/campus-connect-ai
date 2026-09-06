"""
AST-aware code chunking for TypeScript and TSX using tree-sitter.

Extracts top-level declarations (functions, classes, interfaces, type aliases,
enums, and exported constants) as discrete semantic chunks without cutting
syntax constructs across arbitrary character boundaries.
"""

import bisect
from dataclasses import dataclass
from pathlib import Path
from typing import List

import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser


@dataclass
class _Span:
    start_byte: int
    end_byte: int


@dataclass
class AstChunk:
    content: str
    start_line: int  # 1-indexed
    end_line: int    # 1-indexed
    node_type: str
    symbol_name: str


class TreeSitterCodeParser:
    """Parser for TypeScript and TSX files using Tree-Sitter AST."""

    # Node types that represent standalone top-level semantic units
    DECLARATION_TYPES = {
        "function_declaration",
        "class_declaration",
        "abstract_class_declaration",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
        "lexical_declaration",
        "variable_declaration",
        "method_definition",
    }

    def __init__(self):
        self._ts_lang = Language(tstypescript.language_typescript())
        self._tsx_lang = Language(tstypescript.language_tsx())

    def _get_parser(self, file_path: Path) -> Parser:
        if file_path.suffix.lower() == ".tsx":
            return Parser(self._tsx_lang)
        return Parser(self._ts_lang)

    @staticmethod
    def _extract_name(node: Node, source_bytes: bytes) -> str:
        """Attempt to extract symbol identifier name from an AST node."""
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "property_identifier"):
                return source_bytes[child.start_byte : child.end_byte].decode("utf-8", errors="ignore")
        return ""

    def _unwrap_export(self, node: Node) -> Node:
        """If node is an export_statement, return the inner declaration if present."""
        if node.type == "export_statement":
            for child in node.children:
                if child.type in self.DECLARATION_TYPES:
                    return child
        return node

    def parse(
        self, text: str, file_path: Path, min_chunk_chars: int = 80, max_chunk_chars: int = 1500
    ) -> List[AstChunk]:
        """Parse TypeScript/TSX source into semantic AST chunks.

        Returns a list of ``AstChunk`` objects with accurate 1-indexed line numbers.
        Adjacent small items (e.g. imports or short constants) are grouped to prevent
        excessive micro-chunks.
        """
        source_bytes = text.encode("utf-8")
        parser = self._get_parser(file_path)
        tree = parser.parse(source_bytes)
        root = tree.root_node

        if not root.children:
            return []

        line_starts = [0]
        for idx, b in enumerate(source_bytes):
            if b == 10:  # ord('\n')
                line_starts.append(idx + 1)

        def get_line_number(byte_offset: int) -> int:
            return bisect.bisect_right(line_starts, byte_offset)

        chunks: List[AstChunk] = []
        pending_spans: List[_Span] = []
        pending_chars = 0

        def flush_pending():
            nonlocal pending_spans, pending_chars
            if not pending_spans:
                return
            first = pending_spans[0]
            last = pending_spans[-1]
            content = source_bytes[first.start_byte : last.end_byte].decode("utf-8", errors="ignore").strip()
            if content:
                chunks.append(
                    AstChunk(
                        content=content,
                        start_line=get_line_number(first.start_byte),
                        end_line=get_line_number(max(first.start_byte, last.end_byte - 1)),
                        node_type="block",
                        symbol_name="",
                    )
                )
            pending_spans = []
            pending_chars = 0

        leading_comments: List[_Span] = []

        for child in root.children:
            if child.type == ";":
                continue
            if child.type == "comment":
                leading_comments.append(_Span(child.start_byte, child.end_byte))
                continue

            unwrapped = self._unwrap_export(child)
            is_declaration = unwrapped.type in self.DECLARATION_TYPES
            node_chars = child.end_byte - child.start_byte

            if is_declaration:
                name = self._extract_name(unwrapped, source_bytes)
                if node_chars >= min_chunk_chars:
                    flush_pending()
                    start_byte = leading_comments[0].start_byte if leading_comments else child.start_byte
                    chunk_text = (
                        source_bytes[start_byte : child.end_byte].decode("utf-8", errors="ignore").strip()
                    )
                    chunks.append(
                        AstChunk(
                            content=chunk_text,
                            start_line=get_line_number(start_byte),
                            end_line=get_line_number(max(start_byte, child.end_byte - 1)),
                            node_type=unwrapped.type,
                            symbol_name=name,
                        )
                    )
                    leading_comments = []
                    continue

            # If not emitted with declaration, bundle leading comments into pending
            if leading_comments:
                pending_spans.extend(leading_comments)
                leading_comments = []

            pending_spans.append(_Span(child.start_byte, child.end_byte))
            pending_chars += node_chars

            if pending_chars >= max_chunk_chars:
                flush_pending()

        if leading_comments:
            pending_spans.extend(leading_comments)
        flush_pending()
        return chunks
