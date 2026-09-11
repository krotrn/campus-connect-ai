import logging
import sys
from collections.abc import Iterator
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from src.config import settings
from src.errors import LLMQuotaExceededError
from src.retrieval.retriever import RetrievedChunk, Retriever

logger = logging.getLogger(__name__)

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

TOOL_SYNTHESIS_PROMPT = """You are an expert AI Engineering Intelligence Assistant analyzing the
Campus Connect codebase.

You are given raw output from a read-only repository inspection tool (git log, git show, or an
import-dependency scan) together with the engineer's question.

RULES:
1. Answer using ONLY the tool output provided. Never invent commits, files, authors, or dates.
2. Be specific: name the actual commit hashes, file paths, and modules that appear in the output.
3. If the tool output does not answer the question, say so plainly.
4. Keep it concise — a short paragraph or a tight list, not an essay.
"""

NO_KEY_NOTICE = (
    "⚠️ **Notice**: `GEMINI_API_KEY` is not configured. "
    "To enable AI generation, obtain a free API key from https://aistudio.google.com/. "
    "Displaying retrieved codebase citations directly below."
)


def _status_code(error: Exception) -> int | None:
    """Best-effort HTTP status extraction from a google-genai error."""
    if isinstance(error, APIError):
        code = getattr(error, "code", None)
        if isinstance(code, int):
            return code
    return None


def is_quota_error(error: Exception) -> bool:
    """True when the upstream refused because of rate limits or quota."""
    if _status_code(error) == 429:
        return True
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def is_retryable(error: Exception) -> bool:
    """Whether falling back to another model could plausibly succeed.

    Quota (429) and upstream availability (5xx) errors are worth retrying on a
    different model.  Other 4xx responses — an invalid API key, a malformed
    request — will fail identically on every model, so retrying only wastes
    round trips and hides the real cause.
    """
    if is_quota_error(error):
        return True
    code = _status_code(error)
    if code is None:
        # Network/transport errors surface without a status; a retry is cheap.
        return True
    return code >= 500


class SourceCitation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    citation: str
    content: str | None = None
    score: float | None = None


class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceCitation]
    model_used: str | None = None


