"""Tests for sensitive data detection and redaction."""

from __future__ import annotations

from ghosttrace.memory.redaction import contains_sensitive_data, redact_sensitive_data


def test_redact_api_keys() -> None:
    """Ensure typical API keys and secrets are cleanly redacted."""
    raw = (
        "My key is sk-1234567890abcdef1234567890abcdef and my token is "
        "ghp_1234567890abcdef1234567890abcdef123456."
    )
    redacted = redact_sensitive_data(raw)
    assert "sk-" not in redacted
    assert "ghp_" not in redacted
    assert "[REDACTED:OPENAI_API_KEY]" in redacted
    assert "[REDACTED:GITHUB_TOKEN]" in redacted


def test_redact_private_key() -> None:
    """Ensure private key blocks are replaced."""
    raw = (
        "Here is my key:\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0\n"
        "-----END RSA PRIVATE KEY-----\n"
        "End of message."
    )
    redacted = redact_sensitive_data(raw)
    assert "MIIEow" not in redacted
    assert "[REDACTED:PRIVATE_KEY]" in redacted


def test_redact_connection_strings() -> None:
    """Ensure database connection strings with passwords are redacted."""
    raw = "Connecting to postgresql://admin:SuperSecretPassword123@localhost:5432/mydb"
    redacted = redact_sensitive_data(raw)
    assert "SuperSecretPassword123" not in redacted
    assert "[REDACTED:PASSWORD]" in redacted


def test_contains_sensitive_data() -> None:
    """Verify boolean detection of secrets."""
    assert contains_sensitive_data("Normal programming notes about Python") is False
    assert (
        contains_sensitive_data("API token: xoxb-1234567890-123456789012-abcdef12345678901234")
        is True
    )
    assert contains_sensitive_data("password='super_secret_value_123!'") is True
