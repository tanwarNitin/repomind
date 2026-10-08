import os
from app.evals.run_evals import run_retrieval_evals, run_patch_evals, run_all

def test_eval_retrieval_hit_rate_at_3():
    res = run_retrieval_evals()
    assert res["hit_at_3"] == 1.0

def test_eval_patch_apply_rate():
    res = run_patch_evals()
    assert res["apply_rate"] == 1.0

def test_eval_report_renders_markdown():
    run_all()
    evals_dir = os.path.join(os.path.dirname(__file__), "..", "evals")
    report_path = os.path.join(evals_dir, "report.md")
    
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "# RepoMind Evals Report" in content
    assert "Hit-Rate@3" in content
    assert "Apply-Rate" in content
    assert "Targeted-Test-Selection Precision" in content
