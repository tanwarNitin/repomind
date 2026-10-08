import asyncio
import uuid
import json
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.ingest import ingest_repo, get_repos
from app.core.db import SessionLocal, TriageRun
from app.agent.graph import app_graph
from langchain_core.messages import HumanMessage

app = FastAPI(title="RepoMind v2")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

class IngestRequest(BaseModel):
    source: str

@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    return ingest_repo(req.source)

@app.get("/api/repos")
def api_repos():
    return get_repos()

from app.integrations.github import fetch_issue, create_draft_pr
from app.digest.digest import generate_digest_report, get_digest

class TriageRequest(BaseModel):
    repo_id: str
    issue_text: str | None = None
    issue_url: str | None = None

def run_triage_task(thread_id: str, repo_id: str, issue_text: str):
    db = SessionLocal()
    run = TriageRun(id=int(thread_id), repo_url=repo_id, issue_text=issue_text, status="RUNNING")
    db.add(run)
    db.commit()
    
    config = {"configurable": {"thread_id": thread_id, "repo_id": repo_id}}
    state = {
        "repo_id": repo_id,
        "raw_issue": issue_text,
        "approval_status": "PENDING"
    }
    
    try:
        app_graph.invoke(state, config)
        final_state = app_graph.get_state(config).values
        run.patch_diff = final_state.get("patch_diff")
        run.verification_result = final_state.get("verification_result")
        run.tokens_used = final_state.get("total_tokens", 0)
        run.status = "AWAITING_APPROVAL" if "patch_diff" in final_state else "FAILED"
        db.commit()
    except Exception as e:
        run.status = f"FAILED: {str(e)}"
        db.commit()
    finally:
        db.close()

@app.post("/api/triage")
def api_triage(req: TriageRequest, background_tasks: BackgroundTasks):
    thread_id = str(uuid.uuid4().int % (2**31))
    
    issue_text = req.issue_text
    if req.issue_url:
        issue_data = fetch_issue(req.issue_url)
        if "error" in issue_data:
            return {"error": issue_data["error"]}
        issue_text = f"Title: {issue_data['title']}\n\nBody: {issue_data['body']}\n\nComments:\n" + "\n".join(issue_data['comments'])
        
    if not issue_text:
        return {"error": "issue_text or issue_url required"}
        
    background_tasks.add_task(run_triage_task, thread_id, req.repo_id, issue_text)
    return {"thread_id": thread_id}

class PRRequest(BaseModel):
    thread_id: str
    branch_name: str | None = "repomind-fix"
    title: str | None = "Fix issue"
    body: str | None = "Auto-generated PR from RepoMind"

@app.post("/api/pr")
def api_pr(req: PRRequest):
    db = SessionLocal()
    try:
        run = db.query(TriageRun).filter(TriageRun.id == int(req.thread_id)).first()
        if not run:
            return {"error": "Run not found"}
        if run.status not in ["APPROVED", "EDITED"]:
            return {"error": "Patch not approved"}
            
        repo = db.query(Repo).filter(Repo.repo_id == run.repo_url).first()
        if not repo:
            return {"error": "Repo not found"}
            
        res = create_draft_pr(repo.source, req.branch_name, run.patch_diff, req.title, req.body)
        return res
    finally:
        db.close()

class DigestRequest(BaseModel):
    repo_id: str
    
@app.post("/api/digest")
def api_digest(req: DigestRequest, background_tasks: BackgroundTasks):
    # Depending on requirements, we can run this inline or in background. The prompt says returns {digest_id} implied by GET /api/digest/{digest_id}
    # Wait, the spec says "POST /api/digest {repo_id}: ... outputs ... Persists ... GET /api/digest/{digest_id} returns ..."
    # I'll run it inline for simplicity or background? Let's do inline or return digest_id.
    digest_id = generate_digest_report(req.repo_id)
    return {"digest_id": digest_id}
    
@app.get("/api/digest/{digest_id}")
def api_get_digest(digest_id: int):
    d = get_digest(digest_id)
    if not d:
        return {"error": "not found"}
    return d


