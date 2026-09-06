import re
from typing import List
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


def create_agent_graph(retriever: Retriever, generator: AnswerGenerator):
    """
    Constructs and compiles the LangGraph state machine for agentic code intelligence.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Router Node
    # ─────────────────────────────────────────────────────────────────────────
    def router_node(state: AgentState) -> dict:
        question = state["question"]
        route, reasoning, target = route_query(question)
        steps = state.get("steps_taken", []) + [f"routed_to_{route}"]
        return {
            "route": route,
            "route_reasoning": reasoning,
            "target": target,
            "steps_taken": steps,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Branch: Direct RAG Node
    # ─────────────────────────────────────────────────────────────────────────
    def rag_node(state: AgentState) -> dict:
        question = state["question"]
        top_k = state.get("top_k", 5)
        chunks = retriever.retrieve(question, top_k=top_k)
        chunks_payload = [
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
        steps = state.get("steps_taken", []) + ["retrieved_rag_chunks"]
        return {"context_chunks": chunks_payload, "steps_taken": steps}

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Branch: Git History Node
    # ─────────────────────────────────────────────────────────────────────────
    def git_history_node(state: AgentState) -> dict:
        history = get_git_commit_history(max_count=8)
        steps = state.get("steps_taken", []) + ["executed_git_history"]
        return {"tool_output": history, "steps_taken": steps}

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Branch: Git Commit Node
    # ─────────────────────────────────────────────────────────────────────────
    def git_commit_node(state: AgentState) -> dict:
        target = state.get("target") or ""
        if not target:
            # Fallback search for commit hash in the query string
            match = re.search(r"\b([0-9a-fA-F]{6,40})\b", state["question"])
            target = match.group(1) if match else ""
        if not target:
            return {"tool_output": "Error: No commit hash found in the query. Please specify a commit hash.", "steps_taken": state.get("steps_taken", []) + ["error_no_commit_hash"]}

        commit_info = get_commit_details(target)
        steps = state.get("steps_taken", []) + [f"inspected_commit_{target}"]
        return {"tool_output": commit_info, "steps_taken": steps}

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Branch: File Dependents Node
    # ─────────────────────────────────────────────────────────────────────────
    def file_dependents_node(state: AgentState) -> dict:
        target = state.get("target") or ""
        if not target:
            # Extract candidate module name from question
            match = re.search(r"(?:depend on|import|use)\s+['\"]?([a-zA-Z0-9_\-\.\/]+)", state["question"], re.IGNORECASE)
            target = match.group(1) if match else ""
        if not target:
            return {"tool_output": "Error: Could not identify a module name from the query. Please specify which module to check.", "steps_taken": state.get("steps_taken", []) + ["error_no_module_name"]}

        dependents = find_file_dependents(target)
        if dependents:
            output = f"The following files import or depend on '{target}':\n" + "\n".join(
                f"- {f}" for f in dependents
            )
        else:
            output = f"No direct source files were found importing '{target}' in the codebase."

        steps = state.get("steps_taken", []) + [f"scanned_dependents_for_{target}"]
        return {"tool_output": output, "steps_taken": steps}

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Synthesizer Node
    # ─────────────────────────────────────────────────────────────────────────
    def synthesizer_node(state: AgentState) -> dict:
        question = state["question"]
        tool_output = state.get("tool_output")
        context_chunks_data = state.get("context_chunks", [])

        if tool_output:
            # Tool output synthesized directly with grounded formatting
            answer = (
                f"### Result from Codebase Tool Analysis\n\n"
                f"**Route Selected**: `{state.get('route')}` ({state.get('route_reasoning')})\n\n"
                f"```text\n{tool_output}\n```"
            )
            sources = [
                {
                    "file_path": "git-repository-history" if "git" in state.get("route", "") else "module-dependency-graph",
                    "start_line": 1,
                    "end_line": 1,
                    "citation": "repo-tool-call",
                    "content": tool_output,
                    "score": 1.0,
                }
            ]
        elif context_chunks_data:
            # Convert back to RetrievedChunk objects for AnswerGenerator
            chunk_objs = [
                RetrievedChunk(
                    content=c["content"],
                    file_path=c["file_path"],
                    start_line=c["start_line"],
                    end_line=c["end_line"],
                    file_type=c["file_type"],
                    score=c["score"],
                )
                for c in context_chunks_data
            ]
            gen_result = generator.generate(question, chunk_objs)
            answer = gen_result.answer
            sources = [s.model_dump() for s in gen_result.sources]
        else:
            answer = "No sufficient context or tool data could be gathered to answer this question."
            sources = []

        steps = state.get("steps_taken", []) + ["synthesized_final_answer"]
        return {"answer": answer, "sources": sources, "steps_taken": steps}

    # ─────────────────────────────────────────────────────────────────────────
    # Graph Wiring
    # ─────────────────────────────────────────────────────────────────────────
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("direct_rag", rag_node)
    workflow.add_node("git_history", git_history_node)
    workflow.add_node("git_commit", git_commit_node)
    workflow.add_node("file_dependents", file_dependents_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Edge from START to router
    workflow.add_edge(START, "router")

    # Conditional branching from router
    def route_decision(state: AgentState) -> str:
        return state.get("route", "direct_rag")

    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "direct_rag": "direct_rag",
            "git_history": "git_history",
            "git_commit": "git_commit",
            "file_dependents": "file_dependents",
        },
    )

    # All branches flow into the synthesizer
    workflow.add_edge("direct_rag", "synthesizer")
    workflow.add_edge("git_history", "synthesizer")
    workflow.add_edge("git_commit", "synthesizer")
    workflow.add_edge("file_dependents", "synthesizer")

    # Synthesizer terminates the graph
    workflow.add_edge("synthesizer", END)

    return workflow.compile()

