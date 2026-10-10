from typing import List, Dict, Any, Literal
import json
import re
import traceback
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from app.core.guardrails import redact_secrets_and_pii
from app.core.gateway import call_llm
from .state import AgentState, Evidence
from .tools import TOOLS

import tempfile
import shutil
import os
from app.verify.security_scan import scan_diff
from app.verify.patcher import apply_patch
from app.verify.test_selector import select_tests
from app.verify.test_runner import run_tests

def format_messages_for_litellm(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    formatted = []
    for m in messages:
        if isinstance(m, SystemMessage):
            formatted.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            formatted.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            msg = {"role": "assistant", "content": m.content or ""}
            if hasattr(m, "tool_calls") and m.tool_calls:
                msg["tool_calls"] = []
                for tc in m.tool_calls:
                    msg["tool_calls"].append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["args"])
                        }
                    })
            formatted.append(msg)
        elif isinstance(m, ToolMessage):
            formatted.append({
                "role": "tool",
                "tool_call_id": m.tool_call_id,
                "name": m.name,
                "content": m.content
            })
    return formatted

def issue_parser(state: AgentState, config: RunnableConfig):
    sanitized, count = redact_secrets_and_pii(state.get("raw_issue", ""))
    
    prompt = f"""You are an issue parser. Given this issue, extract any explicit file paths or symbol names mentioned. 
Return ONLY a JSON object with 'files' (list of strings) and 'symbols' (list of strings).
Issue: {sanitized}"""

    messages = [HumanMessage(content=prompt)]
    ai_msg, tokens = call_llm(format_messages_for_litellm(messages), use_reasoner=False)
    
    logs = [f"issue_parser extracted info from issue. Tokens: {tokens}"]
    
    try:
        match = re.search(r'\{.*\}', ai_msg.content, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            parsed = {"files": [], "symbols": []}
    except Exception:
        parsed = {"files": [], "symbols": []}
        
    init_msg = HumanMessage(content=f"Issue to fix:\n{sanitized}\n\nExtracted hints: files={parsed.get('files')}, symbols={parsed.get('symbols')}")
    
    return {
        "sanitized_issue": sanitized,
        "redacted_count": count,
        "execution_logs": logs,
        "total_tokens": tokens,
        "messages": [init_msg],
        "tool_iterations": 0
    }

def execute_tools(state: AgentState, config: RunnableConfig):
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}
        
    tool_messages = []
    logs = []
    
    # Expose repo_id in config
    repo_id = state.get("repo_id")
    if repo_id:
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["repo_id"] = repo_id
        
    for tc in last_message.tool_calls:
        tool_name = tc["name"]
        args = tc["args"]
        tool_id = tc["id"]
        
        tool_func = next((t for t in TOOLS if t.name == tool_name), None)
        if not tool_func:
            tool_messages.append(ToolMessage(content=f"Error: Tool {tool_name} not found.", name=tool_name, tool_call_id=tool_id))
            logs.append(f"Tool {tool_name} not found")
            continue
            
        try:
            # We catch exceptions to prevent run failure
            result = tool_func.invoke(args, config=config)
            content = str(result)
            tool_messages.append(ToolMessage(content=content, name=tool_name, tool_call_id=tool_id))
            logs.append(f"Tool {tool_name} executed successfully")
        except Exception as e:
            err = traceback.format_exc()
            tool_messages.append(ToolMessage(content=f"Error: {str(e)}\n{err}", name=tool_name, tool_call_id=tool_id))
            logs.append(f"Tool {tool_name} failed: {str(e)}")
            
    return {
        "messages": tool_messages,
        "execution_logs": logs
    }

