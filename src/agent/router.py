import re
from typing import Optional, Tuple

from google import genai
from google.genai import types

from src.config import settings

ROUTER_SYSTEM_PROMPT = """You are a specialized query classifier for a code intelligence agent.
Classify the user query into exactly one of four routes:

1. "git_commit" : Query asks about a specific commit hash
   (e.g. "What changed in commit 6e19f61?", "Show diff for commit abc1234").
2. "git_history": Query asks about recent commits, commit logs, git history, who changed what recently.
3. "file_dependents": Query asks what files/modules depend on, import, or use a specific file/module
   (e.g. "What depends on redis?", "Which components import auth.utils?").
4. "direct_rag": Standard code location, implementation questions, architecture, database schemas,
   or general onboarding questions.

Respond in this exact format:
ROUTE: <git_commit|git_history|file_dependents|direct_rag>
REASON: <One sentence explanation>
TARGET: <Extracted commit hash or module name if applicable, else NONE>
"""


def classify_route_fast(question: str) -> Optional[Tuple[str, str, str]]:
    """
    Deterministic rule-based router. Returns (route, reasoning, target) if confident,
    or None if ambiguous (to let LLM decide).
    """
    q_lower = question.lower().strip()

    # 1. Check for specific commit hash (6 to 40 hex chars, must contain at least one digit)
    commit_match = re.search(r"\b([0-9a-fA-F]{6,40})\b", question)
    has_digit = any(c.isdigit() for c in commit_match.group(1)) if commit_match else False
    has_keyword = any(w in q_lower for w in ["commit", "diff", "changed in", "show"])
    if commit_match and has_digit and has_keyword:
        commit_hash = commit_match.group(1)
        return (
            "git_commit",
            f"Query references specific commit hash '{commit_hash}'.",
            commit_hash,
        )

    # 2. Check for git history / commit logs
    history_keywords = ["git log", "commit history", "recent commits", "latest commits", "commit log"]
    if any(phrase in q_lower for phrase in history_keywords):
        return (
            "git_history",
            "Query explicitly asks for git commit history or recent commits.",
            "",
        )

    # 3. Check for dependency / reverse import queries
    dep_match = re.search(
        r"(?:what|which)\s+(?:files?|components?|modules?|services?)\s+"
        r"(?:depend on|imports?|use)\s+['\"]?([a-zA-Z0-9_\-\.\/]+)['\"]?",
        q_lower,
    )
    if dep_match:
        target_module = dep_match.group(1)
        return (
            "file_dependents",
            f"Query asks for files depending on or importing '{target_module}'.",
            target_module,
        )

    return None


def classify_route_llm(question: str) -> Tuple[str, str, str]:
    """
    Uses Gemini LLM to classify ambiguous queries.
    """
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        return ("direct_rag", "Defaulted to direct RAG (no Gemini API key configured).", "")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"User Query: {question}",
            config=types.GenerateContentConfig(
                system_instruction=ROUTER_SYSTEM_PROMPT,
                temperature=0.0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        text = response.text or ""

        route = "direct_rag"
        reason = "LLM selected direct RAG."
        target = ""

        for line in text.splitlines():
            line = line.strip()
            if line.startswith("ROUTE:"):
                cand = line.split(":", 1)[1].strip().lower()
                if cand in {"git_commit", "git_history", "file_dependents", "direct_rag"}:
                    route = cand
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
            elif line.startswith("TARGET:"):
                cand_target = line.split(":", 1)[1].strip()
                if cand_target.upper() != "NONE":
                    target = cand_target

        return (route, reason, target)
    except Exception as e:
        return ("direct_rag", f"Routing fallback to direct_rag due to error: {str(e)}", "")


def route_query(question: str) -> Tuple[str, str, str]:
    """
    Main entry point for routing. Tries fast classification first, then falls back to LLM.
    Returns: (route, reasoning, target)
    """
    fast_result = classify_route_fast(question)
    if fast_result is not None:
        return fast_result

    return classify_route_llm(question)

