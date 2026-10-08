import os
import re
from app.core.ast_index import parse_file

def select_tests(repo_path: str, unified_diff: str) -> list:
    """
    Parse the diff's changed symbols, use the Part 2 AST index to build a call graph,
    return only the test files/functions that touch changed symbols. 
    Falls back to the full suite when the graph is inconclusive.
    """
    changed_symbols = set()
    current_file = None
    
    changed_lines = set()
    current_line = 0
    
    # Parse diff to find changed files and lines
    for line in unified_diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"@@ \-\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                current_line = int(match.group(1))
            # try to extract symbol from diff hunk header context as fallback
            ctx_match = re.search(r"@@.*@@\s*(def|class)\s+([a-zA-Z0-9_]+)", line)
            if ctx_match:
                changed_symbols.add(ctx_match.group(2))
        elif line.startswith("+") and not line.startswith("+++"):
            changed_lines.add(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass
        elif not line.startswith("\\"):
            # context line
            current_line += 1
    
    # If we couldn't find symbols via diff context, try to parse the changed files in repo_path
    if not changed_symbols and current_file and changed_lines:
        file_path = os.path.join(repo_path, current_file)
        if os.path.exists(file_path):
            symbols = parse_file(file_path)
            for s in symbols:
                if any(s["start_line"] <= l <= s["end_line"] for l in changed_lines):
                    changed_symbols.add(s["name"])
                
    if not changed_symbols:
        return [] # full suite
        
    selected_tests = []
    tests_dir = os.path.join(repo_path, "tests")
    if not os.path.exists(tests_dir) and os.path.exists(os.path.join(repo_path, "backend", "tests")):
        tests_dir = os.path.join(repo_path, "backend", "tests")
        
    if not os.path.exists(tests_dir):
        return []

    # naive call graph: check if test file contains the symbol
    for root, dirs, files in os.walk(tests_dir):
        for f in files:
            if f.startswith("test_") and f.endswith(".py"):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "r", encoding="utf-8") as file:
                        content = file.read()
                        if any(sym in content for sym in changed_symbols):
                            # We can also parse the test file to get test functions
                            test_symbols = parse_file(fpath)
                            added_specific = False
                            for ts in test_symbols:
                                if ts["name"].startswith("test_"):
                                    # check if this specific function contains the symbol
                                    # this is an approximation
                                    func_code_lines = content.splitlines()[ts["start_line"]-1:ts["end_line"]]
                                    func_code = "\n".join(func_code_lines)
                                    if any(sym in func_code for sym in changed_symbols):
                                        rel_path = os.path.relpath(fpath, repo_path).replace("\\", "/")
                                        selected_tests.append(f"{rel_path}::{ts['name']}")
                                        added_specific = True
                            
                            if not added_specific:
                                rel_path = os.path.relpath(fpath, repo_path).replace("\\", "/")
                                selected_tests.append(rel_path)
                except:
                    pass

    return selected_tests
