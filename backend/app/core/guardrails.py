import re

EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PRIVATE_KEY_REGEX = r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----'
AWS_KEY_REGEX = r'(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])'
JWT_REGEX = r'ey[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
GITHUB_TOKEN_REGEX = r'(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}'

def redact_secrets_and_pii(text: str) -> tuple[str, int]:
    redaction_count = 0

    text, count1 = re.subn(EMAIL_REGEX, "[REDACTED_EMAIL]", text)
    redaction_count += count1
    text, count2 = re.subn(PRIVATE_KEY_REGEX, "[REDACTED_PRIVATE_KEY]", text)
    redaction_count += count2
    text, count3 = re.subn(AWS_KEY_REGEX, "[REDACTED_AWS_KEY]", text)
    redaction_count += count3
    text, count4 = re.subn(JWT_REGEX, "[REDACTED_JWT]", text)
    redaction_count += count4
    text, count5 = re.subn(GITHUB_TOKEN_REGEX, "[REDACTED_GITHUB_TOKEN]", text)
    redaction_count += count5

    return text, redaction_count
