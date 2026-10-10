import pytest
import os
from app.onboarding.explainer import generate_explanation
from app.core.ingest import ingest_repo
from app.core.gateway import MOCK_RESPONSES
from langchain_core.messages import AIMessage

@pytest.fixture(scope="module")
def fixture_repo_id():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixture_repo")
    res = ingest_repo(fixture_path)
    return res["repo_id"]

@pytest.fixture(autouse=True)
def setup_mock(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

def test_explain_has_all_sections(fixture_repo_id):
    MOCK_RESPONSES.clear()
    MOCK_RESPONSES.append(AIMessage(content="""
# Overview
- entry points
- module map (what each top-level module does)
- core logic locations (with file:line citations)
- suggested first-issue areas

(utils.py:1)
"""))
    explanation = generate_explanation(fixture_repo_id)
    assert "entry points" in explanation
    assert "module map (what each top-level module does)" in explanation
    assert "core logic locations (with file:line citations)" in explanation
    assert "suggested first-issue areas" in explanation

def test_explain_cites_evidence_for_claims(fixture_repo_id):
    MOCK_RESPONSES.clear()
    MOCK_RESPONSES.append(AIMessage(content="Here is a claim (utils.py:1)"))
    explanation = generate_explanation(fixture_repo_id)
    assert "(utils.py:1)" in explanation
