import litellm
from .config import settings

# Currently available free-tier models (Verified for Groq & Gemini as of 2024-2025)
CHEAP_MODEL_GROQ = "groq/llama-3.1-8b-instant"
REASONER_MODEL_GROQ = "groq/llama-3.1-70b-versatile"
CHEAP_MODEL_GEMINI = "gemini/gemini-1.5-flash"
REASONER_MODEL_GEMINI = "gemini/gemini-1.5-pro"

def is_mock_mode():
    return not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY

def call_llm(messages: list, use_reasoner: bool = False) -> tuple[str, int]:
    """
    Returns (response_text, tokens_used)
    """
    if is_mock_mode():
        return "MOCK_RESPONSE", 42
        
    # Primary: Groq, Fallback: Gemini
    if settings.GROQ_API_KEY:
        model = REASONER_MODEL_GROQ if use_reasoner else CHEAP_MODEL_GROQ
        api_key = settings.GROQ_API_KEY
    else:
        model = REASONER_MODEL_GEMINI if use_reasoner else CHEAP_MODEL_GEMINI
        api_key = settings.GEMINI_API_KEY

    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            api_key=api_key,
        )
        tokens = response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.content, tokens
    except Exception as e:
        return f"Error: {str(e)}", 0
