"""
LangGraph StateGraph Workflow with MemorySaver and HITL Interrupts for RepoMind.
"""

from typing import Dict, Any, Optional
import sys
import os

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in [backend_dir, app_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

try:
    from app.agent.state import RepoMindState
    from app.agent.nodes import issue_parser_node, tree_search_node, patch_generator_node
except ImportError:
    from agent.state import RepoMindState  # type: ignore
    from agent.nodes import issue_parser_node, tree_search_node, patch_generator_node  # type: ignore


def hitl_interrupt_node(state: RepoMindState) -> Dict[str, Any]:
    """
    Node 4: Pauses execution after patch generator to wait for Maintainer HITL approval.
    """
    # Trigger LangGraph HITL interrupt
    resume_val = interrupt({
        "status": "WAITING_FOR_APPROVAL",
        "patch": state.get("suggested_patch", ""),
        "message": "Maintainer approval required to proceed or apply patch."
    })

    # When resumed via Command(resume={...})
    action = resume_val.get("action", "APPROVED") if isinstance(resume_val, dict) else "APPROVED"
    custom_patch = resume_val.get("patch", "") if isinstance(resume_val, dict) else ""

    logs = list(state.get("execution_logs", []))
    logs.append({
        "step": "hitl_approval",
        "timestamp": "",
        "action": action,
        "message": f"Maintainer action: {action}"
    })

    return {
        "approval_status": action,
        "suggested_patch": custom_patch if (action == "EDITED" and custom_patch) else state.get("suggested_patch", ""),
        "execution_logs": logs
    }


def build_repomind_graph(search_engine=None):
    """
    Constructs and returns the compiled LangGraph StateGraph with MemorySaver checkpointer.
    """
    workflow = StateGraph(RepoMindState)

    # Wrap nodes to pass search_engine
    def _parse(state: RepoMindState):
        return issue_parser_node(state, search_engine)

    def _search(state: RepoMindState):
        return tree_search_node(state, search_engine)

    def _patch(state: RepoMindState):
        return patch_generator_node(state, search_engine)

    workflow.add_node("issue_parser", _parse)
    workflow.add_node("tree_search", _search)
    workflow.add_node("patch_generator", _patch)
    workflow.add_node("hitl_interrupt", hitl_interrupt_node)

    # Edge definitions
    workflow.add_edge(START, "issue_parser")
    workflow.add_edge("issue_parser", "tree_search")
    workflow.add_edge("tree_search", "patch_generator")
    workflow.add_edge("patch_generator", "hitl_interrupt")
    workflow.add_edge("hitl_interrupt", END)

    checkpointer = MemorySaver()
    compiled_app = workflow.compile(checkpointer=checkpointer)
    return compiled_app
