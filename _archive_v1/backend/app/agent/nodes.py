"""
LangGraph Workflow Nodes for RepoMind: IssueParser, TreeSearch, PatchGenerator.
"""

from typing import Dict, Any, List
import sys
import os
import json
import time

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in [backend_dir, app_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.core.guardrails import SecretGuardrail
    from app.core.gateway import ZeroCostGateway
    from app.agent.state import RepoMindState
except ImportError:
    from core.guardrails import SecretGuardrail  # type: ignore
    from core.gateway import ZeroCostGateway  # type: ignore
    from agent.state import RepoMindState  # type: ignore

guardrail = SecretGuardrail()
gateway = ZeroCostGateway()


def issue_parser_node(state: RepoMindState, search_engine=None) -> Dict[str, Any]:
    """
    Node 1: Sanitizes issue text via Guardrails and extracts target symbols using cheap-router.
    """
    start_time = time.time()
    raw_issue = state.get("raw_issue", "")

    # 1. Sanitize issue text with Guardrails
    sanitized_issue, redacted_secrets = guardrail.sanitize_payload(raw_issue)

    # 2. Extract symbols using cheap-router
    system_prompt = (
        "You are RepoMind Issue Parser. Analyze the issue description and stack traces. "
        "Extract potential target class names, function names, and module files involved. "
        "Return a concise JSON object with key 'symbols'."
    )

    res = gateway.complete(
        router_alias="cheap-router",
        messages=[{"role": "user", "content": sanitized_issue}],
        system_prompt=system_prompt
    )

    log_entry = {
        "step": "issue_parser",
        "timestamp": time.strftime("%H:%M:%S"),
        "model": res["model"],
        "router": res["router"],
        "redacted_secrets_count": len(redacted_secrets),
        "tokens": res["total_tokens"],
        "duration_sec": round(time.time() - start_time, 2),
        "message": f"Sanitized issue ({len(redacted_secrets)} secrets redacted). Parsed symbols using {res['model']}."
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)

    return {
        "sanitized_issue": sanitized_issue,
        "redacted_secrets": redacted_secrets,
        "execution_logs": logs,
        "total_tokens": state.get("total_tokens", 0) + res["total_tokens"],
        "total_cost": state.get("total_cost", 0.0) + res["cost_usd"]
    }


def tree_search_node(state: RepoMindState, search_engine=None) -> Dict[str, Any]:
    """
    Node 2: Queries VectorlessSearchEngine for exact AST code ranges and slices.
    """
    start_time = time.time()
    sanitized_issue = state.get("sanitized_issue", "")

    retrieved_context: List[Dict[str, Any]] = []
    if search_engine:
        retrieved_context = search_engine.search(query=sanitized_issue, top_k=3)

    log_entry = {
        "step": "tree_search",
        "timestamp": time.strftime("%H:%M:%S"),
        "model": "Vectorless-BM25-AST-Engine",
        "router": "bm25-ast-hybrid",
        "retrieved_slices": len(retrieved_context),
        "duration_sec": round(time.time() - start_time, 2),
        "message": f"Retrieved {len(retrieved_context)} exact AST code symbol slices matching issue tokens."
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)

    return {
        "retrieved_context": retrieved_context,
        "execution_logs": logs
    }


def patch_generator_node(state: RepoMindState, search_engine=None) -> Dict[str, Any]:
    """
    Node 3: Feeds AST snippets + issue into heavy-reasoner to generate unified git diff.
    """
    start_time = time.time()
    sanitized_issue = state.get("sanitized_issue", "")
    retrieved_context = state.get("retrieved_context", [])

    # Format context for prompt
    context_str = ""
    for idx, ctx in enumerate(retrieved_context, 1):
        context_str += f"\n--- Slice #{idx}: {ctx.get('file_path')} (Lines {ctx.get('start_line')}-{ctx.get('end_line')}) Symbol: {ctx.get('symbol_name')} ---\n"
        context_str += ctx.get("code_snippet", "") + "\n"

    system_prompt = (
        "You are RepoMind Senior Patch Engineer. Review the issue report and exact AST code slices. "
        "Generate a clean, unified git diff that fixes the bug. Output ONLY the unified diff block wrapped in ```diff ... ```."
    )

    user_prompt = f"Issue:\n{sanitized_issue}\n\nAST Code Slices:\n{context_str}"

    res = gateway.complete(
        router_alias="heavy-reasoner",
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt
    )

    patch_output = res["content"]
    # Clean diff wrapper if present
    if "```diff" in patch_output:
        patch_output = patch_output.split("```diff")[1].split("```")[0].strip()
    elif "```" in patch_output:
        patch_output = patch_output.split("```")[1].split("```")[0].strip()

    log_entry = {
        "step": "patch_generator",
        "timestamp": time.strftime("%H:%M:%S"),
        "model": res["model"],
        "router": res["router"],
        "tokens": res["total_tokens"],
        "duration_sec": round(time.time() - start_time, 2),
        "message": f"Generated unified git patch using {res['model']} ({res['total_tokens']} tokens). Awaiting Maintainer Approval (HITL)."
    }

    logs = list(state.get("execution_logs", []))
    logs.append(log_entry)

    return {
        "suggested_patch": patch_output,
        "approval_status": "PENDING",
        "execution_logs": logs,
        "total_tokens": state.get("total_tokens", 0) + res["total_tokens"],
        "total_cost": state.get("total_cost", 0.0) + res["cost_usd"]
    }
