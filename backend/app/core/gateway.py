import litellm
import json
from .config import settings
from langchain_core.messages import AIMessage, ToolCall

# Currently available free-tier models
CHEAP_MODEL_GROQ = "groq/llama-3.1-8b-instant"
REASONER_MODEL_GROQ = "groq/llama-3.1-70b-versatile"
CHEAP_MODEL_GEMINI = "gemini/gemini-1.5-flash"
REASONER_MODEL_GEMINI = "gemini/gemini-1.5-pro"

# Global mock for tests
MOCK_RESPONSES = []

def is_mock_mode():
    return not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY

def format_tools_for_litellm(langchain_tools):
    formatted = []
    for t in langchain_tools:
        formatted.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.args_schema.schema() if t.args_schema else {"type": "object", "properties": {}}
            }
        })
    return formatted

def call_llm(messages: list, use_reasoner: bool = False, tools: list = None) -> tuple[AIMessage, int]:
    """
    Returns (AIMessage, tokens_used)
    """
    if is_mock_mode():
        if MOCK_RESPONSES:
            resp = MOCK_RESPONSES.pop(0)
            if not tools:
                # model cannot emit tool calls if tools were not provided
                resp = AIMessage(content=resp.content or "MOCK_RESPONSE")
            return resp, 42
        return AIMessage(content="MOCK_RESPONSE"), 42
        
    if settings.GROQ_API_KEY:
        model = REASONER_MODEL_GROQ if use_reasoner else CHEAP_MODEL_GROQ
        api_key = settings.GROQ_API_KEY
    else:
        model = REASONER_MODEL_GEMINI if use_reasoner else CHEAP_MODEL_GEMINI
        api_key = settings.GEMINI_API_KEY

    kwargs = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
    }
    if tools:
        kwargs["tools"] = format_tools_for_litellm(tools)

    try:
        response = litellm.completion(**kwargs)
        tokens = response.usage.total_tokens if response.usage else 0
        
        msg = response.choices[0].message
        content = msg.content or ""
        
        tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    name=tc.function.name,
                    args=json.loads(tc.function.arguments),
                    id=tc.id
                ))
        
        return AIMessage(content=content, tool_calls=tool_calls), tokens
    except Exception as e:
        return AIMessage(content=f"Error: {str(e)}"), 0
