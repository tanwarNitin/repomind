import os
import subprocess
import re
from typing import Annotated, List, Dict, Any
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.core.guardrails import redact_secrets_and_pii
from app.core.ingest import REPOS_DIR
from app.core.search import query_repo

def get_repo_path(config: RunnableConfig) -> str:
    repo_id = config.get("configurable", {}).get("repo_id")
    if not repo_id:
        raise ValueError("repo_id not found in config")
    repo_path = os.path.join(REPOS_DIR, repo_id)
    return repo_path

def sanitize_path(base_path: str, relative_path: str) -> str:
    absolute_base = os.path.abspath(base_path)
    absolute_target = os.path.abspath(os.path.join(absolute_base, relative_path))
    
    if not absolute_target.startswith(absolute_base + os.sep) and absolute_target != absolute_base:
        raise ValueError(f"Path traversal detected: {relative_path}")
    
    return absolute_target

@tool
def read_file(path: str, start: int, end: int, config: RunnableConfig) -> str:
    """Read a specific range of lines from a file."""
    repo_path = get_repo_path(config)
    try:
        file_path = sanitize_path(repo_path, path)
    except ValueError as e:
        return f"Error: {str(e)}"
    
    if not os.path.exists(file_path):
        return f"Error: File {path} not found."
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = max(0, start - 1)
    end_idx = min(len(lines), end)
    
    content = "".join(lines[start_idx:end_idx])
    sanitized, _ = redact_secrets_and_pii(content)
    return sanitized

@tool
def grep(pattern: str, path: str, config: RunnableConfig) -> List[str]:
    """Search for a regex pattern across the repository or a specific path."""
    repo_path = get_repo_path(config)
    try:
        search_path = sanitize_path(repo_path, path)
    except ValueError as e:
        return [f"Error: {str(e)}"]
    
    results = []
    regex = re.compile(pattern)
        
    if os.path.isfile(search_path):
        to_walk = [(os.path.dirname(search_path), [], [os.path.basename(search_path)])]
    else:
        to_walk = os.walk(search_path)
        
    for root, dirs, files in to_walk:
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if regex.search(line):
                            results.append(f"{rel_path}:{i+1}:{line.strip()}")
            except Exception:
                continue
    
    if not results:
        return []
        
    sanitized_results = []
    for res in results:
        sanitized, _ = redact_secrets_and_pii(res)
        sanitized_results.append(sanitized)
    return sanitized_results

@tool
def symbol_lookup(name: str, config: RunnableConfig) -> List[Dict[str, Any]]:
    """Lookup a symbol (function, class, etc) in the codebase."""
    repo_id = config.get("configurable", {}).get("repo_id")
    if not repo_id:
        raise ValueError("repo_id not found in config")
        
    results = query_repo(repo_id, name, top_k=5)
    if not results:
        return []
        
    for res in results:
        res["snippet"], _ = redact_secrets_and_pii(res["snippet"])
        
    return results

@tool
def git_log_recent(path: str, n: int, config: RunnableConfig) -> str:
    """Get the recent n git commit logs for a specific path."""
    repo_path = get_repo_path(config)
    try:
        file_path = sanitize_path(repo_path, path)
    except ValueError as e:
        return f"Error: {str(e)}"
    
    if not os.path.exists(os.path.join(repo_path, ".git")):
        return "Error: Not a git repository."
        
    cmd = ["git", "log", f"-n{n}", "--oneline", "--", file_path]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    
    if result.returncode != 0:
        return f"Error running git log: {result.stderr}"
        
    sanitized, _ = redact_secrets_and_pii(result.stdout)
    return sanitized

TOOLS = [read_file, grep, symbol_lookup, git_log_recent]
