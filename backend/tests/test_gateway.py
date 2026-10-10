import pytest
from app.core.gateway import call_llm, is_mock_mode
from app.core.config import settings

def test_gateway_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    
    assert is_mock_mode() is True
    
    response, tokens = call_llm([{"role": "user", "content": "Hello"}])
    assert response.content == "MOCK_RESPONSE"
    assert tokens == 42

def test_gateway_model_ids_not_retired():
    from app.core.gateway import CHEAP_MODEL_GEMINI, REASONER_MODEL_GEMINI, CHEAP_MODEL_GROQ, REASONER_MODEL_GROQ
    assert "1.5" not in CHEAP_MODEL_GEMINI
    assert "1.5" not in REASONER_MODEL_GEMINI
    assert "llama-" not in CHEAP_MODEL_GROQ
    assert "llama-" not in REASONER_MODEL_GROQ

def test_reasoner_model_has_free_tier():
    from app.core.gateway import REASONER_MODEL_GEMINI
    assert "flash" in REASONER_MODEL_GEMINI

def test_call_llm_raises_gateway_error(monkeypatch):
    import litellm
    from app.core.gateway import GatewayError, call_llm
    from app.core.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)

    def mock_completion(*args, **kwargs):
        raise Exception("API failure")
    
    monkeypatch.setattr(litellm, "completion", mock_completion)

    with pytest.raises(GatewayError, match="API failure"):
        call_llm([{"role": "user", "content": "hi"}])
