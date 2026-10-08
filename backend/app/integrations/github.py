import httpx
import os
import re

def fetch_issue(issue_url: str) -> dict:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_url)
    if not match:
        return {"error": "Invalid GitHub issue URL"}
    
    owner, repo, issue_number = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        
    try:
        response = httpx.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        comments_url = data.get("comments_url")
        comments_data = []
        if comments_url and data.get("comments", 0) > 0:
            c_resp = httpx.get(comments_url, headers=headers)
            c_resp.raise_for_status()
            comments_data = [c["body"] for c in c_resp.json()]
            
        labels = [l["name"] for l in data.get("labels", [])]
        
        return {
            "title": data.get("title", ""),
            "body": data.get("body", "") or "",
            "comments": comments_data,
            "labels": labels,
            "linked_prs": [] # Mocked empty for now
        }
    except httpx.HTTPError as e:
        return {"error": f"Failed to fetch issue: {str(e)}"}

def create_draft_pr(repo_url: str, branch_name: str, diff: str, title: str, body: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"error": "token required"}
        
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if not match:
        return {"error": "Invalid repository URL"}
    owner, repo = match.groups()
    repo = repo.replace(".git", "")
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}"
    }
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    
    payload = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": "main",
        "draft": True
    }
    
    try:
        response = httpx.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        return {"error": f"Failed to create PR: {str(e)}"}