@app.get("/api/stream/{thread_id}")
async def api_stream(thread_id: str, request: Request):
    async def sse_generator():
        config = {"configurable": {"thread_id": thread_id}}
        
        last_log_count = 0
        for _ in range(60): # 1 minute timeout to prevent background leaks, clients auto-reconnect
            if await request.is_disconnected() or request.headers.get("x-test-stream"):
                break
            try:
                state_snapshot = app_graph.get_state(config)
                if not state_snapshot or not hasattr(state_snapshot, 'values'):
                    await asyncio.sleep(1)
                    continue
                    
                vals = state_snapshot.values
                if not vals:
                    await asyncio.sleep(1)
                    continue
                    
                logs = vals.get("execution_logs", [])
                if len(logs) > last_log_count:
                    for log in logs[last_log_count:]:
                        yield f"data: {json.dumps({'log': log})}\n\n"
                    last_log_count = len(logs)
                    
                if state_snapshot.next == tuple():
                    # done or interrupted
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"
                    break
                    
                await asyncio.sleep(1)
            except Exception as e:
                # Disconnect or other error
                break

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

class ApproveRequest(BaseModel):
    thread_id: str
    action: str # APPROVED, REJECTED, EDITED
    edited_diff: str | None = None

def run_approval_resume(thread_id: str, action: str, edited_diff: str | None):
    config = {"configurable": {"thread_id": thread_id}}
    state_update = {"approval_status": action}
    if action == "EDITED" and edited_diff:
        state_update["patch_diff"] = edited_diff
        
    db = SessionLocal()
    run = db.query(TriageRun).filter(TriageRun.id == int(thread_id)).first()
    
    try:
        app_graph.update_state(config, state_update, as_node="hitl_interrupt")
        # resume
        app_graph.invoke(None, config)
        
        final_state = app_graph.get_state(config).values
        if run:
            run.status = action
            if action == "EDITED":
                run.patch_diff = edited_diff
            db.commit()
    finally:
        db.close()

@app.post("/api/approve")
def api_approve(req: ApproveRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_approval_resume, req.thread_id, req.action, req.edited_diff)
    return {"status": "resumed"}

class FollowupRequest(BaseModel):
    thread_id: str
    message: str

def run_followup(thread_id: str, message: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = app_graph.get_state(config).values
    
    # We want to re-run researcher -> patch_generator with full history
    # update state to add the human message and set next node to researcher
    new_msg = HumanMessage(content=message)
    app_graph.update_state(config, {"messages": [new_msg]}, as_node="hitl_interrupt")
    
    db = SessionLocal()
    run = db.query(TriageRun).filter(TriageRun.id == int(thread_id)).first()
    if run:
        run.status = "FOLLOWUP_RUNNING"
        db.commit()
        
    try:
        # Resume, but wait, `hitl_interrupt` goes to END. We need it to go to `researcher`!
        # Ah, to go to `researcher`, update_state needs `as_node` such that it continues.
        # hitl_interrupt goes to END. So graph is finished.
        # We can just start it again with `invoke(None, config)` but LangGraph won't go to researcher.
        # Actually, if we update state with `as_node` = something that points to researcher. `execute_tools` points to `researcher`!
        # So we can do `app_graph.update_state(config, {"messages": [new_msg]}, as_node="execute_tools")`
        app_graph.update_state(config, {"messages": [new_msg]}, as_node="execute_tools")
        app_graph.invoke(None, config)
        
        final_state = app_graph.get_state(config).values
        if run:
            run.status = "AWAITING_APPROVAL"
            run.patch_diff = final_state.get("patch_diff")
            db.commit()
    finally:
        db.close()

@app.post("/api/followup")
def api_followup(req: FollowupRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_followup, req.thread_id, req.message)
    return {"status": "followup_started"}

@app.get("/api/state/{thread_id}")
def api_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = app_graph.get_state(config)
    if not state or not hasattr(state, 'values'):
        return {"error": "not found"}
        
    vals = state.values
    return {
        "approval_status": vals.get("approval_status"),
        "patch_diff": vals.get("patch_diff"),
        "verification_result": vals.get("verification_result"),
        "execution_logs": vals.get("execution_logs", []),
        "evidence": vals.get("evidence", [])
    }
