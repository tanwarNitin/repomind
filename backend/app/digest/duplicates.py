from rank_bm25 import BM25Okapi
import re

def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [w.lower() for w in re.findall(r'\w+', text)]

def find_duplicates(new_issue: dict, existing_issues: list[dict], threshold=0.7) -> list[dict]:
    if not existing_issues:
        return []
        
    tokenized_corpus = [tokenize(issue.get("title", "") + " " + issue.get("body", "")) for issue in existing_issues]
    bm25 = BM25Okapi(tokenized_corpus)
    
    query_text = new_issue.get("title", "") + " " + new_issue.get("body", "")
    tokenized_query = tokenize(query_text)
    
    if not tokenized_query:
        return []
        
    scores = bm25.get_scores(tokenized_query)
    
    results = []
    for i, score in enumerate(scores):
        score = float(score)
        is_duplicate = bool(score > threshold)
        results.append({
            "issue_id": existing_issues[i]["id"],
            "score": score,
            "is_duplicate": is_duplicate
        })
        
    # sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
