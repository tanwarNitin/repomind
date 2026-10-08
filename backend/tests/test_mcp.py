import pytest
import os
from app.mcp_server import mcp
import app.mcp_server as mcp_server
from app.core.ingest import ingest_repo

@pytest.fixture(scope="module")
def fixture_repo_id():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
    res = ingest_repo(fixture_path)
    return res["repo_id"]

@pytest.fixture(autouse=True)
def setup_mcp(fixture_repo_id):
    mcp_server.CURRENT_REPO_ID = fixture_repo_id
    yield
    mcp_server.CURRENT_REPO_ID = None

@pytest.mark.asyncio
async def test_mcp_server_lists_all_tools():
    tools = await mcp.list_tools()
    names = [t.name for t in tools]
    assert "search_code" in names
    assert "read_file" in names
    assert "symbol_lookup" in names
    assert "grep" in names
    assert "repo_summary" in names

@pytest.mark.asyncio
async def test_mcp_read_file_returns_exact_lines():
    res_tuple = await mcp.call_tool("read_file", {"path": "utils.py", "start": 1, "end": 2})
    text = res_tuple[0][0].text
    assert "def parse_date" in text

@pytest.mark.asyncio
async def test_mcp_tool_rejects_path_traversal():
    res_tuple = await mcp.call_tool("read_file", {"path": "../../../etc/passwd", "start": 1, "end": 10})
    text = res_tuple[0][0].text
    assert "Path traversal" in text or "Error" in text

@pytest.mark.asyncio
async def test_mcp_search_code_returns_ranked_slices():
    res_tuple = await mcp.call_tool("search_code", {"query": "date parsing"})
    text = res_tuple[0][0].text
    # FastMCP converts list/dict results to string implicitly in TextContent
    assert "utils.py" in text
