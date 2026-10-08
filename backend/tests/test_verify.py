import os
import tempfile
import shutil
import pytest
from langchain_core.runnables import RunnableConfig
from app.verify.patcher import apply_patch
from app.verify.test_selector import select_tests
from app.verify.test_runner import run_tests
from app.verify.security_scan import scan_diff
from app.agent.nodes import verifier, _handle_verification_failure
from app.agent.state import AgentState
from app.core.ingest import ingest_repo, get_repos

@pytest.fixture
def sample_repo():
    with tempfile.TemporaryDirectory() as td:
        repo_dir = os.path.join(td, "repo")
        os.makedirs(repo_dir)
        
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
        
        code = "def my_func():\n    return 42\n\ndef other_func():\n    return 0\n"
        with open(os.path.join(repo_dir, "main.py"), "w") as f:
            f.write(code)
            
        os.makedirs(os.path.join(repo_dir, "tests"))
        test_code = "from main import my_func\n\ndef test_my_func():\n    assert my_func() == 42\n"
        with open(os.path.join(repo_dir, "tests", "test_main.py"), "w") as f:
            f.write(test_code)
            
        test_other = "from main import other_func\n\ndef test_other():\n    assert other_func() == 0\n"
        with open(os.path.join(repo_dir, "tests", "test_other.py"), "w") as f:
            f.write(test_other)
            
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)
        
        yield repo_dir

def test_apply_patch_leaves_original_untouched(sample_repo):
    original_mtime = os.path.getmtime(os.path.join(sample_repo, "main.py"))
    diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
 def my_func():
-    return 42
+    return 43
"""
    with tempfile.TemporaryDirectory() as td:
        copy_dir = os.path.join(td, "copy")
        shutil.copytree(sample_repo, copy_dir)
        res = apply_patch(copy_dir, diff)
        assert res["ok"]
        
        # original untouched
        with open(os.path.join(sample_repo, "main.py")) as f:
            assert "return 42" in f.read()

def test_apply_malformed_patch_returns_error(sample_repo):
    diff = "garbage patch"
    with tempfile.TemporaryDirectory() as td:
        copy_dir = os.path.join(td, "copy")
        shutil.copytree(sample_repo, copy_dir)
        res = apply_patch(copy_dir, diff)
        assert not res["ok"]

def test_targeted_selection_finds_affected_tests(sample_repo):
    diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
 def my_func():
-    return 42
+    return 43
"""
    tests = select_tests(sample_repo, diff)
    assert any("test_main.py" in t for t in tests)
    assert not any("test_other.py" in t for t in tests)

def test_targeted_selection_falls_back_when_inconclusive(sample_repo):
    diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,1 +1,2 @@
 # Test
+new line
"""
    tests = select_tests(sample_repo, diff)
    assert tests == [] # full suite

def test_verifier_retries_exactly_once_on_test_failure():
    state = {"verifier_retries": 0, "messages": [], "execution_logs": []}
    res1 = _handle_verification_failure(state, "test failed")
    assert res1["verifier_retries"] == 1
    
    state2 = {"verifier_retries": 1, "messages": [], "execution_logs": []}
    res2 = _handle_verification_failure(state2, "test failed again")
    assert "verification_result" in res2
    assert "Failed after retries" in res2["verification_result"]

def test_verifier_proceeds_to_hitl_after_retry_exhausted():
    from app.agent.nodes import should_continue_verifier
    state = {"execution_logs": ["Verifier: Tests failed, exhausted retries"]}
    assert should_continue_verifier(state) == "hitl_interrupt"

def test_security_scan_blocks_secret_in_diff():
    diff = "+ jwt_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI.eyJzdWIiOiIxMjM0NTY3ODkw.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'"
    res = scan_diff(diff)
    assert not res["clean"]
    assert "JWT token found" in res["findings"]

def test_security_scan_clean_diff_passes():
    diff = "+ x = 5"
    assert scan_diff(diff)["clean"]

def test_full_verifier_node_passes_good_patch(sample_repo):
    res = ingest_repo(sample_repo)
    repo_id = res["repo_id"]
    
    diff = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
 def my_func():
-    return 42
+    return 42
"""
    state = {"repo_id": repo_id, "patch_diff": diff, "execution_logs": [], "messages": []}
    res = verifier(state, RunnableConfig())
    assert "Passed" in res.get("verification_result", "")
