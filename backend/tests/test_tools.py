import os
import pytest
from app.agent.tools import read_file, grep, symbol_lookup, git_log_recent
from app.core.ingest import ingest_repo

@pytest.fixture(scope="module")
def fixture_repo_id():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
    res = ingest_repo(fixture_path)
    return res["repo_id"]

def test_read_file_rejects_path_traversal(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = read_file.invoke({"path": "../../etc/passwd", "start": 1, "end": 10}, config=config)
    assert isinstance(res, str)
    assert "Path traversal" in res

def test_read_file_missing_returns_error(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = read_file.invoke({"path": "does_not_exist.py", "start": 1, "end": 10}, config=config)
    assert isinstance(res, str)
    assert "Error: File" in res

def test_read_file(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = read_file.invoke({"path": "utils.py", "start": 1, "end": 2}, config=config)
    assert isinstance(res, str)
    lines = res.splitlines()
    assert len(lines) == 2

def test_grep_no_matches_returns_empty(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = grep.invoke({"pattern": "NON_EXISTENT_PATTERN_XYZ_123", "path": ""}, config=config)
    assert isinstance(res, list)
    assert len(res) == 0

def test_grep(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = grep.invoke({"pattern": "def ", "path": ""}, config=config)
    assert len(res) > 0
    
    res = grep.invoke({"pattern": "def ", "path": "../../etc/passwd"}, config=config)
    assert isinstance(res, list)
    assert len(res) == 1
    assert "Path traversal" in res[0]

def test_symbol_lookup_unknown_returns_empty(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = symbol_lookup.invoke({"name": "nonExistentSymbolXYZ"}, config=config)
    assert isinstance(res, list)
    assert len(res) == 0

def test_symbol_lookup(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = symbol_lookup.invoke({"name": "parse_date"}, config=config)
    assert len(res) > 0

def test_git_log_recent_non_git_degrades(fixture_repo_id):
    config = {"configurable": {"repo_id": fixture_repo_id}}
    res = git_log_recent.invoke({"path": "utils.py", "n": 5}, config=config)
    assert isinstance(res, str)
    assert "Error: Not a git repository." in res
