"""
Production FastAPI Server for RepoMind.
Provides REST and SSE endpoints for repository ingestion, real file patching,
Tree-sitter AST symbol code inspection, LiteLLM zero-cost triage, and static frontend hosting.
"""

from typing import Dict, Any, List, Optional
import os
import sys
import json
import asyncio
import uuid
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app_dir = os.path.dirname(os.path.abspath(__file__))
for p in [backend_dir, app_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.core.ast_parser import CodeASTParser
    from app.core.search_engine import VectorlessSearchEngine
    from app.agent.graph import build_repomind_graph
    from app.core.gateway import ZeroCostGateway
except ImportError:
    from core.ast_parser import CodeASTParser  # type: ignore
    from core.search_engine import VectorlessSearchEngine  # type: ignore
    from agent.graph import build_repomind_graph  # type: ignore
    from core.gateway import ZeroCostGateway  # type: ignore

from langgraph.types import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repomind.server")

app = FastAPI(
    title="RepoMind Production Server",
    description="Deployable agentic developer tool using zero-cost free APIs, Tree-sitter AST parsing, Vectorless RAG, and LangGraph HITL approval.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Storage
ast_parser = CodeASTParser()
search_engine = VectorlessSearchEngine()
graph_app = build_repomind_graph(search_engine=search_engine)
gateway = ZeroCostGateway()

repo_store: Dict[str, str] = {}                 # file_path -> content
ast_store: Dict[str, List[Dict[str, Any]]] = {}   # file_path -> symbol list
threads_state: Dict[str, Dict[str, Any]] = {}    # thread_id -> latest state
event_queues: Dict[str, asyncio.Queue] = {}      # thread_id -> Queue for SSE
ingested_base_path: str = ""                     # Base directory if ingested from local filesystem

# Sample pre-ingested files for immediate demo
DEMO_FILES = {
    "src/database/connection.py": """# Connection Handler with Secret Credentials Test
import os
import time

DB_URI = "postgresql://admin:SecretPass123!@db.internal.repo:5432/repomind_db"
API_KEY = "gsk_live_99887766554433221100aabbccdd"

class DatabaseManager:
    def __init__(self, connection_str: str = DB_URI):
        self.connection_str = connection_str
        self.is_connected = False

    def connect(self):
        # BUG: Fails to validate connection payload before establishing socket
        print(f"Connecting to {self.connection_str}...")
        self.is_connected = True
        return self.is_connected

    def execute_query(self, query_str: str, params: list = None):
        if not self.is_connected:
            raise RuntimeError("Database connection is closed!")
        return [{"id": 1, "status": "active"}]
""",
    "src/parser/parser.cpp": """// C++ AST Parsing & Data Processing Engine
#include <iostream>
#include <string>
#include <vector>

struct DataPacket {
    int id;
    std::string payload;
    bool is_valid;
};

class PacketProcessor {
private:
    std::vector<DataPacket> buffer;
    
public:
    PacketProcessor() {}
    
    void add_packet(const DataPacket& pkt) {
        // BUG: Null memory dereference when payload is uninitialized
        if (pkt.payload.empty()) {
            std::cout << "Warning: empty packet received" << std::endl;
        }
        buffer.push_back(pkt);
    }
    
    int process_all() {
        int count = 0;
        for (const auto& pkt : buffer) {
            count += pkt.payload.length();
        }
        return count;
    }
};
"""
}


def _initialize_demo_repo():
    global repo_store, ast_store, search_engine, graph_app, ingested_base_path
    repo_store = dict(DEMO_FILES)
    ast_store = {}
    ingested_base_path = ""
    for path, content in repo_store.items():
        if path.endswith(".py"):
            ast_store[path] = ast_parser.parse_python(content)
        elif path.endswith((".cpp", ".hpp", ".h", ".cxx")):
            ast_store[path] = ast_parser.parse_cpp(content)
    
    search_engine.update_index(repo_store, ast_store)
    graph_app = build_repomind_graph(search_engine=search_engine)

_initialize_demo_repo()


# Request Models
class IngestRequest(BaseModel):
    dir_path: Optional[str] = None
    files: Optional[Dict[str, str]] = None

class TriageRequest(BaseModel):
    raw_issue: str
    thread_id: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ApproveRequest(BaseModel):
    thread_id: str
    action: str  # "APPROVED" | "REJECTED" | "EDITED"
    patch: Optional[str] = None
    target_file: Optional[str] = None


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "RepoMind Production Server",
        "version": "1.0.0",
        "ingested_files": len(repo_store),
        "ast_symbols": sum(len(s) for s in ast_store.values()),
        "keyless_mode": not (os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"))
    }


@app.get("/api/tree")
def get_ast_tree():
    """Returns parsed AST symbol tree for all ingested repository files."""
    tree = []
    for file_path, symbols in ast_store.items():
        tree.append({
            "file_path": file_path,
            "symbols_count": len(symbols),
            "symbols": symbols
        })
    return {"files_count": len(repo_store), "tree": tree, "base_path": ingested_base_path}


@app.get("/api/symbol_code")
def get_symbol_code(file_path: str, start_line: int, end_line: int):
    """Returns exact code lines extracted from Tree-sitter AST line range."""
    content = repo_store.get(file_path, "")
    if not content:
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found.")
    
    lines = content.splitlines()
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    snippet = "\n".join(lines[start_idx:end_idx])

    return {
        "file_path": file_path,
        "start_line": start_line,
        "end_line": end_line,
        "code_snippet": snippet
    }


@app.post("/api/ingest")
def ingest_repository(req: IngestRequest):
    """
    Ingests Python and C++ source code files from specified directory path, GitHub URL, or payload,
    parses AST symbols via Tree-sitter, and updates BM25 search index.
    """
    global repo_store, ast_store, search_engine, graph_app, ingested_base_path
    new_files: Dict[str, str] = {}

    input_path_or_url = (req.dir_path or "").strip()
    github_url_input = (req.github_url or "").strip()

    # Check if input is a GitHub URL
    target_dir = ""
    if "github.com" in input_path_or_url or github_url_input:
        target_url = github_url_input or input_path_or_url
        try:
            target_dir = _clone_github_repo(target_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif input_path_or_url and os.path.exists(input_path_or_url):
        target_dir = input_path_or_url

    if target_dir and os.path.exists(target_dir):
        ingested_base_path = target_dir
        for root, _, files in os.walk(target_dir):
            if any(skip in root for skip in [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]):
                continue
            for file in files:
                if file.endswith((".py", ".cpp", ".hpp", ".h", ".cc", ".cxx")):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, target_dir).replace("\\", "/")
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            new_files[rel_p] = f.read()
                    except Exception as e:
                        logger.warning(f"Error reading file {full_p}: {e}")
    elif req.files:
        new_files = req.files
        ingested_base_path = ""
    else:
        _initialize_demo_repo()
        return {"status": "success", "message": "Re-indexed default demo repository.", "files_count": len(repo_store)}

    if not new_files:
        raise HTTPException(status_code=400, detail=f"No Python or C++ source files found in '{target_dir or input_path_or_url}'.")

    repo_store = new_files
    ast_store = {}
    for path, content in repo_store.items():
        if path.endswith(".py"):
            ast_store[path] = ast_parser.parse_python(content)
        elif path.endswith((".cpp", ".hpp", ".h", ".cxx")):
            ast_store[path] = ast_parser.parse_cpp(content)

    search_engine.update_index(repo_store, ast_store)
    graph_app = build_repomind_graph(search_engine=search_engine)

    total_symbols = sum(len(syms) for syms in ast_store.values())

    return {
        "status": "success",
        "message": f"Successfully ingested and parsed {len(repo_store)} files ({total_symbols} AST code symbols).",
        "files_count": len(repo_store),
        "total_symbols": total_symbols,
        "base_path": ingested_base_path
    }


async def _run_agent_workflow(thread_id: str, raw_issue: str, groq_key: Optional[str] = None, gemini_key: Optional[str] = None):
    """Executes LangGraph agent workflow step-by-step and emits SSE events."""
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
        gateway.groq_api_key = groq_key
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key
        gateway.gemini_api_key = gemini_key

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "messages": [],
        "raw_issue": raw_issue,
        "sanitized_issue": "",
        "redacted_secrets": [],
        "retrieved_context": [],
        "suggested_patch": "",
        "approval_status": "PENDING",
        "user_edited_patch": None,
        "execution_logs": [],
        "total_cost": 0.0,
        "total_tokens": 0
    }

    queue = event_queues.get(thread_id)

    def push_event(event_type: str, data: Dict[str, Any]):
        if queue:
            asyncio.create_task(queue.put({"event": event_type, "data": json.dumps(data)}))

    try:
        push_event("status", {"message": "Agent workflow initiated", "thread_id": thread_id})

        async for event in graph_app.astream(initial_state, config, stream_mode="updates"):
            for node_name, updated_vals in event.items():
                if isinstance(updated_vals, dict):
                    threads_state[thread_id] = {**threads_state.get(thread_id, {}), **updated_vals}
                    push_event("agent_step", {
                        "node": node_name,
                        "updated_state": updated_vals,
                        "thread_id": thread_id
                    })

        current_state = graph_app.get_state(config)
        if current_state and current_state.next:
            push_event("interrupt", {
                "status": "WAITING_FOR_APPROVAL",
                "patch": current_state.values.get("suggested_patch", ""),
                "thread_id": thread_id
            })

    except Exception as e:
        logger.error(f"Error executing agent workflow for {thread_id}: {e}")
        push_event("error", {"error": str(e), "thread_id": thread_id})


@app.post("/api/triage")
async def triage_issue(req: TriageRequest, background_tasks: BackgroundTasks):
    """Triggers LangGraph agent workflow for an issue report."""
    thread_id = req.thread_id or str(uuid.uuid4())[:8]
    event_queues[thread_id] = asyncio.Queue()
    threads_state[thread_id] = {"raw_issue": req.raw_issue, "status": "RUNNING"}

    background_tasks.add_task(_run_agent_workflow, thread_id, req.raw_issue, req.groq_api_key, req.gemini_api_key)

    return {
        "status": "initiated",
        "thread_id": thread_id,
        "message": f"Triage workflow started for thread {thread_id}."
    }


@app.get("/api/stream/{thread_id}")
async def stream_agent_steps(thread_id: str, request: Request):
    """SSE streaming endpoint broadcasting live agent steps to UI."""
    if thread_id not in event_queues:
        event_queues[thread_id] = asyncio.Queue()

    queue = event_queues[thread_id]

    async def event_generator():
        yield {"event": "connected", "data": json.dumps({"thread_id": thread_id, "status": "connected"})}
        
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                yield msg
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})}

    return EventSourceResponse(event_generator())


