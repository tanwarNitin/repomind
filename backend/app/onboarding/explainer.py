import os
from typing import Dict, Any, List
from litellm import completion
from app.core.config import settings
from app.core.search import query_repo, _indexes
from app.core.ingest import get_repos

def get_repo_files(repo_id: str) -> List[str]:
    """Helper to get a list of all files in the indexed repo to generate the module map."""
    if repo_id not in _indexes:
        return []
    docs = _indexes[repo_id]["docs"]
    return list(set(doc["file"] for doc in docs))

def generate_explanation(repo_id: str) -> str:
    repos = get_repos()
    if repo_id not in repos:
        raise ValueError(f"Repo {repo_id} not found")
        
    files = get_repo_files(repo_id)
    files_str = "\n".join(files)
    
    # We want to use the "Part 2 retrieval + reasoner router" to fetch context.
    # We can just query for general architecture words.
    context_results = query_repo(repo_id, "main setup init config index application entry app module", top_k=10)
    
    context_str = ""
    for r in context_results:
        context_str += f"File: {r['file']}, Lines {r['start_line']}-{r['end_line']}\n"
        context_str += f"{r['snippet']}\n\n"
        
    prompt = f"""
    You are an expert software architect.
    Your task is to write a newcomer's architecture overview for this repository.
    
    You must format it as Markdown with the following EXACT sections:
    - entry points
    - module map (what each top-level module does)
    - core logic locations (with file:line citations)
    - suggested first-issue areas
    
    Repository Files:
    {files_str}
    
    Retrieved Context:
    {context_str}
    
    CRITICAL INSTRUCTION: Every factual claim in your explanation MUST cite evidence entries in the format (File:line) based ONLY on the Retrieved Context. Do not invent any files or citations.
    """
    
    # Check if API keys are set for litellm
    import litellm
    # We can just let litellm pick up from env, but let's pass explicitly if needed.
    # Actually, in mock mode for testing, we should check MOCK_RESPONSES.
    from app.core.gateway import is_mock_mode, MOCK_RESPONSES
    if is_mock_mode() and MOCK_RESPONSES:
        mock_msg = MOCK_RESPONSES.pop(0)
        return mock_msg.content

    api_key = os.environ.get("GEMINI_API_KEY")
    model = "gemini/gemini-flash-latest"
    
    try:
        res = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Error generating explanation: {e}"
