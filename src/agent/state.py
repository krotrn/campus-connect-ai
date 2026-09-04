from typing import List, Literal, Optional, TypedDict


class AgentState(TypedDict):
    question: str
    top_k: int
    route: Literal["direct_rag", "git_history", "git_commit", "file_dependents"]
    route_reasoning: str
    target: Optional[str]
    context_chunks: List[dict]
    tool_output: Optional[str]
    answer: str
    sources: List[dict]
    steps_taken: List[str]