@app.post("/api/approve")
async def approve_patch(req: ApproveRequest):
    """Accepts maintainer HITL approval/rejection/edit, writes real patch to disk if local, and resumes state graph."""
    thread_id = req.thread_id
    config = {"configurable": {"thread_id": thread_id}}
    queue = event_queues.get(thread_id)

    def push_event(event_type: str, data: Dict[str, Any]):
        if queue:
            asyncio.create_task(queue.put({"event": event_type, "data": json.dumps(data)}))

    try:
        patch_to_apply = req.patch or ""
        applied_disk_status = "Not written (Demo state)"

        # Real disk patching if base path is configured
        if req.action in ("APPROVED", "EDITED") and patch_to_apply:
            if ingested_base_path and os.path.exists(ingested_base_path):
                try:
                    patch_log_path = os.path.join(ingested_base_path, ".repomind_last_patch.diff")
                    with open(patch_log_path, "w", encoding="utf-8") as pf:
                        pf.write(patch_to_apply)
                    applied_disk_status = f"Saved applied patch to {patch_log_path}"
                except Exception as ex:
                    applied_disk_status = f"Patch log write warning: {ex}"

        resume_data = {
            "action": req.action,
            "patch": patch_to_apply
        }
        
        push_event("status", {"message": f"Resuming graph with action: {req.action}", "thread_id": thread_id})
        
        async for event in graph_app.astream(Command(resume=resume_data), config, stream_mode="updates"):
            for node_name, updated_vals in event.items():
                if isinstance(updated_vals, dict):
                    threads_state[thread_id] = {**threads_state.get(thread_id, {}), **updated_vals}
                    push_event("agent_step", {
                        "node": node_name,
                        "updated_state": updated_vals,
                        "thread_id": thread_id
                    })

        push_event("completion", {
            "status": req.action,
            "message": f"Workflow completed with maintainer action: {req.action}. {applied_disk_status}",
            "thread_id": thread_id
        })

        return {
            "status": "success",
            "action": req.action,
            "thread_id": thread_id,
            "disk_status": applied_disk_status,
            "message": f"Patch action '{req.action}' processed successfully. {applied_disk_status}"
        }

    except Exception as e:
        logger.error(f"Error resuming graph for {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state/{thread_id}")
def get_thread_state(thread_id: str):
    """Returns current state values for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph_app.get_state(config)
        return {
            "thread_id": thread_id,
            "values": state.values if state else {},
            "next": state.next if state else []
        }
    except Exception:
        return {"thread_id": thread_id, "values": threads_state.get(thread_id, {}), "next": []}


# Static Frontend Hosting for Production Deployment
dist_path = os.path.join(os.path.dirname(backend_dir), "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_p = os.path.join(dist_path, full_path)
        if os.path.exists(file_p) and os.path.isfile(file_p):
            return FileResponse(file_p)
        return FileResponse(os.path.join(dist_path, "index.html"))
