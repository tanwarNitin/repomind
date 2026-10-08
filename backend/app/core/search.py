import os
from rank_bm25 import BM25Okapi
from .ast_index import parse_file

# In-memory cache for search indices
# repo_id -> {"bm25": BM25Okapi, "docs": list of dict, "repo_path": str}
_indexes = {}

def tokenize(text: str) -> list[str]:
    return text.lower().replace("_", " ").replace("-", " ").split()

def build_index(repo_id: str, repo_path: str):
    docs = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "dist", "build"]]
        
        for file in files:
            if file.startswith(".") or file.endswith(".lock"):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
                
            # Add file-level document
            lines = content.splitlines()
            docs.append({
                "file": rel_path,
                "start_line": 1,
                "end_line": len(lines),
                "snippet": content[:500] + ("..." if len(content) > 500 else ""),
                "text": content
            })
            
            # Add symbol-level documents
            symbols = parse_file(file_path)
            for sym in symbols:
                start = sym["start_line"] - 1
                end = sym["end_line"]
                snippet_lines = lines[start:end]
                sym_text = "\n".join(snippet_lines)
                docs.append({
                    "file": rel_path,
                    "start_line": sym["start_line"],
                    "end_line": sym["end_line"],
                    "snippet": sym_text[:500] + ("..." if len(sym_text) > 500 else ""),
                    "text": sym["name"] + " " + sym_text
                })

    tokenized_corpus = [tokenize(doc["text"]) for doc in docs]
    if tokenized_corpus:
        bm25 = BM25Okapi(tokenized_corpus)
    else:
        bm25 = None
        
    _indexes[repo_id] = {
        "bm25": bm25,
        "docs": docs,
        "repo_path": repo_path
    }
    
    return {"files_indexed": len(set(d["file"] for d in docs)), "symbols_indexed": len(docs) - len(set(d["file"] for d in docs))}

def query_repo(repo_id: str, query_text: str, top_k: int = 3):
    if repo_id not in _indexes:
        return []
    
    index_data = _indexes[repo_id]
    bm25 = index_data["bm25"]
    docs = index_data["docs"]
    
    if not bm25 or not docs:
        return []
        
    tokenized_query = tokenize(query_text)
    scores = bm25.get_scores(tokenized_query)
    
    results = []
    for i, score in enumerate(scores):
        if score > 0:
            results.append((score, docs[i]))
            
    results.sort(key=lambda x: x[0], reverse=True)
    
    final_results = []
    for score, doc in results[:top_k]:
        final_results.append({
            "file": doc["file"],
            "start_line": doc["start_line"],
            "end_line": doc["end_line"],
            "snippet": doc["snippet"],
            "score": score
        })
        
    return final_results
