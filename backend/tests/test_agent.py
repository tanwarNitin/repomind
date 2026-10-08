import os
import pytest
from app.core.ingest import ingest_repo
from app.agent.graph import app_graph
from app.core.gateway import MOCK_RESPONSES, is_mock_mode
from app.core.config import settings
from langchain_core.messages import AIMessage, HumanMessage

@pytest.fixture(scope="module")
def fixture_repo_id():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
    res = ingest_repo(fixture_path)
    return res["repo_id"]

@pytest.fixture(autouse=True)
def setup_mock(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    MOCK_RESPONSES.clear()

def test_agent_triage_loop(fixture_repo_id):
    assert is_mock_mode() is True
    
    # 1. issue_parser: no tools, returns JSON string
    MOCK_RESPONSES.append(AIMessage(content='{"files": ["utils.py"], "symbols": ["parse_date"]}'))
    
    # 2. researcher: let's give it 10 tool calls, so it loops 8 times, and on the 9th time it stops
    for i in range(10):
        content = ""
        if i >= 8:
            # On the 9th and 10th time, we still provide tool calls to simulate a stubborn LLM,
            # but we also provide valid JSON content so that when tools are stripped, it parses correctly.
            content = '{"plan": "fix stuff", "evidence": [{"file": "utils.py", "start_line": 1, "end_line": 10, "why": "because"}]}'
            
        MOCK_RESPONSES.append(AIMessage(
            content=content,
            tool_calls=[{"name": "read_file", "args": {"path": "utils.py", "start": 1, "end": 10}, "id": f"call_{i}"}]
        ))
    
    # 3. patch_generator: generates diff citing evidence
    MOCK_RESPONSES.append(AIMessage(content='```diff\n--- a/utils.py\n+++ b/utils.py\n@@ -1,3 +1,3 @@\n-def old_func():\n+def parse_date():\n```'))
    
    config = {"configurable": {"thread_id": "test_thread_1", "repo_id": fixture_repo_id}}
    state = {
        "repo_id": fixture_repo_id,
        "raw_issue": "Fix date parsing in utils.py",
        "approval_status": "PENDING"
    }
    
    # Run graph
    app_graph.invoke(state, config)
    
    final_state = app_graph.get_state(config).values
    
    # Check it reached HITL interrupt (pending)
    assert final_state["approval_status"] == "PENDING"
    assert "patch_diff" in final_state
    assert final_state["patch_diff"] != ""
    assert len(final_state["evidence"]) == 1
    
    # Verify execution logs covers every node
    logs = "\n".join(final_state["execution_logs"])
    assert "issue_parser extracted" in logs
    assert "researcher iteration 1" in logs
    assert "researcher iteration 8" in logs
    assert "patch_generator finished" in logs
    
    # Assert the run completes with exactly 8 tool_iterations
    assert final_state["tool_iterations"] == 8

def test_patch_generator_rejected_no_evidence(fixture_repo_id):
    # If researcher generates NO evidence, patch_generator rejects back to researcher once.
    MOCK_RESPONSES.clear()
    
    # 1. issue_parser
    MOCK_RESPONSES.append(AIMessage(content='{"files": [], "symbols": []}'))
    
    # 2. researcher gives NO evidence
    MOCK_RESPONSES.append(AIMessage(content='{"plan": "fix stuff", "evidence": []}'))
    
    # 3. patch_generator runs, sees no evidence, rejects and routes back to researcher
    # 4. researcher gives evidence this time
    MOCK_RESPONSES.append(AIMessage(content='{"plan": "fix stuff 2", "evidence": [{"file": "api.ts", "start_line": 1, "end_line": 2, "why": "ok"}]}'))
    
    # 5. patch_generator yields patch
    MOCK_RESPONSES.append(AIMessage(content='```diff\n--- a/api.ts\n+++ b/api.ts\n@@ -1,2 +1,2 @@\n-old\n+new\n```'))
    
    config = {"configurable": {"thread_id": "test_thread_2", "repo_id": fixture_repo_id}}
    state = {
        "repo_id": fixture_repo_id,
        "raw_issue": "Fix api.ts",
        "approval_status": "PENDING"
    }
    app_graph.invoke(state, config)
    final_state = app_graph.get_state(config).values
    assert final_state["patch_diff"] == "--- a/api.ts\n+++ b/api.ts\n@@ -1,2 +1,2 @@\n-old\n+new"
    assert "patch_generator rejected due to no evidence" in "\n".join(final_state["execution_logs"])

def test_resume_paths(fixture_repo_id):
    MOCK_RESPONSES.clear()
    
    config = {"configurable": {"thread_id": "test_thread_1"}} # same thread as test 1
    
    # Resume with APPROVED
    app_graph.update_state(config, {"approval_status": "APPROVED"}, as_node="hitl_interrupt")
    app_graph.invoke(None, config)
    assert app_graph.get_state(config).values["approval_status"] == "APPROVED"

def test_followup_preserves_history(fixture_repo_id):
    MOCK_RESPONSES.clear()
    
    # In followup, we resume from execute_tools
    # We must provide responses for researcher and patch_generator
    # 1. researcher tool call (or just plan + evidence)
    MOCK_RESPONSES.append(AIMessage(content='{"plan": "followup plan", "evidence": [{"file": "main.js", "start_line": 1, "end_line": 2, "why": "ok"}]}'))
    # 2. patch_generator diff
    MOCK_RESPONSES.append(AIMessage(content='```diff\n--- a/main.js\n+++ b/main.js\n@@ -1,2 +1,2 @@\n-a\n+b\n```'))
    
    config = {"configurable": {"thread_id": "test_thread_1"}}
    new_msg = HumanMessage(content="Please also check main.js")
    
    app_graph.update_state(config, {"messages": [new_msg]}, as_node="execute_tools")
    app_graph.invoke(None, config)
    
    final_state = app_graph.get_state(config).values
    assert "main.js" in final_state["patch_diff"]
    
    # history intact
    msgs = final_state["messages"]
    assert len(msgs) > 3
