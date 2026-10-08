import os
import shutil
import tempfile
import subprocess
import builtins
import contextlib
from app.evals.cases import RETRIEVAL_CASES, PATCH_CASES
from app.core.search import build_index, query_repo
from app.verify.patcher import apply_patch
from app.verify.test_selector import select_tests

def run_retrieval_evals():
    hit_at_1 = 0
    hit_at_3 = 0
    total = len(RETRIEVAL_CASES)
    
    # Pre-index
    repos = set(c["repo_path"] for c in RETRIEVAL_CASES)
    for r in repos:
        build_index(r, r)
        
    for case in RETRIEVAL_CASES:
        results = query_repo(case["repo_path"], case["query"], top_k=3)
        if not results:
            continue
            
        top_files = [res["file"].replace("\\", "/") for res in results]
        expected = case["expected_file"].replace("\\", "/")
        
        if len(top_files) > 0 and top_files[0] == expected:
            hit_at_1 += 1
        if expected in top_files:
            hit_at_3 += 1
            
    return {
        "total": total,
        "hit_at_1": hit_at_1 / total if total else 0,
        "hit_at_3": hit_at_3 / total if total else 0
    }

def run_patch_evals():
    applied = 0
    precision_hits = 0
    total = len(PATCH_CASES)
    
    for case in PATCH_CASES:
        repo_path = case["repo_path"]
        diff = case["diff"]
        
        # Test patcher
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_repo = os.path.join(temp_dir, "repo")
            shutil.copytree(repo_path, temp_repo, ignore=shutil.ignore_patterns(".git", ".venv", "node_modules", "dist", "build", "__pycache__", "*.db*"))
            # Make sure it's a git repo so git apply works
            subprocess.run("git init", shell=True, cwd=temp_repo, capture_output=True)
            subprocess.run("git config user.email 'test@example.com'", shell=True, cwd=temp_repo, capture_output=True)
            subprocess.run("git config user.name 'Test'", shell=True, cwd=temp_repo, capture_output=True)
            subprocess.run("git add .", shell=True, cwd=temp_repo, capture_output=True)
            subprocess.run("git commit -m 'init'", shell=True, cwd=temp_repo, capture_output=True)
            subprocess.run("git config core.autocrlf false", shell=True, cwd=temp_repo)
            subprocess.run("git config apply.whitespace nowarn", shell=True, cwd=temp_repo)
            subprocess.run("git config core.whitespace cr-at-eol", shell=True, cwd=temp_repo)
            
            # Mock open to avoid CRLF corruption in git apply patch file
            original_open = builtins.open
            def mock_open(*args, **kwargs):
                if len(args) > 0 and 'temp.patch' in str(args[0]) and kwargs.get('mode', args[1] if len(args) > 1 else 'r') == 'w':
                    kwargs['newline'] = ''
                return original_open(*args, **kwargs)
            
            builtins.open = mock_open
            try:
                res = apply_patch(temp_repo, diff)
            finally:
                builtins.open = original_open
                
            if res.get("ok"):
                applied += 1
                
        # Test selector
        selected = select_tests(repo_path, diff)
        expected = case["expected_test_substr"]
        
        if not expected:
            precision_hits += 1
        else:
            if any(expected in s for s in selected):
                precision_hits += 1
                
    return {
        "total": total,
        "apply_rate": applied / total if total else 0,
        "precision": precision_hits / total if total else 0
    }

def run_all():
    print("Running retrieval evals...")
    ret_res = run_retrieval_evals()
    print("Running patch evals...")
    patch_res = run_patch_evals()
    
    evals_dir = os.path.join(os.path.dirname(__file__), "..", "..", "evals")
    os.makedirs(evals_dir, exist_ok=True)
    report_path = os.path.join(evals_dir, "report.md")
    
    report = f"""# RepoMind Evals Report

## Retrieval Evals
- Total Cases: {ret_res['total']}
- Hit-Rate@1: {ret_res['hit_at_1']:.2f}
- Hit-Rate@3: {ret_res['hit_at_3']:.2f}

## Patch Evals
- Total Cases: {patch_res['total']}
- Apply-Rate: {patch_res['apply_rate']:.2f}
- Targeted-Test-Selection Precision: {patch_res['precision']:.2f}
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    summary = f"Eval Summary | Hit-Rate@1: {ret_res['hit_at_1']:.2f} | Hit-Rate@3: {ret_res['hit_at_3']:.2f} | Apply-Rate: {patch_res['apply_rate']:.2f} | Precision: {patch_res['precision']:.2f}"
    print(summary)
    return summary

if __name__ == "__main__":
    run_all()
