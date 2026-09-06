import sys
from typing import Any, Dict, Iterator, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.config import settings
from src.errors import LLMQuotaExceededError
from src.retrieval.retriever import RetrievedChunk, Retriever

SYSTEM_PROMPT = """You are an expert AI Engineering Intelligence Assistant analyzing the Campus Connect codebase.

Your mission is to answer engineering questions accurately, concisely, and strictly grounded in the
provided code/docs chunks.

RULES:
1. Base your answer ONLY on the provided context chunks.
2. For every claim, architectural fact, or code location, cite the source using the exact format:
   `[filepath#Lstart-Lend]`.
3. If the provided context does not contain enough information to answer the question, clearly state:
   "I cannot find sufficient information in the codebase to answer this question."
   Do NOT hallucinate non-existent files or functions.
4. Provide actionable, technical explanations with relevant code references.
"""


class SourceCitation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    citation: str
    content: Optional[str] = None
    score: Optional[float] = None


class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceCitation]


class AnswerGenerator:
    """
    Synthesizes grounded engineering answers from retrieved codebase chunks
    using Google Gemini with citation-enforcing prompts.
    """

    def __init__(self, model_name: str = "gemini-3.6-flash", raise_on_quota: bool = False):
        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            print("⚠️  Warning: GEMINI_API_KEY is not set. Generator will operate in degradation mode.")
            self.client = None
        else:
            self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = model_name
        self.raise_on_quota = raise_on_quota

    def _build_context_block(self, chunks: List[RetrievedChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks):
            parts.append(
                f"--- CHUNK {i+1}: [{chunk.citation}] (Type: {chunk.file_type}) ---\n"
                f"{chunk.content}\n"
            )
        return "\n".join(parts)

    def generate(
        self,
        question: str,
        chunks: List[RetrievedChunk],
        history: Optional[List[Any]] = None,
    ) -> AnswerResponse:
        sources = [
            SourceCitation(
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                citation=c.citation,
                content=c.content,
                score=c.score,
            )
            for c in chunks
        ]

        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            return AnswerResponse(
                question=question,
                answer=(
                    "⚠️ **Notice**: `GEMINI_API_KEY` is not configured in `.env`. "
                    "To enable AI generation, obtain a free API key from https://aistudio.google.com/. "
                    "Displaying retrieved codebase citations directly below."
                ),
                sources=sources,
            )

        context_str = self._build_context_block(chunks)
        history_str = ""
        if history:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if getattr(msg, "role", "") == "user" else "Assistant"
                content = getattr(msg, "content", "")
                truncated = content[:250] + "..." if len(content) > 250 else content
                history_lines.append(f"{role}: {truncated}")
            history_str = "Prior Conversation Context:\n" + "\n".join(history_lines) + "\n\n"

        user_prompt = (
            f"{history_str}"
            f"Context from codebase:\n"
            f"{context_str}\n\n"
            f"Question: {question}\n\n"
            f"Answer with citations:"
        )

        answer_text = ""
        last_error = None
        for model in [self.model_name, "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                if response and response.text:
                    answer_text = response.text
                    break
            except Exception as e:
                last_error = e
                # If 429 quota or connection error, try next candidate model
                continue

        # If all LLM candidates failed, provide graceful degraded fallback instead of crashing
        if not answer_text and last_error:
            err_str = str(last_error)
            is_quota = "RESOURCE_EXHAUSTED" in err_str or "429" in err_str
            if is_quota and self.raise_on_quota:
                raise LLMQuotaExceededError(f"Gemini API quota exhausted: {err_str}")

            if is_quota:
                answer_text = (
                    "⚠️ **Upstream AI Quota Exceeded (HTTP 429)**: "
                    "The Gemini generation quota has been temporarily reached. "
                    "Below are the exact grounded context chunks retrieved for your question:\n\n"
                    + "\n\n".join(
                        f"**Source: `{c.citation}`** ({c.file_type})\n```\n{c.content[:250].strip()}...\n```"
                        for c in chunks[:3]
                    )
                )
            else:
                answer_text = (
                    f"⚠️ **AI Service Warning**: An upstream model error occurred ({type(last_error).__name__}). "
                    f"Showing retrieved source references directly below."
                )

        return AnswerResponse(
            question=question,
            answer=answer_text,
            sources=sources,
        )

    def generate_stream(
        self,
        question: str,
        chunks: List[RetrievedChunk],
        history: Optional[List[Any]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream generated answer tokens in real-time using Chat.send_message_stream.
        Yields events:
          - {'type': 'sources', 'sources': [...]} (immediate retrieval citations)
          - {'type': 'token', 'text': '...'} (streamed tokens)
          - {'type': 'done', 'answer': '...'} (completion marker)
        """
        sources = [
            SourceCitation(
                file_path=c.file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                citation=c.citation,
                content=c.content,
                score=c.score,
            )
            for c in chunks
        ]
        # 1. Yield retrieved citations immediately (~35ms)
        yield {"type": "sources", "sources": [s.model_dump() for s in sources]}

        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here" or not self.client:
            notice = (
                "⚠️ **Notice**: `GEMINI_API_KEY` is not configured in `.env`. "
                "To enable AI generation, obtain a free API key from https://aistudio.google.com/. "
                "Displaying retrieved codebase citations directly below."
            )
            yield {"type": "token", "text": notice}
            yield {"type": "done", "answer": notice}
            return

        context_str = self._build_context_block(chunks)
        history_str = ""
        if history:
            history_lines = []
            for msg in history[-4:]:
                role = "User" if getattr(msg, "role", "") == "user" else "Assistant"
                content = getattr(msg, "content", "")
                truncated = content[:250] + "..." if len(content) > 250 else content
                history_lines.append(f"{role}: {truncated}")
            history_str = "Prior Conversation Context:\n" + "\n".join(history_lines) + "\n\n"

        user_prompt = (
            f"{history_str}"
            f"Context from codebase:\n"
            f"{context_str}\n\n"
            f"Question: {question}\n\n"
            f"Answer with citations:"
        )

        full_text_chunks = []
        last_error = None

        for model in [self.model_name, "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
            try:
                # Use official Chat.send_message_stream as recommended by Google GenAI SDK
                chat = self.client.chats.create(
                    model=model,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                stream = chat.send_message_stream(user_prompt)
                for response_chunk in stream:
                    if response_chunk and response_chunk.text:
                        full_text_chunks.append(response_chunk.text)
                        yield {"type": "token", "text": response_chunk.text}
                if full_text_chunks:
                    break
            except Exception as e:
                last_error = e
                continue

        if not full_text_chunks and last_error:
            err_str = str(last_error)
            is_quota = "RESOURCE_EXHAUSTED" in err_str or "429" in err_str
            if is_quota and self.raise_on_quota:
                raise LLMQuotaExceededError(f"Gemini API quota exhausted: {err_str}")

            if is_quota:
                fallback = (
                    "⚠️ **Upstream AI Quota Exceeded (HTTP 429)**: "
                    "The Gemini generation quota has been temporarily reached. "
                    "Below are the exact grounded context chunks retrieved for your question:\n\n"
                    + "\n\n".join(
                        f"**Source: `{c.citation}`** ({c.file_type})\n```\n{c.content[:250].strip()}...\n```"
                        for c in chunks[:3]
                    )
                )
            else:
                fallback = (
                    f"⚠️ **AI Service Warning**: An upstream model error occurred ({type(last_error).__name__}). "
                    f"Showing retrieved source references directly below."
                )
            yield {"type": "token", "text": fallback}
            full_text_chunks.append(fallback)

        yield {"type": "done", "answer": "".join(full_text_chunks)}


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "What database models are defined in this project?"
    )
    print(f"\n❓ Question: {query}\n")

    retriever = Retriever()
    chunks = retriever.retrieve(query, top_k=5)

    generator = AnswerGenerator()
    result = generator.generate(query, chunks)

    print("💡 Answer:\n")
    print(result.answer)
    print("\n📚 Sources Retrieved:")
    for s in result.sources:
        print(f"  - {s.citation}")
