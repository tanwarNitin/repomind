import os
import shutil
import subprocess
import uuid
import sys
import stat
from urllib.parse import urlparse
from pathlib import Path
from fastapi import HTTPException
from .search import build_index
from .db import SessionLocal, Repo

REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "repos")

# Ensure repos dir exists
os.makedirs(REPOS_DIR, exist_ok=True)

def normalize_source(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        parsed = urlparse(source)
        normalized_netloc = parsed.netloc.lower()
        normalized = f"{parsed.scheme}://{normalized_netloc}{parsed.path}"
        return normalized.rstrip('/')
    return source.rstrip('/')

def ingest_repo(source: str):
    if not (source.startswith("http://") or source.startswith("https://") or os.path.exists(source)):
        raise HTTPException(status_code=400, detail="Invalid source")

    norm_source = normalize_source(source)

    db = SessionLocal()
    try:
        existing = db.query(Repo).filter(Repo.source == norm_source).first()
        if existing:
            from .search import _indexes
            if existing.repo_id not in _indexes:
                build_index(existing.repo_id, existing.path)
            return {
                "repo_id": existing.repo_id,
                "files_indexed": existing.files_indexed,
                "symbols_indexed": existing.symbols_indexed
            }

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
        
        repo_obj = Repo(
            repo_id=repo_id,
            source=norm_source,
            path=repo_path,
            files_indexed=stats["files_indexed"],
            symbols_indexed=stats["symbols_indexed"]
        )
        db.add(repo_obj)
        db.commit()
        
        return {
            "repo_id": repo_id,
            "files_indexed": stats["files_indexed"],
            "symbols_indexed": stats["symbols_indexed"]
        }
    finally:
        db.close()

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def reingest_repo(repo_id: str):
    db = SessionLocal()
    try:
        repo_obj = db.query(Repo).filter(Repo.repo_id == repo_id).first()
        if not repo_obj:
            raise HTTPException(status_code=404, detail="Repo not found")
            
        repo_path = repo_obj.path
        source = repo_obj.source
        
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, onerror=remove_readonly)
        
        if source.startswith("http://") or source.startswith("https://"):
            try:
                subprocess.run(["git", "clone", "--depth", "1", source, repo_path], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                lines = e.stderr.strip().split('\n') if e.stderr else []
                last_line = lines[-1] if lines else "unknown error"
                raise HTTPException(status_code=502, detail=f"clone_failed: {last_line}")
        else:
            shutil.copytree(source, repo_path)
            
        stats = build_index(repo_id, repo_path)
        repo_obj.files_indexed = stats["files_indexed"]
        repo_obj.symbols_indexed = stats["symbols_indexed"]
        db.commit()
        
        return {
            "repo_id": repo_id,
            "files_indexed": stats["files_indexed"],
            "symbols_indexed": stats["symbols_indexed"]
        }
    finally:
        db.close()

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
