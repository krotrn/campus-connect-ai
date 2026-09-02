from dataclasses import dataclass
from pathlib import Path
from typing import List
from langchain_text_splitters import (
    Language,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

@dataclass
class CodeChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    file_type: str
    chunk_index:int

class CodeAwareChunker:
    def __init__(self, chunk_size:int=800, chunk_overlap:int=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
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

    def _find_line_number(self, full_text:str, chunk_text:str, search_from:int=0):
        """Finds 1-indexed start and end line numbers for a chunk within full_text."""
        idx = full_text.find(chunk_text.strip()[:60], search_from)
        if idx == -1:
            idx = search_from

        start_line = full_text.count("\n", 0, idx) + 1
        end_line = start_line + chunk_text.count("\n")
        next_search = idx + len(chunk_text.strip()[:60])
        return start_line, end_line, next_search

    def chunk_file(self, file_path:Path, rel_path:str) -> List[CodeChunk]:
        try:
            full_text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        if not full_text.strip():
            return []

        ext = file_path.suffix.lower()
        chunks = []

        if ext in [".ts", ".tsx"]:
            raw_chunks = self.ts_splitter.split_text(full_text)
            file_type = "code"
        elif ext == ".md":
            raw_chunks = self.md_splitter.split_text(full_text)
            file_type = "markdown"
        elif ext == ".prisma":
            raw_chunks = self.generic_splitter.split_text(full_text)
            file_type = "schema"
        else:
            raw_chunks = self.generic_splitter.split_text(full_text)
            file_type = "config"

        search_pos = 0

        for i, text in enumerate(raw_chunks):
            if not text.strip():
                continue
            start_l, end_l, search_pos = self._find_line_number(full_text, text, search_pos)
            chunks.append(
                CodeChunk(
                    content=text,
                    file_path=rel_path,
                    start_line=start_l,
                    end_line=end_l,
                    file_type=file_type,
                    chunk_index=i
                )
            )
        return chunks
