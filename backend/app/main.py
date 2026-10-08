from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
from app.core.config import settings

app = FastAPI(title="RepoMind v2")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

async def fake_sse_generator():
    yield "data: {\"status\": \"starting\"}\n\n"
    await asyncio.sleep(1)
    yield "data: {\"status\": \"done\"}\n\n"

@app.get("/api/stream")
async def stream():
    return StreamingResponse(fake_sse_generator(), media_type="text/event-stream")

from pydantic import BaseModel
from app.core.ingest import ingest_repo, get_repos

class IngestRequest(BaseModel):
    source: str

@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    return ingest_repo(req.source)

@app.get("/api/repos")
def api_repos():
    return get_repos()
