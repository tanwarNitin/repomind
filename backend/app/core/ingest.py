import os
import shutil
import subprocess
import uuid
from pathlib import Path
from .search import build_index

REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "repos")

# Ensure repos dir exists
os.makedirs(REPOS_DIR, exist_ok=True)

# Map repo_id -> URL/Source
_repos = {}

def ingest_repo(source: str):
    repo_id = str(uuid.uuid4())
    repo_path = os.path.join(REPOS_DIR, repo_id)
    
    if source.startswith("http://") or source.startswith("https://"):
        # clone depth 1
        subprocess.run(["git", "clone", "--depth", "1", source, repo_path], check=True)
    else:
        # local path
        if not os.path.exists(source):
            raise ValueError(f"Local path does not exist: {source}")
        # copy to repo_path
        shutil.copytree(source, repo_path)
        
    stats = build_index(repo_id, repo_path)
    
    _repos[repo_id] = {
        "source": source,
        "path": repo_path,
        "files_indexed": stats["files_indexed"],
        "symbols_indexed": stats["symbols_indexed"]
    }
    
    return {
        "repo_id": repo_id,
        "files_indexed": stats["files_indexed"],
        "symbols_indexed": stats["symbols_indexed"]
    }

def get_repos():
    return _repos