class AnswerGenerator:
    """
    Synthesizes grounded engineering answers from retrieved codebase chunks
    using Google Gemini with citation-enforcing prompts.
    """

    def __init__(self, model_name: str | None = None, raise_on_quota: bool = False):
        if not settings.has_gemini_key:
            logger.warning("GEMINI_API_KEY is not set. Generator will operate in degradation mode.")
            self.client = None
        else:
            self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = model_name or settings.gemini_model
        self.raise_on_quota = raise_on_quota

    @property
    def model_candidates(self) -> list[str]:
        """Preferred model first, then the configured fallbacks."""
        ordered = [self.model_name, *settings.gemini_fallback_models]
        seen: set[str] = set()
        return [m for m in ordered if m and not (m in seen or seen.add(m))]

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt assembly
    # ─────────────────────────────────────────────────────────────────────────

    def _build_context_block(self, chunks: list[RetrievedChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks):
            parts.append(
                f"--- CHUNK {i+1}: [{chunk.citation}] (Type: {chunk.file_type}) ---\n"
                f"{chunk.content}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _build_history_block(history: list[Any] | None) -> str:
        if not history:
            return ""
        history_lines = []
        for msg in history[-4:]:
            role = "User" if getattr(msg, "role", "") == "user" else "Assistant"
            content = getattr(msg, "content", "")
            truncated = content[:250] + "..." if len(content) > 250 else content
            history_lines.append(f"{role}: {truncated}")
        return "Prior Conversation Context:\n" + "\n".join(history_lines) + "\n\n"

    def _build_user_prompt(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[Any] | None,
    ) -> str:
        return (
            f"{self._build_history_block(history)}"
            f"Context from codebase:\n"
            f"{self._build_context_block(chunks)}\n\n"
            f"Question: {question}\n\n"
            f"Answer with citations:"
        )

    @staticmethod
    def _generation_config() -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def _resolve_client(self, api_key: str | None = None) -> tuple[genai.Client | None, bool]:
        """
        Resolve the Google GenAI client to use.
        If an explicit api_key is provided from the client, instantiate a dedicated client for it.
        Otherwise, fall back to self.client configured from server environment settings.
        Returns: (client, is_custom_key)
        """
        clean_key = (api_key or "").strip()
        if clean_key and clean_key != "your_gemini_api_key_here":
            return genai.Client(api_key=clean_key), True
        return self.client, False

    @staticmethod
    def _to_sources(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
        return [
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

    # ─────────────────────────────────────────────────────────────────────────
    # Degraded fallbacks
    # ─────────────────────────────────────────────────────────────────────────

    def _degraded_answer(self, chunks: list[RetrievedChunk], last_error: Exception) -> str:
        """Answer text to show when every model candidate failed."""
        if is_quota_error(last_error):
            if self.raise_on_quota:
                raise LLMQuotaExceededError(f"Gemini API quota exhausted: {last_error}")
            return (
                "⚠️ **Upstream AI Quota Exceeded (HTTP 429)**: "
                "The Gemini generation quota has been temporarily reached. "
                "Below are the exact grounded context chunks retrieved for your question:\n\n"
                + "\n\n".join(
                    f"**Source: `{c.citation}`** ({c.file_type})\n```\n{c.content[:250].strip()}...\n```"
                    for c in chunks[:3]
                )
            )
        return (
            f"⚠️ **AI Service Warning**: An upstream model error occurred ({type(last_error).__name__}). "
            f"Showing retrieved source references directly below."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[Any] | None = None,
        api_key: str | None = None,
    ) -> AnswerResponse:
        sources = self._to_sources(chunks)

        client, _ = self._resolve_client(api_key)
        if not client:
            return AnswerResponse(question=question, answer=NO_KEY_NOTICE, sources=sources)

        user_prompt = self._build_user_prompt(question, chunks, history)

        answer_text = ""
        model_used: str | None = None
        last_error: Exception | None = None

        for model in self.model_candidates:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=self._generation_config(),
                )
                if response and response.text:
                    answer_text = response.text
                    model_used = model
                    break
                logger.warning("Model %s returned an empty response; trying next candidate.", model)
            except Exception as e:
                last_error = e
                if not is_retryable(e):
                    logger.error("Model %s failed with a non-retryable error: %s", model, e)
                    break
                logger.warning("Model %s failed (%s); trying next candidate.", model, e)

        if not answer_text and last_error is not None:
            logger.error("All model candidates failed. Last error: %s", last_error, exc_info=True)
            answer_text = self._degraded_answer(chunks, last_error)

        return AnswerResponse(
            question=question,
            answer=answer_text,
            sources=sources,
            model_used=model_used,
        )

    def generate_from_tool_output(
        self,
        question: str,
        tool_output: str,
        route: str,
        api_key: str | None = None,
    ) -> str:
        """Turn raw repository-tool output into a natural-language answer.

        The git and dependency tools emit machine output (a diffstat, a log,
        a file list).  Passing it through the model produces an actual answer
        to the question instead of a dump the reader has to interpret.
        Falls back to the raw output if no model is available.
        """
        raw_block = f"```text\n{tool_output}\n```"

        client, _ = self._resolve_client(api_key)
        if not client or not tool_output.strip():
            return raw_block

        prompt = (
            f"A repository inspection tool (route: {route}) produced the following output "
            f"for the engineer's question.\n\n"
            f"Tool output:\n{raw_block}\n\n"
            f"Question: {question}\n\n"
            f"Answer the question directly from this tool output. Summarize what it shows in "
            f"prose, name the specific commits, files, or modules involved, and do not invent "
            f"anything absent from the output. Finish with the raw tool output in a fenced "
            f"`text` block so the engineer can verify it."
        )

        last_error: Exception | None = None
        for model in self.model_candidates:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=TOOL_SYNTHESIS_PROMPT,
                        temperature=0.1,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                if not is_retryable(e):
                    break
                logger.warning("Tool synthesis via %s failed (%s); trying next candidate.", model, e)

        if last_error is not None:
            logger.warning("Tool synthesis fell back to raw output: %s", last_error)
        return raw_block

    def generate_stream(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[Any] | None = None,
        api_key: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Stream generated answer tokens in real-time using Chat.send_message_stream.
        Yields events:
          - {'type': 'sources', 'sources': [...]} (immediate retrieval citations)
          - {'type': 'token', 'text': '...'} (streamed tokens)
          - {'type': 'done', 'answer': '...', 'model': '...'} (completion marker)
        """
        sources = self._to_sources(chunks)
        # 1. Yield retrieved citations immediately (~35ms)
        yield {"type": "sources", "sources": [s.model_dump() for s in sources]}

        client, _ = self._resolve_client(api_key)
        if not client:
            yield {"type": "token", "text": NO_KEY_NOTICE}
            yield {"type": "done", "answer": NO_KEY_NOTICE, "model": None}
            return

        user_prompt = self._build_user_prompt(question, chunks, history)

        full_text_chunks: list[str] = []
        model_used: str | None = None
        last_error: Exception | None = None

        for model in self.model_candidates:
            try:
                # Use official Chat.send_message_stream as recommended by Google GenAI SDK
                chat = client.chats.create(model=model, config=self._generation_config())
                stream = chat.send_message_stream(user_prompt)
                for response_chunk in stream:
                    if response_chunk and response_chunk.text:
                        full_text_chunks.append(response_chunk.text)
                        yield {"type": "token", "text": response_chunk.text}
                if full_text_chunks:
                    model_used = model
                    break
                logger.warning("Model %s streamed no tokens; trying next candidate.", model)
            except Exception as e:
                last_error = e
                if full_text_chunks:
                    # Tokens already reached the client; a different model would
                    # restart mid-answer, so stop here with what we have.
                    logger.warning("Stream from %s interrupted after partial output: %s", model, e)
                    model_used = model
                    break
                if not is_retryable(e):
                    logger.error("Model %s failed with a non-retryable error: %s", model, e)
                    break
                logger.warning("Model %s failed (%s); trying next candidate.", model, e)

        if not full_text_chunks and last_error is not None:
            logger.error("All streaming candidates failed. Last error: %s", last_error, exc_info=True)
            fallback = self._degraded_answer(chunks, last_error)
            yield {"type": "token", "text": fallback}
            full_text_chunks.append(fallback)

        yield {"type": "done", "answer": "".join(full_text_chunks), "model": model_used}


if __name__ == "__main__":
    from src.logging_config import configure_logging

    configure_logging()

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
