import pytest
import subprocess
from fastapi.testclient import TestClient
from app.main import app
from app.core import ingest
from app.core.db import SessionLocal, Repo

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_test_repos():
    db = SessionLocal()
    urls = [
        "https://github.com/a/b.git",
        "https://github.com/test/reingest",
        "https://github.com/Test/Norm.git"
    ]
    db.query(Repo).filter(Repo.source.in_(urls)).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(Repo).filter(Repo.source.in_(urls)).delete()
    db.commit()
    db.close()

def test_ingest_same_url_returns_existing_repo_id(monkeypatch):
    call_count = 0
    def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return subprocess.CompletedProcess(args, 0, "", "")
    
    monkeypatch.setattr(ingest.subprocess, "run", mock_run)
    monkeypatch.setattr(ingest, "build_index", lambda repo_id, repo_path: {"files_indexed": 1, "symbols_indexed": 1})
    
    res1 = client.post("/api/ingest", json={"source": "https://github.com/a/b.git"})
    assert res1.status_code == 200
    repo_id1 = res1.json()["repo_id"]
    
    res2 = client.post("/api/ingest", json={"source": "https://github.com/a/b.git"})
    assert res2.status_code == 200
    repo_id2 = res2.json()["repo_id"]
    
    assert repo_id1 == repo_id2
    assert call_count == 1

def test_reingest_refreshes_under_same_repo_id(monkeypatch):
    call_count = 0
    def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return subprocess.CompletedProcess(args, 0, "", "")
    
    monkeypatch.setattr(ingest.subprocess, "run", mock_run)
    monkeypatch.setattr(ingest, "build_index", lambda repo_id, repo_path: {"files_indexed": call_count, "symbols_indexed": call_count})
    
    res = client.post("/api/ingest", json={"source": "https://github.com/test/reingest"})
    assert res.status_code == 200
    repo_id = res.json()["repo_id"]
    assert res.json()["files_indexed"] == 1
    assert call_count == 1
    
    res_re = client.post("/api/reingest", json={"repo_id": repo_id})
    assert res_re.status_code == 200
    assert res_re.json()["repo_id"] == repo_id
    assert res_re.json()["files_indexed"] == 2
    assert call_count == 2

def test_url_normalization_collapses_variants(monkeypatch):
    call_count = 0
    def mock_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return subprocess.CompletedProcess(args, 0, "", "")
    
    monkeypatch.setattr(ingest.subprocess, "run", mock_run)
    monkeypatch.setattr(ingest, "build_index", lambda repo_id, repo_path: {"files_indexed": 1, "symbols_indexed": 1})
    
    res1 = client.post("/api/ingest", json={"source": "https://github.com/Test/Norm.git/"})
    assert res1.status_code == 200
    repo_id1 = res1.json()["repo_id"]
    
    res2 = client.post("/api/ingest", json={"source": "https://GITHUB.com/Test/Norm.git"})
    assert res2.status_code == 200
    repo_id2 = res2.json()["repo_id"]
    
    assert repo_id1 == repo_id2
    assert call_count == 1
