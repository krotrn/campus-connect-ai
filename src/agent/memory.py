"""
Multi-turn conversational session memory and coreference query rewriting.

Enables engineers to ask contextual follow-up questions (e.g. "Can you show me its unit test?",
"How does it handle token expiration?") by tracking conversation turns and rewriting follow-ups
into self-contained search queries before retrieval.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from src.config import settings

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are an expert search query reformulation engine for a codebase intelligence tool.

Your job is to examine a conversation history between a software engineer and an assistant,
and rewrite the user's latest follow-up question into a single, fully self-contained search query.

RULES:
1. Resolve all ambiguous pronouns ("it", "its", "that", "this component", "those files")
   using the context from the conversation history.
2. If the user's question is already completely self-contained (e.g. "Where is Redis configured in Docker Compose?"),
   output it EXACTLY as-is.
3. Do NOT attempt to answer the question.
4. Output ONLY the rewritten search query. No markdown fences, no explanations, no preamble.
"""


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class SessionMemory:
    """Thread-safe conversational memory for a single session."""

    def __init__(self, session_id: str, max_turns: int = 5):
        self.session_id = session_id
        self.max_turns = max_turns
        self.messages: list[ChatMessage] = []
        self._lock = threading.Lock()
        self.last_accessed = time.time()

    def add_turn(self, user_text: str, assistant_text: str):
        """Append a user question and assistant response pair."""
        with self._lock:
            self.last_accessed = time.time()
            self.messages.append(ChatMessage(role="user", content=user_text))
            self.messages.append(ChatMessage(role="assistant", content=assistant_text))
            # Sliding window: keep at most max_turns * 2 messages
            max_msgs = self.max_turns * 2
            if len(self.messages) > max_msgs:
                self.messages = self.messages[-max_msgs:]

    def get_history(self) -> list[ChatMessage]:
        """Return a copy of the current message history."""
        with self._lock:
            self.last_accessed = time.time()
            return list(self.messages)

    def clear(self):
        with self._lock:
            self.messages.clear()


class SessionMemoryManager:
    """Global registry of conversational session memories."""

    def __init__(self, max_turns_per_session: int = 5, ttl_seconds: int = 86400):
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = threading.Lock()
        self.max_turns = max_turns_per_session
        self.ttl_seconds = ttl_seconds

    def get_or_create(self, session_id: str | None = None) -> tuple[str, SessionMemory]:
        """Retrieve existing session or create a new one with a fresh UUID.

        Also evicts expired sessions (older than ttl_seconds) to prevent memory leaks.
        """
        with self._lock:
            # Evict expired sessions
            now = time.time()
            expired = [
                sid for sid, mem in self._sessions.items()
                if (now - mem.last_accessed) > self.ttl_seconds
            ]
            for sid in expired:
                del self._sessions[sid]

            if not session_id or not session_id.strip():
                session_id = f"sess_{uuid.uuid4().hex[:12]}"

            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(session_id, max_turns=self.max_turns)

            return session_id, self._sessions[session_id]

    def clear_session(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].clear()

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)


# Global singleton instance
memory_manager = SessionMemoryManager()


def rewrite_query_with_history(
    query: str,
    history: list[ChatMessage],
    client: genai.Client | None = None,
    model_name: str | None = None,
) -> str:
    """Rewrite follow-up queries using conversation history to resolve coreferences.

    If history is empty or query is already self-contained, returns query directly.
    """
    if not history:
        return query

    # Quick heuristic: if query contains no pronouns or follow-up markers, leave as-is
    follow_up_markers = {
        "it", "its", "that", "this", "these", "those", "them", "and", "what about", "how about", "show me"
    }
    words = set(query.lower().split())
    if not (words & follow_up_markers) and len(query.split()) >= 6:
        return query

    if client is None:
        if not settings.has_gemini_key:
            return query
        client = genai.Client(api_key=settings.gemini_api_key)

    # Format history turns
    history_lines = []
    for msg in history[-6:]:  # Use last 3 turns
        role_label = "User" if msg.role == "user" else "Assistant"
        # Truncate assistant messages to keep prompt focused
        content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
        history_lines.append(f"{role_label}: {content}")

    conversation_context = "\n".join(history_lines)

    prompt = f"""[Conversation History]
{conversation_context}

[Latest Follow-Up Question]
{query}

Rewritten Self-Contained Query:"""

    candidates = [model_name or settings.gemini_model, *settings.gemini_fallback_models]
    for model in candidates:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=REWRITE_SYSTEM_PROMPT,
                    temperature=0.0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            rewritten = (resp.text or "").strip()
            if rewritten and len(rewritten) >= 3:
                return rewritten
        except Exception as e:
            logger.warning("Query rewrite via %s failed: %s", model, e)
            continue

    # Fallback to original query on upstream failure
    return query

