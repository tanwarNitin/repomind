from app.core.guardrails import EMAIL_REGEX, PRIVATE_KEY_REGEX, AWS_KEY_REGEX, JWT_REGEX, GITHUB_TOKEN_REGEX
import re

def scan_diff(unified_diff: str) -> dict:
    """
    Scans the unified diff for leaked secrets and obvious injection patterns.
    Returns {clean} or {clean: False, findings}.
    """
    findings = []
    
    if re.search(PRIVATE_KEY_REGEX, unified_diff):
        findings.append("Private key found")
    if re.search(AWS_KEY_REGEX, unified_diff):
        findings.append("AWS key found")
    if re.search(JWT_REGEX, unified_diff):
        findings.append("JWT token found")
    if re.search(GITHUB_TOKEN_REGEX, unified_diff):
        findings.append("GitHub token found")
        
    # Injection patterns (sql, xss, etc)
    if re.search(r'execute\s*\(\s*f["\'].*\{.*\}', unified_diff) or re.search(r'execute\s*\(\s*["\'].*%\s*[a-zA-Z]', unified_diff):
        findings.append("Potential SQL injection")
        
    if re.search(r'eval\s*\(', unified_diff) or re.search(r'exec\s*\(', unified_diff):
        findings.append("Usage of eval/exec")
        
    if findings:
        return {"clean": False, "findings": findings}
    return {"clean": True}
