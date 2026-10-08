"""
Secret & PII Sanitizer Middleware for RepoMind.
Sanitizes raw issue descriptions, stack traces, and code payloads before sending them to LLM APIs.
"""

from typing import Tuple, List
import re


class SecretGuardrail:
    """
    Regex-based Secret and PII Sanitizer.
    Identifies credentials, API keys, tokens, and database connection URIs, replacing them with [REDACTED_SECRET].
    """

    PATTERNS = [
        # Groq API Keys (e.g. gsk_...)
        (r'gsk_[A-Za-z0-9_{}-]{16,}', 'Groq API Key'),
        # Google Gemini / GCP API Keys (e.g. AIzaSy...)
        (r'AIzaSy[A-Za-z0-9_-]{33}', 'Gemini API Key'),
        # OpenAI / Standard API Keys (e.g. sk-...)
        (r'sk-[A-Za-z0-9_{}-]{20,}', 'OpenAI API Key'),
        # Generic Secret Keys / Tokens (e.g. secret_..., bearer tokens, etc.)
        (r'bearer\s+[A-Za-z0-9_\-\.=]{20,}', 'Bearer Token'),
        # JSON Web Tokens (JWT)
        (r'eyJ[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT Token'),
        # Database Connection URIs (postgres, mysql, mongodb, redis)
        (r'(?:postgres|postgresql|mysql|mongodb|redis):\/\/[A-Za-z0-9_\-\.]+:[^@\s]+@[A-Za-z0-9_\-\.:]+\/[A-Za-z0-9_\-\.]+', 'Database Connection URI'),
        # Environment Variable assignments (.env format: PASSWORD=..., SECRET=...)
        (r'(?i)(?:SECRET|PASSWORD|PASS|API_KEY|TOKEN|PRIVATE_KEY)\s*=\s*["\']?[^\s"\'#]+["\']?', 'Environment Credential'),
        # AWS Access / Secret Keys
        (r'(?:AKIA|ASIA)[0-9A-Z]{16}', 'AWS Access Key'),
        (r'(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9\/+=]{40}', 'AWS Secret Key'),
    ]

    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE if '(?i)' in pattern else 0), label)
            for pattern, label in self.PATTERNS
        ]

    def sanitize_payload(self, text: str) -> Tuple[str, List[str]]:
        """
        Scans and redacts sensitive credentials from the payload text.

        Returns:
            Tuple[str, List[str]]: (Sanitized text with [REDACTED_SECRET], List of detected secret descriptions)
        """
        if not text:
            return "", []

        sanitized_text = text
        detected_secrets = []

        for pattern, label in self.compiled_patterns:
            matches = pattern.findall(sanitized_text)
            if matches:
                count = len(matches)
                detected_secrets.append(f"{label} ({count} found)")
                sanitized_text = pattern.sub("[REDACTED_SECRET]", sanitized_text)

        return sanitized_text, detected_secrets
