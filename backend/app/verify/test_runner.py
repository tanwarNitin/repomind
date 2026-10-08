import subprocess
import os

def run_tests(workdir: str, test_files: list) -> dict:
    """
    Runs pytest on the selected tests (timeout 120s).
    Returns {passed, failed, failures_summary (last ~40 lines)}.
    """
    if not test_files:
        test_files = ["tests"] # default to running all tests if list is empty
        
    # Assuming pytest is available in the environment running this,
    # or we can use `python -m pytest`
    import sys
    cmd = [sys.executable, "-m", "pytest"] + test_files
    
    try:
        res = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=120)
        passed = res.returncode == 0
        
        failures_summary = ""
        if not passed:
            lines = res.stdout.splitlines() + res.stderr.splitlines()
            failures_summary = "\n".join(lines[-40:])
            
        return {
            "passed": passed,
            "failed": not passed,
            "failures_summary": failures_summary
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "failed": True,
            "failures_summary": "Test execution timed out after 120 seconds."
        }
    except Exception as e:
        return {
            "passed": False,
            "failed": True,
            "failures_summary": str(e)
        }
