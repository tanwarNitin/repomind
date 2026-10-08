import pytest
import httpx
from app.integrations.github import fetch_issue, create_draft_pr
import os

def mock_get(url, **kwargs):
    url_str = str(url)
    if url_str == "https://api.github.com/repos/owner/repo/issues/1":
        return httpx.Response(200, json={
            "title": "Test Issue",
            "body": "This is a bug.",
            "comments": 2,
            "comments_url": "https://api.github.com/repos/owner/repo/issues/1/comments",
            "labels": [{"name": "bug"}, {"name": "urgent"}]
        }, request=httpx.Request("GET", url))
    elif url_str == "https://api.github.com/repos/owner/repo/issues/1/comments":
        return httpx.Response(200, json=[
            {"body": "Comment 1"},
            {"body": "Comment 2"}
        ], request=httpx.Request("GET", url))
    elif url_str == "https://api.github.com/repos/owner/repo/issues/2":
        return httpx.Response(404, request=httpx.Request("GET", url))
    return httpx.Response(500, request=httpx.Request("GET", url))

def mock_post(url, **kwargs):
    url_str = str(url)
    if url_str == "https://api.github.com/repos/owner/repo/pulls":
        return httpx.Response(201, json={"html_url": "https://github.com/owner/repo/pull/3"}, request=httpx.Request("POST", url))
    return httpx.Response(500, request=httpx.Request("POST", url))

def test_fetch_issue_parses_all_fields(monkeypatch):
    monkeypatch.setattr(httpx, "get", mock_get)
    issue_url = "https://github.com/owner/repo/issues/1"
    
    res = fetch_issue(issue_url)
    assert res["title"] == "Test Issue"
    assert res["body"] == "This is a bug."
    assert res["comments"] == ["Comment 1", "Comment 2"]
    assert res["labels"] == ["bug", "urgent"]
    assert "linked_prs" in res

def test_fetch_issue_handles_api_error_cleanly(monkeypatch):
    monkeypatch.setattr(httpx, "get", mock_get)
    issue_url = "https://github.com/owner/repo/issues/2"
    
    res = fetch_issue(issue_url)
    assert "error" in res

def test_create_draft_pr_requires_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    res = create_draft_pr("https://github.com/owner/repo", "test-branch", "diff", "title", "body")
    assert res["error"] == "token required"

def test_create_draft_pr_dry_run_succeeds(monkeypatch):
    monkeypatch.setattr(httpx, "post", mock_post)
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")
    
    res = create_draft_pr("https://github.com/owner/repo", "test-branch", "diff", "title", "body")
    assert "html_url" in res
