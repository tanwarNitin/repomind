from typing import TypedDict, List, Dict, Any, Annotated
import operator

def add_logs(left: List[str], right: List[str]) -> List[str]:
    return left + right

class Evidence(TypedDict):
    file: str
    start_line: int
    end_line: int
    why: str

class AgentState(TypedDict):
    repo_id: str
    raw_issue: str
    sanitized_issue: str
    redacted_count: int
    retrieved_slices: List[Dict[str, Any]]
    plan: str
    evidence: List[Evidence]
    patch_diff: str
    verification_result: str
    approval_status: str
    execution_logs: Annotated[List[str], add_logs]
    total_tokens: int
    messages: Annotated[List[Any], operator.add]
    tool_iterations: int
