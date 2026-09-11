from typing import Literal, NotRequired, TypedDict

Route = Literal["direct_rag", "git_history", "git_commit", "file_dependents"]


class AgentState(TypedDict):
    """State threaded through the LangGraph agent.

    Only ``question`` is supplied by every caller. ``route``/``route_reasoning``/
    ``target`` may be pre-populated by the API layer when it has already
    classified the query, in which case ``router_node`` reuses that decision
    instead of re-running classification.
    """

    question: str
    top_k: NotRequired[int]
    route: NotRequired[Route]
    route_reasoning: NotRequired[str]
    target: NotRequired[str | None]
    context_chunks: NotRequired[list[dict]]
    tool_output: NotRequired[str | None]
    answer: NotRequired[str]
    sources: NotRequired[list[dict]]
    steps_taken: NotRequired[list[str]]
    gemini_api_key: NotRequired[str | None]
