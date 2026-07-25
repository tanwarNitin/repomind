"""
LiteLLM Router Gateway for RepoMind.
Routes LLM calls strictly through zero-cost / free-tier API providers (Groq and Gemini)
with transparent fallback failover and usage/cost tracking. Includes mock fallback for keyless environments.
"""

from typing import List, Dict, Any, Optional
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("repomind.gateway")

try:
    import litellm
    # Suppress verbose LiteLLM logs
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class ZeroCostGateway:
    """
    LiteLLM zero-cost API router supporting Groq & Gemini free tiers.
    """

    ROUTER_CONFIGS = {
        "cheap-router": {
            "primary": "groq/llama-3.1-8b-instant",
            "fallback": "gemini/gemini-1.5-flash",
            "max_tokens": 1024,
            "temperature": 0.2
        },
        "heavy-reasoner": {
            "primary": "groq/llama-3.3-70b-versatile",
            "fallback": "gemini/gemini-2.0-flash",
            "max_tokens": 2048,
            "temperature": 0.3
        }
    }

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def complete(
        self,
        router_alias: str,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes completion via primary model, falling back to secondary on rate limit / error.
        If no API keys are present, falls back gracefully to deterministic logic.
        """
        config = self.ROUTER_CONFIGS.get(router_alias, self.ROUTER_CONFIGS["cheap-router"])

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        # 1. Try Primary Model
        if LITELLM_AVAILABLE and (self.groq_api_key or self.gemini_api_key):
            for model in [config["primary"], config["fallback"]]:
                try:
                    # Set provider API key if available
                    if model.startswith("groq/") and not self.groq_api_key:
                        continue
                    if model.startswith("gemini/") and not self.gemini_api_key:
                        continue

                    response = litellm.completion(
                        model=model,
                        messages=formatted_messages,
                        max_tokens=config["max_tokens"],
                        temperature=config["temperature"],
                        api_key=self.groq_api_key if model.startswith("groq/") else self.gemini_api_key
                    )

                    content = response.choices[0].message.content
                    usage = response.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                    return {
                        "content": content,
                        "model": model,
                        "router": router_alias,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "cost_usd": 0.0,  # Free Tier API
                        "status": "SUCCESS"
                    }
                except Exception as e:
                    logger.warning(f"Gateway failover from {model} due to error: {e}")

        # 2. Keyless / Fallback Engine when API keys are not provided or API calls fail
        return self._generate_keyless_fallback(router_alias, messages)

    def _generate_keyless_fallback(
        self,
        router_alias: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Intelligent offline/keyless fallback logic so RepoMind operates seamlessly
        even without API keys configured.
        """
        last_message = messages[-1]["content"] if messages else ""

        if router_alias == "cheap-router":
            # Extract symbol target heuristic
            extracted_symbols = []
            words = [w.strip("(),.:;`'") for w in last_message.split() if len(w) > 2]
            for w in words:
                if w[0].isupper() or "_" in w or w.endswith("Handler") or w.endswith("Parser"):
                    extracted_symbols.append(w)
            
            target_symbols = list(set(extracted_symbols))[:3] or ["main", "process_data"]
            content = json.dumps({
                "summary": "Extracted issue targets and code symbol references.",
                "symbols": target_symbols
            })
        else:
            # Heavy reasoner patch generator fallback
            content = """```diff
--- a/src/core.py
+++ b/src/core.py
@@ -10,6 +10,8 @@ def process_data(payload):
     if payload is None:
-        raise ValueError("Payload cannot be null")
+        logger.warning("Null payload received, applying default fallback")
+        payload = {}
     return payload
```"""

        return {
            "content": content,
            "model": "repomind-free-fallback (offline mode)",
            "router": router_alias,
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "total_tokens": 200,
            "cost_usd": 0.0,
            "status": "FALLBACK_OFFLINE"
        }
