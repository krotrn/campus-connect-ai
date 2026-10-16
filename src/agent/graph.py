"""The agent: a small LangGraph state machine.

    START -> router --+--> direct_rag ------+
                      +--> git_history -----+
                      +--> git_commit ------+--> synthesizer -> END
                      +--> file_dependents -+

1. router       picks ONE route (reuses the API layer's choice if it already made one)
2. one branch   gathers evidence: RAG chunks, or the output of a git/dependency tool
3. synthesizer  turns that evidence into the final answer + sources

Every node reads the shared ``AgentState`` and returns only the keys it changes.
"""

import re

from langgraph.graph import END, START, StateGraph

from src.agent.router import route_query
from src.agent.state import AgentState
from src.agent.tools import (
    find_file_dependents,
    get_commit_details,
    get_git_commit_history,
)
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import RetrievedChunk, Retriever

# ─── helpers ─────────────────────────────────────────────────────────────────


def _with_step(state: AgentState, step: str) -> list[str]:
    """The audit trail returned to the client: previous steps plus this one."""
    return state.get("steps_taken", []) + [step]


def _tool_error(state: AgentState, message: str, step: str) -> dict:
    return {"tool_output": f"Error: {message}", "steps_taken": _with_step(state, step)}


# ─── 1. router ───────────────────────────────────────────────────────────────


def router_node(state: AgentState) -> dict:
    # The API layer may have already routed (it needs the route to choose between
    # streaming RAG and this agent). Reuse it rather than pay for a second LLM call.
    if preresolved := state.get("route"):
        return {
            "route": preresolved,
            "route_reasoning": state.get("route_reasoning", ""),
            "target": state.get("target"),
            "steps_taken": _with_step(state, f"reused_route_{preresolved}"),
        }

    route, reasoning, target = route_query(state["question"], api_key=state.get("gemini_api_key"))
    return {
        "route": route,
        "route_reasoning": reasoning,
        "target": target,
        "steps_taken": _with_step(state, f"routed_to_{route}"),
    }


# ─── 2. branches (each one gathers evidence) ─────────────────────────────────


def make_rag_node(retriever: Retriever):
    """Needs the retriever, so it is built with it injected."""

    def rag_node(state: AgentState) -> dict:
        chunks = retriever.retrieve(state["question"], top_k=state.get("top_k", 5))
        payload = [
            {
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content": c.content,
                "file_type": c.file_type,
                "score": c.score,
                "citation": c.citation,
            }
            for c in chunks
        ]
        return {"context_chunks": payload, "steps_taken": _with_step(state, "retrieved_rag_chunks")}

    return rag_node


def git_history_node(state: AgentState) -> dict:
    return {
        "tool_output": get_git_commit_history(max_count=8),
        "steps_taken": _with_step(state, "executed_git_history"),
    }


def git_commit_node(state: AgentState) -> dict:
    # Prefer the router's target; otherwise look for a hex hash in the question.
    target = state.get("target") or ""
    if not target and (match := re.search(r"\b([0-9a-fA-F]{6,40})\b", state["question"])):
        target = match.group(1)
    if not target:
        return _tool_error(
            state, "No commit hash found in the query. Please specify a commit hash.", "error_no_commit_hash"
        )

    return {
        "tool_output": get_commit_details(target),
        "steps_taken": _with_step(state, f"inspected_commit_{target}"),
    }


def file_dependents_node(state: AgentState) -> dict:
    # Prefer the router's target; otherwise pull a module name after "depend on/import/use".
    target = state.get("target") or ""
    if not target and (
        match := re.search(
            r"(?:depend on|import|use)\s+['\"]?([a-zA-Z0-9_\-\.\/]+)",
            state["question"],
            re.IGNORECASE,
        )
    ):
        target = match.group(1)
    if not target:
        return _tool_error(
            state,
            "Could not identify a module name from the query. Please specify which module to check.",
            "error_no_module_name",
        )

    if dependents := find_file_dependents(target):
        output = f"The following files import or depend on '{target}':\n" + "\n".join(f"- {f}" for f in dependents)
    else:
        output = f"No direct source files were found importing '{target}' in the codebase."
    return {"tool_output": output, "steps_taken": _with_step(state, f"scanned_dependents_for_{target}")}


# ─── 3. synthesizer ──────────────────────────────────────────────────────────


def make_synthesizer_node(generator: AnswerGenerator):
    """Turns whatever the branch gathered into the final answer."""

    def answer_from_tool(state: AgentState, tool_output: str) -> tuple[str, list[dict]]:
        # Run the raw tool output through the model so the engineer gets an answer,
        # not a diffstat. The generator falls back to the raw block without a model.
        synthesized = generator.generate_from_tool_output(
            state["question"],
            tool_output,
            route=state.get("route", ""),
            api_key=state.get("gemini_api_key"),
        )
        answer = f"**Route Selected**: `{state.get('route')}` ({state.get('route_reasoning')})\n\n{synthesized}"
        source = {
            "file_path": "git-repository-history" if "git" in state.get("route", "") else "module-dependency-graph",
            "start_line": 1,
            "end_line": 1,
            "citation": "repo-tool-call",
            "content": tool_output,
            "score": 1.0,
        }
        return answer, [source]

    def answer_from_chunks(state: AgentState, chunk_dicts: list[dict]) -> tuple[str, list[dict]]:
        chunks = [
            RetrievedChunk(
                content=c["content"],
                file_path=c["file_path"],
                start_line=c["start_line"],
                end_line=c["end_line"],
                file_type=c["file_type"],
                score=c["score"],
            )
            for c in chunk_dicts
        ]
        result = generator.generate(state["question"], chunks, api_key=state.get("gemini_api_key"))
        return result.answer, [s.model_dump() for s in result.sources]

    def synthesizer_node(state: AgentState) -> dict:
        if tool_output := state.get("tool_output"):
            answer, sources = answer_from_tool(state, tool_output)
        elif chunk_dicts := state.get("context_chunks"):
            answer, sources = answer_from_chunks(state, chunk_dicts)
        else:
            answer, sources = "No sufficient context or tool data could be gathered to answer this question.", []
        return {"answer": answer, "sources": sources, "steps_taken": _with_step(state, "synthesized_final_answer")}

    return synthesizer_node


# ─── wiring ──────────────────────────────────────────────────────────────────


def create_agent_graph(retriever: Retriever, generator: AnswerGenerator):
    """Build and compile the graph drawn at the top of this file."""
    branches = {
        "direct_rag": make_rag_node(retriever),
        "git_history": git_history_node,
        "git_commit": git_commit_node,
        "file_dependents": file_dependents_node,
    }

    workflow = StateGraph(AgentState)
    workflow.add_node("router", router_node)
    workflow.add_node("synthesizer", make_synthesizer_node(generator))
    workflow.add_edge(START, "router")

    for name, node in branches.items():
        workflow.add_node(name, node)
        workflow.add_edge(name, "synthesizer")  # every branch converges here

    # The router's chosen route is literally the name of the branch to run.
    workflow.add_conditional_edges(
        "router",
        lambda state: state.get("route", "direct_rag"),
        {name: name for name in branches},
    )
    workflow.add_edge("synthesizer", END)
    return workflow.compile()
