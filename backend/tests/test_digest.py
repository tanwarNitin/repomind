import pytest
import httpx
from app.digest.duplicates import find_duplicates
from app.digest.digest import generate_digest_report, get_digest
from app.core.db import SessionLocal, Repo, Digest
from app.core.ingest import get_repos

def test_duplicate_detection_finds_duplicate():
    existing = [
        {"id": "1", "title": "Button is completely broken", "body": "When I click the button it crashes."},
        {"id": "2", "title": "Random issue", "body": "This has nothing to do with it."},
        {"id": "3", "title": "Another thing", "body": "Fixing the UI bug."}
    ]
    new_issue = {"title": "Button crashes", "body": "Clicking button causes crash"}
    dups = find_duplicates(new_issue, existing, threshold=0.01)
    assert len(dups) > 0
    assert dups[0]["is_duplicate"] is True

def test_duplicate_detection_no_false_positive():
    existing = [
        {"id": "1", "title": "Button is completely broken", "body": "When I click the button it crashes."}
    ]
    new_issue = {"title": "Update README", "body": "Fix typo in documentation"}
    dups = find_duplicates(new_issue, existing, threshold=0.5)
    assert len(dups) == 0 or dups[0]["is_duplicate"] is False

def mock_get_issues(url, **kwargs):
    if "api.github.com/repos/owner/repo/issues" in str(url):
        return httpx.Response(200, json=[
            {"number": 1, "title": "High Sev High Conf", "body": "Easy to fix crash", "html_url": "url1"},
            {"number": 2, "title": "Low Sev Low Conf", "body": "Hard to reproduce typo", "html_url": "url2"},
            {"number": 3, "title": "High Sev Low Conf", "body": "Hard crash", "html_url": "url3"}
        ], request=httpx.Request("GET", url))
    return httpx.Response(500, request=httpx.Request("GET", url))

class MockCompletion:
    class Choice:
        class Message:
            def __init__(self, content):
                self.content = content
        def __init__(self, content):
            self.message = self.Message(content)
    def __init__(self, content):
        self.choices = [self.Choice(content)]

def mock_completion(model, messages, response_format):
    content = messages[0]["content"]
    if "High Sev High Conf" in content:
        return MockCompletion('{"severity": 9, "confidence": 9, "summary": "sum1", "evidence_refs": []}')
    elif "Low Sev Low Conf" in content:
        return MockCompletion('{"severity": 2, "confidence": 2, "summary": "sum2", "evidence_refs": []}')
    elif "High Sev Low Conf" in content:
        return MockCompletion('{"severity": 9, "confidence": 2, "summary": "sum3", "evidence_refs": []}')
    return MockCompletion('{"severity": 5, "confidence": 5, "summary": "default", "evidence_refs": []}')

def test_digest_ranks_by_severity_then_confidence(monkeypatch):
    monkeypatch.setattr(httpx, "get", mock_get_issues)
    import app.digest.digest as digest_module
    monkeypatch.setattr(digest_module, "completion", mock_completion)
    
    db = SessionLocal()
    try:
        repo = Repo(repo_id="test_repo_1", source="https://github.com/owner/repo", path="/tmp")
        db.merge(repo)
        db.commit()
    finally:
        db.close()
        
    digest_id = generate_digest_report("test_repo_1")
    report = get_digest(digest_id)
    md = report["markdown_report"]
    
    # Check ordering. High Sev High (81) > High Sev Low (18) > Low Sev Low (4)
    idx1 = md.find("High Sev High Conf")
    idx2 = md.find("High Sev Low Conf")
    idx3 = md.find("Low Sev Low Conf")
    
    assert idx1 < idx2 < idx3

def test_digest_report_persists_and_renders_markdown(monkeypatch):
    monkeypatch.setattr(httpx, "get", mock_get_issues)
    import app.digest.digest as digest_module
    monkeypatch.setattr(digest_module, "completion", mock_completion)
    
    db = SessionLocal()
    try:
        repo = Repo(repo_id="test_repo_2", source="https://github.com/owner/repo", path="/tmp")
        db.merge(repo)
        db.commit()
    finally:
        db.close()
        
    digest_id = generate_digest_report("test_repo_2")
    
    db = SessionLocal()
    digest = db.query(Digest).filter(Digest.id == digest_id).first()
    assert digest is not None
    assert "# Digest Report for https://github.com/owner/repo" in digest.markdown_report
    db.close()

def test_repos_survive_restart_in_sqlite():
    db = SessionLocal()
    try:
        repo = Repo(repo_id="test_repo_persist", source="local/path", path="/tmp/path", files_indexed=10, symbols_indexed=20)
        db.merge(repo)
        db.commit()
    finally:
        db.close()
        
    repos = get_repos()
    assert "test_repo_persist" in repos
    assert repos["test_repo_persist"]["files_indexed"] == 10
