import os
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.gateway import MOCK_RESPONSES
from langchain_core.messages import AIMessage
from app.core.config import settings

@pytest.fixture(autouse=True)
def setup_mock(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    MOCK_RESPONSES.clear()

def test_api_e2e_triage_flow():
    async def run_test():
        # Setup mock responses for triage
        MOCK_RESPONSES.append(AIMessage(content='{"files": ["main.py"], "symbols": []}'))
        MOCK_RESPONSES.append(AIMessage(content='{"plan": "fix", "evidence": [{"file": "main.py", "start_line": 1, "end_line": 2, "why": "test"}]}'))
        MOCK_RESPONSES.append(AIMessage(content='```diff\n--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-a\n+b\n```'))
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. POST /api/ingest with the fixture repo
            fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
            res = await client.post("/api/ingest", json={"source": fixture_path})
            assert res.status_code == 200
            repo_id = res.json()["repo_id"]
            
            # 2. POST /api/triage
            res = await client.post("/api/triage", json={
                "repo_id": repo_id,
                "issue_text": "Fix tests"
            })
            assert res.status_code == 200
            thread_id = res.json()["thread_id"]
            
            # 3. Poll GET /api/state/{thread_id}
            state = None
            for _ in range(5):
                res = await client.get(f"/api/state/{thread_id}")
                assert res.status_code == 200
                state = res.json()
                if state.get("approval_status") == "PENDING" and state.get("evidence"):
                    break
            
            assert state["approval_status"] == "PENDING"
            assert len(state["evidence"]) > 0
            
            # Assert GET /api/stream/{thread_id} returns content-type text/event-stream
            async with client.stream("GET", f"/api/stream/{thread_id}", headers={"x-test-stream": "true"}) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
            
            # 4. POST /api/approve with APPROVED
            res = await client.post("/api/approve", json={
                "thread_id": thread_id,
                "action": "APPROVED"
            })
            assert res.status_code == 200
            
            # Wait for approval task
            for _ in range(5):
                res = await client.get(f"/api/state/{thread_id}")
                state = res.json()
                if state.get("approval_status") == "APPROVED":
                    break
                    
            assert state["approval_status"] == "APPROVED"
            
            # Wait for the api_stream generator to observe the APPROVED state and exit
            await asyncio.sleep(1.5)
            
            # 5. POST /api/followup on the same thread_id
            MOCK_RESPONSES.append(AIMessage(content='{"plan": "fix2", "evidence": [{"file": "main.py", "start_line": 1, "end_line": 2, "why": "test"}]}'))
            MOCK_RESPONSES.append(AIMessage(content='```diff\n--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-a\n+c\n```'))
            
            res = await client.post("/api/followup", json={
                "thread_id": thread_id,
                "message": "Also fix this"
            })
            assert res.status_code == 200
            
            # Poll for completion of followup
            for _ in range(5):
                res = await client.get(f"/api/state/{thread_id}")
                state = res.json()
                if state.get("patch_diff") and "--- a/main.py" in state["patch_diff"] and "+c" in state["patch_diff"]:
                    break
            
            # Assert a second patch exists with history intact
            assert state["patch_diff"] is not None
            assert "+c" in state["patch_diff"]
            assert len(state["execution_logs"]) > 0

    asyncio.run(run_test())
