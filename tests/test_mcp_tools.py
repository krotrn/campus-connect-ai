import pytest
from src.mcp.server import ALLOWED_MCP_TOOLS, mcp_server


@pytest.mark.asyncio
async def test_mcp_list_tools():
    tools = await mcp_server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == ALLOWED_MCP_TOOLS
    assert "search_campus_connect" in tool_names
    assert "explain_codebase_query" in tool_names
    assert "get_commit_history" in tool_names
    assert "get_commit_diff" in tool_names
    assert "find_module_dependents" in tool_names


@pytest.mark.asyncio
async def test_mcp_call_search_tool():
    result = await mcp_server.call_tool(
        "search_campus_connect",
        {"query": "Where is authentication implemented?", "top_k": 2},
    )
    assert not result.is_error
    text_content = result.content[0].text
    assert "relevant code chunks" in text_content or "Chunk" in text_content
    assert "[" in text_content and "#L" in text_content


@pytest.mark.asyncio
async def test_mcp_call_commit_history():
    result = await mcp_server.call_tool(
        "get_commit_history",
        {"max_count": 2},
    )
    assert not result.is_error
    text_content = result.content[0].text
    assert len(text_content) > 10
    assert " - " in text_content


@pytest.mark.asyncio
async def test_mcp_call_commit_diff():
    result = await mcp_server.call_tool(
        "get_commit_diff",
        {"commit_hash": "6e19f61"},
    )
    assert not result.is_error
    text_content = result.content[0].text
    assert "6e19f61" in text_content
    assert "Add integration tests" in text_content


@pytest.mark.asyncio
async def test_mcp_call_module_dependents():
    result = await mcp_server.call_tool(
        "find_module_dependents",
        {"module_name": "redis"},
    )
    assert not result.is_error
    text_content = result.content[0].text
    assert "redis" in text_content
    assert "-" in text_content

