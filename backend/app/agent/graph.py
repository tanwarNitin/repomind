from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os

from app.core.config import settings
from .state import AgentState
from .nodes import issue_parser, researcher, execute_tools, patch_generator, hitl_interrupt, should_continue_researcher, should_continue_patch

def build_graph():
    builder = StateGraph(AgentState)

    from .nodes import issue_parser, researcher, execute_tools, patch_generator, verifier, hitl_interrupt, should_continue_researcher, should_continue_patch, should_continue_verifier

    builder.add_node("issue_parser", issue_parser)
    builder.add_node("researcher", researcher)
    builder.add_node("execute_tools", execute_tools)
    builder.add_node("patch_generator", patch_generator)
    builder.add_node("verifier", verifier)
    builder.add_node("hitl_interrupt", hitl_interrupt)

    builder.add_edge(START, "issue_parser")
    builder.add_edge("issue_parser", "researcher")

    builder.add_conditional_edges("researcher", should_continue_researcher, {
        "execute_tools": "execute_tools",
        "patch_generator": "patch_generator"
    })
    
    builder.add_edge("execute_tools", "researcher")
    
    builder.add_conditional_edges("patch_generator", should_continue_patch, {
        "researcher": "researcher",
        "verifier": "verifier"
    })

    builder.add_conditional_edges("verifier", should_continue_verifier, {
        "patch_generator": "patch_generator",
        "hitl_interrupt": "hitl_interrupt"
    })
    
    builder.add_edge("hitl_interrupt", END)

    # Use checkpointer matching db.py
    # db.py uses sqlite:///./repomind.db
    # We will use the same file
    db_path = "repomind.db"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["hitl_interrupt"])

app_graph = build_graph()
