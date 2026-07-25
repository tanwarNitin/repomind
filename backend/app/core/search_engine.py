"""
Hybrid Vectorless RAG Engine for RepoMind.
Uses Rank-BM25 to index repository files and intersects search results with Tree-sitter AST JSON symbols.
Produces exact code slices (start_line to end_line) without vector embeddings.
"""

from typing import List, Dict, Any, Optional
import re
from rank_bm25 import BM25Okapi


class VectorlessSearchEngine:
    """
    RAG search engine combining BM25 keyword ranking with AST line bounding.
    """

    def __init__(self, repo_files: Optional[Dict[str, str]] = None, ast_map: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.repo_files: Dict[str, str] = repo_files or {}
        self.ast_map: Dict[str, List[Dict[str, Any]]] = ast_map or {}
        self.corpus_documents: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        
        if self.repo_files:
            self._build_index()

    def update_index(self, repo_files: Dict[str, str], ast_map: Dict[str, List[Dict[str, Any]]]):
        """Updates the repository files, AST mapping, and rebuilds the BM25 index."""
        self.repo_files = repo_files
        self.ast_map = ast_map
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Simple code tokenizer breaking by non-alphanumeric characters."""
        return [token.lower() for token in re.findall(r'[A-Za-z0-9_]+', text) if len(token) > 1]

    def _build_index(self):
        """Builds BM25 documents at both file level and AST symbol level."""
        self.corpus_documents = []
        tokenized_corpus = []

        for file_path, content in self.repo_files.items():
            symbols = self.ast_map.get(file_path, [])
            lines = content.splitlines()

            if symbols:
                for sym in symbols:
                    start_l = max(1, sym.get("start_line", 1))
                    end_l = min(len(lines), sym.get("end_line", len(lines)))
                    snippet_lines = lines[start_l - 1:end_l]
                    snippet = "\n".join(snippet_lines)

                    doc_text = f"{file_path} {sym.get('name', '')} {sym.get('type', '')} {snippet}"
                    tokens = self._tokenize(doc_text)

                    self.corpus_documents.append({
                        "file_path": file_path,
                        "symbol_name": sym.get("name", "Unknown"),
                        "symbol_type": sym.get("type", "block"),
                        "start_line": start_l,
                        "end_line": end_l,
                        "code_snippet": snippet,
                        "doc_text": doc_text
                    })
                    tokenized_corpus.append(tokens)
            else:
                # If no AST symbols found, index entire file in 30-line chunks
                chunk_size = 30
                for idx in range(0, max(1, len(lines)), chunk_size):
                    chunk_lines = lines[idx:idx + chunk_size]
                    snippet = "\n".join(chunk_lines)
                    doc_text = f"{file_path} {snippet}"
                    tokens = self._tokenize(doc_text)

                    self.corpus_documents.append({
                        "file_path": file_path,
                        "symbol_name": "global",
                        "symbol_type": "file_chunk",
                        "start_line": idx + 1,
                        "end_line": min(len(lines), idx + chunk_size),
                        "code_snippet": snippet,
                        "doc_text": doc_text
                    })
                    tokenized_corpus.append(tokens)

        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Intersects BM25 search results with Tree-sitter AST line ranges.
        Returns top_k code slices with file paths, symbol metadata, line numbers, and exact code.
        """
        if not self.bm25 or not self.corpus_documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.corpus_documents[:top_k]

        scores = self.bm25.get_scores(query_tokens)
        scored_docs = list(zip(scores, self.corpus_documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_keys = set()

        for score, doc in scored_docs:
            if len(results) >= top_k:
                break
            
            key = f"{doc['file_path']}:{doc['start_line']}-{doc['end_line']}"
            if key not in seen_keys:
                seen_keys.add(key)
                res = dict(doc)
                res["score"] = round(float(score), 4)
                results.append(res)

        return results
