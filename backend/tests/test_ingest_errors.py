import pytest
import subprocess
from fastapi.testclient import TestClient
from app.main import app
from app.core import ingest

client = TestClient(app)

def test_ingest_bad_source_returns_400():
    res = client.post("/api/ingest", json={"source": "invalid_path_that_does_not_exist_at_all"})
    assert res.status_code == 400
    assert "Invalid source" in res.json()["detail"]

def test_ingest_clone_failure_returns_502(monkeypatch):
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "clone"],
            output="",
            stderr="fatal: Could not resolve host: github.com"
        )
    
    monkeypatch.setattr(ingest.subprocess, "run", mock_run)
    
    res = client.post("/api/ingest", json={"source": "https://github.com/invalid/repo.git"})
    assert res.status_code == 502
    assert "clone_failed: fatal: Could not resolve host: github.com" in res.json()["detail"]
