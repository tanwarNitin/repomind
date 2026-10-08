import pytest
from app.core.gateway import call_llm, is_mock_mode
from app.core.config import settings

def test_gateway_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    
    assert is_mock_mode() is True
    
    response, tokens = call_llm([{"role": "user", "content": "Hello"}])
    assert response == "MOCK_RESPONSE"
    assert tokens == 42
