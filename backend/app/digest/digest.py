import httpx
import re
import os
import json
from app.core.db import SessionLocal, Digest, Repo
from litellm import completion
from .duplicates import find_duplicates

def generate_digest_report(repo_id: str):
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.repo_id == repo_id).first()
        if not repo:
            raise ValueError("Repo not found")
            
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo.source)
        if not match:
            raise ValueError("Only GitHub repos supported for digest")
            
        owner, repo_name = match.groups()
        repo_name = repo_name.replace(".git", "")
        
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues?state=open"
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            
        resp = httpx.get(api_url, headers=headers)
        resp.raise_for_status()
        issues_data = resp.json()
        
        # Keep only actual issues (not PRs)
        issues_data = [i for i in issues_data if "pull_request" not in i]
        
        existing_issues = []
        assessed_issues = []
        
        for issue in issues_data:
            issue_id = str(issue["number"])
            title = issue["title"]
            body = issue["body"] or ""
            
            # Duplicate check
            dups = find_duplicates({"title": title, "body": body}, existing_issues)
            duplicate_of = dups[0]["issue_id"] if dups and dups[0]["is_duplicate"] else None
            
            existing_issues.append({"id": issue_id, "title": title, "body": body})
            
            # Light triage
            parsed = parse_issue(f"{title}\n{body}") if "parse_issue" in globals() else {"core_problem": title}
            context = retrieve_context(repo_id, title) if "retrieve_context" in globals() else []
            
            prompt = f"""
Assess this issue for severity (1-10) and confidence (1-10) in our ability to auto-fix it.
Issue: {title}
{body}

Context:
{context}

Respond in JSON only:
{{"severity": 8, "confidence": 5, "summary": "Short summary", "evidence_refs": ["file.py"]}}
"""
            # Minimal LLM call
            res = completion(
                model="gemini/gemini-1.5-flash",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            try:
                assessment = json.loads(res.choices[0].message.content)
            except Exception:
                assessment = {"severity": 5, "confidence": 5, "summary": title, "evidence_refs": []}
                
            score = assessment.get("severity", 0) * assessment.get("confidence", 0)
            
            assessed_issues.append({
                "id": issue_id,
                "title": title,
                "url": issue["html_url"],
                "severity": assessment.get("severity", 0),
                "confidence": assessment.get("confidence", 0),
                "score": score,
                "summary": assessment.get("summary", ""),
                "evidence_refs": assessment.get("evidence_refs", []),
                "duplicate_of": duplicate_of
            })
            
        # Rank by severity x confidence
        assessed_issues.sort(key=lambda x: x["score"], reverse=True)
        
        # Render markdown
        lines = [f"# Digest Report for {repo.source}", ""]
        for ai in assessed_issues:
            dup_text = f" (Duplicate of #{ai['duplicate_of']})" if ai["duplicate_of"] else ""
            lines.append(f"## [#{ai['id']}] {ai['title']}{dup_text}")
            lines.append(f"**Severity**: {ai['severity']} | **Confidence**: {ai['confidence']} | **Score**: {ai['score']}")
            lines.append(f"**Summary**: {ai['summary']}")
            if ai['evidence_refs']:
                lines.append(f"**Evidence**: {', '.join(ai['evidence_refs'])}")
            lines.append("")
            
        markdown_report = "\n".join(lines)
        
        digest = Digest(repo_id=repo_id, markdown_report=markdown_report)
        db.add(digest)
        db.commit()
        db.refresh(digest)
        return digest.id
    finally:
        db.close()

def get_digest(digest_id: int):
    db = SessionLocal()
    try:
        digest = db.query(Digest).filter(Digest.id == digest_id).first()
        if not digest:
            return None
        return {"id": digest.id, "repo_id": digest.repo_id, "markdown_report": digest.markdown_report, "created_at": digest.created_at}
    finally:
        db.close()
