import argparse
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from app.agent.tools import read_file as _read_file, grep as _grep, symbol_lookup as _symbol_lookup
from app.core.search import query_repo
from app.core.ingest import get_repos
from app.core.guardrails import redact_secrets_and_pii

mcp = FastMCP("RepoMind")

CURRENT_REPO_ID = None

def get_config():
    return {"configurable": {"repo_id": CURRENT_REPO_ID}}

@mcp.tool()
def read_file(path: str, start: int = 1, end: int = 1000) -> str:
    """Read a specific range of lines from a file."""
    if not CURRENT_REPO_ID:
        return "Error: No repo_id configured"
    return _read_file.invoke({"path": path, "start": start, "end": end}, config=get_config())

@mcp.tool()
def grep(pattern: str, path: str = ".") -> List[str]:
    """Search for a regex pattern across the repository or a specific path."""
    if not CURRENT_REPO_ID:
        return ["Error: No repo_id configured"]
    return _grep.invoke({"pattern": pattern, "path": path}, config=get_config())

@mcp.tool()
def symbol_lookup(name: str) -> List[Dict[str, Any]]:
    """Lookup a symbol (function, class, etc) in the codebase."""
    if not CURRENT_REPO_ID:
        return [{"error": "No repo_id configured"}]
    return _symbol_lookup.invoke({"name": name}, config=get_config())

@mcp.tool()
def search_code(query: str) -> List[Dict[str, Any]]:
    """Search code using semantic search (BM25 + embeddings)."""
    if not CURRENT_REPO_ID:
        return [{"error": "No repo_id configured"}]
    results = query_repo(CURRENT_REPO_ID, query, top_k=5)
    sanitized_results = []
    for res in results:
        snippet, _ = redact_secrets_and_pii(res.get("snippet", ""))
        res["snippet"] = snippet
        sanitized_results.append(res)
    return sanitized_results

@mcp.tool()
def repo_summary() -> Dict[str, Any]:
    """Get statistics and summary about the repository."""
    if not CURRENT_REPO_ID:
        return {"error": "No repo_id configured"}
    repos = get_repos()
    if CURRENT_REPO_ID not in repos:
        return {"error": "Repo not found in registry"}
    
    repo_data = repos[CURRENT_REPO_ID]
    return {
        "repo_id": CURRENT_REPO_ID,
        "source": repo_data.get("source"),
        "files_indexed": repo_data.get("files_indexed"),
        "symbols_indexed": repo_data.get("symbols_indexed")
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoMind MCP Server")
    parser.add_argument("--repo", type=str, required=True, help="Repository ID to sandbox tools to")
    args = parser.parse_args()
    
    CURRENT_REPO_ID = args.repo
    mcp.run()
