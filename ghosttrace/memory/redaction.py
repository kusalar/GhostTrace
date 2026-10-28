"""Sensitive data detection and redaction for GhostTrace memory and project indexing.

Provides conservative pattern matching for common API keys, tokens, passwords,
private keys, and connection credentials before persistent storage or export.

Disclaimer:
    Heuristic redaction is conservative and designed for defense-in-depth, but does
    not guarantee detection of all arbitrary or proprietary secret formats.
"""

from __future__ import annotations

import re

# Compiled regex patterns for common credentials and secret patterns
REDACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Private Key Blocks
    (
        re.compile(
            r"-----BEGIN [A-Z0-9_\- ]+PRIVATE KEY-----"
            r"[\s\S]*?-----END [A-Z0-9_\- ]+PRIVATE KEY-----",
            re.MULTILINE,
        ),
        "[REDACTED:PRIVATE_KEY]",
    ),
    # GitHub Tokens
    (
        re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b"),
        "[REDACTED:GITHUB_TOKEN]",
    ),
    (
        re.compile(r"\bgithub_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}\b"),
        "[REDACTED:GITHUB_TOKEN]",
    ),
    # GitLab Personal Access Tokens
    (
        re.compile(r"\bglpat-[a-zA-Z0-9\-]{20,}\b"),
        "[REDACTED:GITLAB_TOKEN]",
    ),
    # Slack Tokens
    (
        re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,}-[0-9a-zA-Z]{10,}-[0-9a-zA-Z]{16,}\b"),
        "[REDACTED:SLACK_TOKEN]",
    ),
    # AWS Access Key ID
    (
        re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
        "[REDACTED:AWS_KEY_ID]",
    ),
    # AWS Secret Access Key
    (
        re.compile(
            r"(?i)(aws_secret_access_key|aws_session_token)\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?"
        ),
        r"\1=[REDACTED:AWS_SECRET]",
    ),
    # Google API Keys
    (
        re.compile(r"\bAIzaSy[a-zA-Z0-9_\-]{33}\b"),
        "[REDACTED:GOOGLE_API_KEY]",
    ),
    # OpenAI API Keys
    (
        re.compile(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{32,}\b"),
        "[REDACTED:OPENAI_API_KEY]",
    ),
    # Bearer Tokens in Headers or Strings
    (
        re.compile(r"(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{24,})\b"),
        "Bearer [REDACTED:BEARER_TOKEN]",
    ),
    # Database Connection Strings with Credentials
    (
        re.compile(
            r"(?i)\b(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|mssql)://"
            r"([^:\s@]+):([^@\s]+)@([^\/\s]+)"
        ),
        r"\1://\2:[REDACTED:PASSWORD]@\4",
    ),
    # Password Assignments
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|db_pass|database_password)\s*[:=]\s*['\"]([^'\"]{4,})['\"]"
        ),
        r"\1='[REDACTED:PASSWORD]'",
    ),
    # Generic API Keys and Secrets
    (
        re.compile(
            r"(?i)\b(api_key|apikey|secret_key|secretkey|auth_token|access_token)"
            r"\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?"
        ),
        r"\1='[REDACTED:API_KEY]'",
    ),
]


def redact_sensitive_data(text: str) -> str:
    """Detect and replace recognizable secrets with redaction placeholders.

    Args:
        text: Raw text content to inspect.

    Returns:
        Redacted text safe for persistent storage, retrieval, and export.
    """
    if not text:
        return ""

    redacted = text
    for pattern, replacement in REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)

    return redacted


def contains_sensitive_data(text: str) -> bool:
    """Return True if the text contains any recognizable credential or secret pattern."""
    if not text:
        return False

    return any(pattern.search(text) for pattern, _ in REDACTION_PATTERNS)
