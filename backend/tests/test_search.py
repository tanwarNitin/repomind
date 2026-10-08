import os
import pytest
from app.core.ingest import ingest_repo
from app.core.search import query_repo

def test_ingest_and_search_fixture():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
    
    # Ingest
    res = ingest_repo(fixture_path)
    repo_id = res["repo_id"]
    
    assert res["files_indexed"] >= 3
    assert res["symbols_indexed"] >= 3
    
    # Search for known symbol 'parse_date'
    results = query_repo(repo_id, "parse date from string", top_k=3)
    assert len(results) > 0
    found = False
    for r in results:
        if r["file"] == "utils.py" and r["start_line"] == 1:
            found = True
            break
    assert found, "Expected to find utils.py with parse_date function in top results"
    
    # Search for known symbol in JS
    results_js = query_repo(repo_id, "initializeApp", top_k=3)
    found_js = False
    for r in results_js:
        if r["file"] == "main.js" and r["start_line"] == 6:
            found_js = True
            break
    assert found_js, "Expected to find initializeApp in main.js"
    
    # Search for known symbol in TS
    results_ts = query_repo(repo_id, "performLogin", top_k=3)
    found_ts = False
    for r in results_ts:
        if r["file"] == "api.ts" and r["start_line"] == 6:
            found_ts = True
            break
    assert found_ts, "Expected to find performLogin in api.ts"
