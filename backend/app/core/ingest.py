import os
import shutil
import subprocess
import uuid
from pathlib import Path
from fastapi import HTTPException
from .search import build_index
from .db import SessionLocal, Repo

REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "repos")

# Ensure repos dir exists
os.makedirs(REPOS_DIR, exist_ok=True)

def ingest_repo(source: str):
    if not (source.startswith("http://") or source.startswith("https://") or os.path.exists(source)):
        raise HTTPException(status_code=400, detail="Invalid source")

    repo_id = str(uuid.uuid4())
    repo_path = os.path.join(REPOS_DIR, repo_id)
    
    if source.startswith("http://") or source.startswith("https://"):
        # clone depth 1
        try:
            subprocess.run(["git", "clone", "--depth", "1", source, repo_path], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            lines = e.stderr.strip().split('\n') if e.stderr else []
            last_line = lines[-1] if lines else "unknown error"
            raise HTTPException(status_code=502, detail=f"clone_failed: {last_line}")
    else:
        # local path
        # copy to repo_path
        shutil.copytree(source, repo_path)
        
    stats = build_index(repo_id, repo_path)
    
    db = SessionLocal()
    try:
        repo_obj = Repo(
            repo_id=repo_id,
            source=source,
            path=repo_path,
            files_indexed=stats["files_indexed"],
            symbols_indexed=stats["symbols_indexed"]
        )
        db.add(repo_obj)
        db.commit()
    finally:
        db.close()
    
    return {
        "repo_id": repo_id,
        "files_indexed": stats["files_indexed"],
        "symbols_indexed": stats["symbols_indexed"]
    }

def get_repos():
    db = SessionLocal()
    try:
        repos = db.query(Repo).all()
        return {
            r.repo_id: {
                "source": r.source,
                "path": r.path,
                "files_indexed": r.files_indexed,
                "symbols_indexed": r.symbols_indexed
            } for r in repos
        }
    finally:
        db.close()
