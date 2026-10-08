"""
LangGraph TypedDict State Schema for RepoMind.
"""

from typing import TypedDict, List, Dict, Any, Optional


class RepoMindState(TypedDict):
    messages: List[Dict[str, Any]]
    raw_issue: str
    sanitized_issue: str
    redacted_secrets: List[str]
    retrieved_context: List[Dict[str, Any]]
    suggested_patch: str
    approval_status: str  # "PENDING" | "APPROVED" | "REJECTED" | "EDITED"
    user_edited_patch: Optional[str]
    execution_logs: List[Dict[str, Any]]
    total_cost: float
    total_tokens: int
