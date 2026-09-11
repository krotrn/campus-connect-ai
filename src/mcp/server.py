import asyncio
import logging
import sys

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from src.agent.tools import (
    find_file_dependents,
    get_commit_details,
    get_git_commit_history,
)
from src.config import settings
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Explicit Permissions / Tool Allowlist (FR6.2)
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_MCP_TOOLS = {
    "search_campus_connect",
    "explain_codebase_query",
    "get_commit_history",
    "get_commit_diff",
    "find_module_dependents",
}

# Singleton instances for MCP execution
_retriever: Retriever | None = None
_generator: AnswerGenerator | None = None


def _get_services():
    global _retriever, _generator
    # Reuse singletons from FastAPI lifespan if available
    try:
        from src.api.main import services
        if services.get("retriever") and services.get("generator"):
            return services["retriever"], services["generator"]
    except Exception:
        pass

    # Fallback for standalone stdio execution
    if _retriever is None:
        _retriever = Retriever()
    if _generator is None:
        _generator = AnswerGenerator()
    return _retriever, _generator


def create_mcp_server(allowed_tools: set[str] | None = None) -> MCPServer:
    """
    Constructs and configures the AEIA Model Context Protocol Server (2026-07-28 Spec).

    Only tools named in *allowed_tools* are registered, so a disallowed tool is
    absent from ``tools/list`` entirely rather than advertised and then refused.
    """
    allowed = ALLOWED_MCP_TOOLS if allowed_tools is None else allowed_tools
    server = MCPServer(
        name="aeia-campus-connect",
        version="0.4.0",
        instructions=(
            "Model Context Protocol server for Campus Connect codebase intelligence. "
            "Provides grounded semantic search, architectural query explanation, "
            "git commit inspection, and reverse module dependency analysis."
        ),
    )

    def tool(name: str, description: str):
        """Register a tool only when the allowlist permits it."""
        if name in allowed:
            return server.tool(name=name, description=description)
        logger.info("MCP tool %r is not in the allowlist; skipping registration.", name)
        return lambda fn: fn

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 1: Hybrid Semantic & Lexical Search
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "search_campus_connect",
        (
            "Perform hybrid (BM25 + dense vector) search over the Campus Connect codebase. "
            "Returns code chunks with exact file paths and line numbers."
        ),
    )
    def search_campus_connect(query: str, top_k: int = 5) -> str:
        retriever, _ = _get_services()
        chunks = retriever.retrieve(query, top_k=min(max(1, top_k), 15))

        if not chunks:
            return "No matching code chunks found."

        output_parts = [f"Found {len(chunks)} relevant code chunks:"]
        for i, c in enumerate(chunks, 1):
            output_parts.append(
                f"\n--- Chunk {i}: [{c.citation}] (Type: {c.file_type}, Score: {c.score:.4f}) ---\n"
                f"{c.content.strip()}"
            )
        return "\n".join(output_parts)

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 2: Full Grounded RAG Query
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "explain_codebase_query",
        (
            "Ask an engineering question about the Campus Connect codebase. "
            "Returns a synthesized answer strictly grounded in source code with [filepath#Lstart-Lend] citations."
        ),
    )
    def explain_codebase_query(question: str, top_k: int = 5) -> str:
        retriever, generator = _get_services()
        chunks = retriever.retrieve(question, top_k=min(max(1, top_k), 10))
        result = generator.generate(question, chunks)

        citations_summary = "\n".join(f"- {s.citation}" for s in result.sources)
        return f"{result.answer}\n\nSources Cited:\n{citations_summary}"

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 3: Git Commit History (Non-RAG)
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "get_commit_history",
        (
            "Retrieve recent git commit logs from the Campus Connect repository, optionally filtered by file path."
        ),
    )
    def get_commit_history(max_count: int = 5, path: str = "") -> str:
        return get_git_commit_history(max_count=max_count, path=path if path else None)

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 4: Git Commit Diff & Stats (Non-RAG)
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "get_commit_diff",
        "Retrieve changed files and line change stats for a specific git commit hash in Campus Connect.",
    )
    def get_commit_diff(commit_hash: str) -> str:
        return get_commit_details(commit_hash)

    # ─────────────────────────────────────────────────────────────────────────
    # Tool 5: Module Reverse Dependency Tracker (Non-RAG)
    # ─────────────────────────────────────────────────────────────────────────
    @tool(
        "find_module_dependents",
        (
            "Scan the codebase to identify all source files (.ts, .tsx, .js) that import or depend on a given module."
        ),
    )
    def find_module_dependents(module_name: str) -> str:
        dependents = find_file_dependents(module_name)
        if not dependents:
            return f"No source files were found importing or depending on '{module_name}'."
        return f"Files importing '{module_name}':\n" + "\n".join(f"- {f}" for f in dependents)

    return server


# Global server instance
mcp_server = create_mcp_server()


def get_streamable_http_app():
    """
    Creates Starlette app speaking the 2026-07-28 stateless HTTP protocol.
    """
    # DNS-rebinding protection rejects any Host header not on this list, so it
    # must name the deployed hostname — not just localhost — or every real
    # request is refused.
    sec = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_hosts,
    )
    return mcp_server.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        transport_security=sec,
    )


if __name__ == "__main__":
    # Stdio transport entrypoint for local execution (e.g. Claude Desktop, Cursor)
    from src.logging_config import configure_logging

    configure_logging()
    print("Starting AEIA Model Context Protocol Server (stdio transport)...", file=sys.stderr)
    asyncio.run(mcp_server.run_stdio_async())

