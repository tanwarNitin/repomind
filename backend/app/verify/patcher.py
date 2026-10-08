import os
import subprocess
import re

def apply_patch(repo_copy_path: str, unified_diff: str) -> dict:
    """
    Applies a unified diff to a COPY of the ingested repo in a temp dir.
    Returns {ok, applied_files} or {ok: False, error}.
    """
    patch_file = os.path.join(repo_copy_path, "temp.patch")
    try:
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(unified_diff)
            
        # check patch first
        check_cmd = ["git", "apply", "--check", "--unidiff-zero", patch_file]
        res = subprocess.run(check_cmd, cwd=repo_copy_path, capture_output=True, text=True)
        if res.returncode != 0:
            return {"ok": False, "error": res.stderr}
            
        # apply
        apply_cmd = ["git", "apply", "--unidiff-zero", patch_file]
        res = subprocess.run(apply_cmd, cwd=repo_copy_path, capture_output=True, text=True)
        if res.returncode != 0:
            return {"ok": False, "error": res.stderr}
            
        # get applied files
        files = []
        for line in unified_diff.splitlines():
            if line.startswith("diff --git a/"):
                match = re.match(r"^diff --git a/(.*?) b/", line)
                if match:
                    files.append(match.group(1))
        
        return {"ok": True, "applied_files": list(set(files))}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        if os.path.exists(patch_file):
            try:
                os.remove(patch_file)
            except:
                pass
