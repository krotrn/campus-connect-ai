from typing import Literal, NotRequired, TypedDict


class AgentState(TypedDict):
    question: str
    top_k: int
    route: Literal["direct_rag", "git_history", "git_commit", "file_dependents"]
    route_reasoning: str
    target: str | None
    context_chunks: list[dict]
    tool_output: str | None
    answer: str
    sources: list[dict]
    steps_taken: list[str]
    gemini_api_key: NotRequired[str | None]
