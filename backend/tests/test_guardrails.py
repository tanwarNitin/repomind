from app.core.guardrails import redact_secrets_and_pii

def test_guardrails_redaction():
    text = "Here is my email: user@example.com and my AWS key: AKIAIOSFODNN7EXAMPLE."
    sanitized_text, count = redact_secrets_and_pii(text)
    
    assert count == 2
    assert "user@example.com" not in sanitized_text
    assert "[REDACTED_EMAIL]" in sanitized_text
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized_text
    assert "[REDACTED_AWS_KEY]" in sanitized_text

def test_guardrails_no_redaction():
    text = "Just a normal message."
    sanitized_text, count = redact_secrets_and_pii(text)
    
    assert count == 0
    assert sanitized_text == text