def researcher(state: AgentState, config: RunnableConfig):
    system_prompt = """You are an expert researcher. Use tools to investigate the codebase.
When you are done researching, you MUST output a final JSON object (and no other text) with:
- "plan": detailed string plan of what to change
- "evidence": list of dicts with {"file": str, "start_line": int, "end_line": int, "why": str}
If you need more info, call tools."""

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # Cap at 8 tool iterations
    iterations = state.get("tool_iterations", 0)
    use_tools = TOOLS if iterations < 8 else None
    
    ai_msg, tokens = call_llm(format_messages_for_litellm(messages), use_reasoner=True, tools=use_tools)
    
    updates = {
        "messages": [ai_msg],
        "total_tokens": tokens,
        "execution_logs": [f"researcher iteration {iterations+1}, tokens={tokens}"]
    }
    
    if ai_msg.tool_calls:
        updates["tool_iterations"] = iterations + 1
    else:
        # Try parse plan and evidence
        try:
            match = re.search(r'\{.*\}', ai_msg.content, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                updates["plan"] = parsed.get("plan", "")
                updates["evidence"] = parsed.get("evidence", [])
            else:
                updates["plan"] = ai_msg.content
                updates["evidence"] = []
        except Exception:
            updates["plan"] = ai_msg.content
            updates["evidence"] = []
            
    return updates

def patch_generator(state: AgentState, config: RunnableConfig):
    # Only called when researcher is done. We can reject it if evidence is missing.
    evidence = state.get("evidence", [])
    if not evidence:
        rejections = state.get("rejection_count", 0)
        if rejections >= 3:
            raise RuntimeError("Run failed: rejected due to no evidence 3 times.")
        return {
            "messages": [HumanMessage(content="Your previous step provided no evidence. Please research again and provide evidence.")],
            "rejection_count": rejections + 1,
            "execution_logs": ["patch_generator rejected due to no evidence"]
        }
        
    system_prompt = f"""You are an expert patch generator. Based on the plan and evidence, output ONLY a valid Unified Diff patch.
Plan: {state.get('plan')}
Evidence: {json.dumps(evidence)}
"""
    # We pass the history as well
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    ai_msg, tokens = call_llm(format_messages_for_litellm(messages), use_reasoner=True)
    
    # Parse diff
    diff_content = ai_msg.content
    # Try extract from markdown
    if "```diff" in diff_content:
        match = re.search(r'```diff\n(.*?)\n```', diff_content, re.DOTALL)
        if match:
            diff_content = match.group(1)
            
    return {
        "patch_diff": diff_content,
        "verification_result": "Ready for review",
        "approval_status": "PENDING",
        "messages": [ai_msg],
        "total_tokens": tokens,
        "execution_logs": [f"patch_generator finished, tokens={tokens}"]
    }

def verifier(state: AgentState, config: RunnableConfig):
    patch_diff = state.get("patch_diff", "")
    
    sec_res = scan_diff(patch_diff)
    if not sec_res["clean"]:
        return {
            "verification_result": "Security scan failed: " + ", ".join(sec_res["findings"]),
            "execution_logs": ["Verifier: Security scan failed"]
        }
        
    repo_id = state.get("repo_id")
    from app.core.ingest import get_repos
    repos = get_repos()
    if repo_id not in repos:
        return {
            "verification_result": f"Repo {repo_id} not found for verification",
            "execution_logs": ["Verifier: Repo not found"]
        }
        
    original_repo_path = repos[repo_id]["path"]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_repo = os.path.join(temp_dir, "repo")
        shutil.copytree(original_repo_path, temp_repo)
        
        patch_res = apply_patch(temp_repo, patch_diff)
        if not patch_res["ok"]:
            return _handle_verification_failure(state, "Patch failed to apply: " + patch_res.get("error", ""))
            
        test_files = select_tests(temp_repo, patch_diff)
        test_res = run_tests(temp_repo, test_files)
        
        if test_res["passed"]:
            return {
                "verification_result": "Passed",
                "execution_logs": ["Verifier: Tests passed"]
            }
        else:
            return _handle_verification_failure(state, "Tests failed:\n" + test_res.get("failures_summary", ""))

def _handle_verification_failure(state: AgentState, error_msg: str):
    retries = state.get("verifier_retries", 0)
    if retries >= 1:
        return {
            "verification_result": "Failed after retries: " + error_msg,
            "execution_logs": ["Verifier: Tests failed, exhausted retries"]
        }
        
    new_msg = HumanMessage(content=f"Your patch failed verification. Please fix it.\nError:\n{error_msg}")
    return {
        "verifier_retries": retries + 1,
        "messages": [new_msg],
        "execution_logs": ["Verifier: Patch failed, sending back to patch_generator"]
    }

def should_continue_researcher(state: AgentState) -> Literal["execute_tools", "patch_generator"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"
    return "patch_generator"

def should_continue_patch(state: AgentState) -> Literal["researcher", "verifier"]:
    last_log = state.get("execution_logs", [])[-1] if state.get("execution_logs") else ""
    if "rejected due to no evidence" in last_log:
        return "researcher"
    return "verifier"

def should_continue_verifier(state: AgentState) -> Literal["patch_generator", "hitl_interrupt"]:
    last_log = state.get("execution_logs", [])[-1] if state.get("execution_logs") else ""
    if "sending back to patch_generator" in last_log:
        return "patch_generator"
    return "hitl_interrupt"

def hitl_interrupt(state: AgentState):
    # This node just acts as an interrupt point for LangGraph.
    # It receives updates from human if resumed.
    # Wait, the human can resume with an update to `approval_status` and `patch_diff`.
    return {}
