"""Unit tests for ExecutionPolicy permission rules and parameter bounds."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.guardian.analyzer import CommandAnalyzer
from ghosttrace.guardian.policy import ExecutionPolicy


def test_policy_instantiation_and_defaults() -> None:
    """Verify policy defaults and parameter clamping."""
    policy = ExecutionPolicy()
    assert policy.enabled is True
    assert policy.execution_enabled is True
    assert policy.require_approval is True
    assert policy.block_high_risk is True
    assert policy.timeout_seconds == 30
    assert policy.max_timeout_seconds == 120
    assert policy.max_output_chars == 12000
    assert policy.history_limit == 50


def test_policy_from_settings() -> None:
    """Verify policy factory from Settings instance."""
    settings = Settings(
        guard_enabled=True,
        guard_execution_enabled=False,
        guard_timeout_seconds=45,
        guard_max_output_chars=8000,
        guard_history_limit=25,
    )
    policy = ExecutionPolicy.from_settings(settings)
    assert policy.enabled is True
    assert policy.execution_enabled is False
    assert policy.timeout_seconds == 45
    assert policy.max_output_chars == 8000
    assert policy.history_limit == 25


def test_policy_clamping_bounds() -> None:
    """Verify bounds clamping on extreme constructor inputs."""
    policy = ExecutionPolicy(
        timeout_seconds=9999,
        max_timeout_seconds=1000,
        max_output_chars=50,
        history_limit=10000,
    )
    assert policy.max_timeout_seconds == 600
    assert policy.timeout_seconds == 600
    assert policy.max_output_chars == 100
    assert policy.history_limit == 500


def test_policy_check_permission_rules() -> None:
    """Verify check_permission enforces every security rule."""
    analyzer = CommandAnalyzer()
    policy = ExecutionPolicy()

    # 1. Permitted safe command
    safe_analysis = analyzer.analyze("python --version")
    permitted, reason = policy.check_permission(safe_analysis)
    assert permitted is True

    # 2. Guardian disabled
    disabled_policy = ExecutionPolicy(enabled=False)
    permitted, reason = disabled_policy.check_permission(safe_analysis)
    assert permitted is False
    assert "disabled" in reason.lower()

    # 3. Execution disabled (analysis only)
    no_exec_policy = ExecutionPolicy(execution_enabled=False)
    permitted, reason = no_exec_policy.check_permission(safe_analysis)
    assert permitted is False
    assert "static analysis only" in reason.lower()

    # 4. Malformed command
    malformed_analysis = analyzer.analyze('git commit -m "unclosed')
    permitted, reason = policy.check_permission(malformed_analysis)
    assert permitted is False
    assert "malformed" in reason.lower()

    # 5. Shell operators
    operator_analysis = analyzer.analyze("git status && dir")
    permitted, reason = policy.check_permission(operator_analysis)
    assert permitted is False
    assert "shell chaining" in reason.lower()

    # 6. BLOCKED risk level
    blocked_analysis = analyzer.analyze("format C:")
    permitted, reason = policy.check_permission(blocked_analysis)
    assert permitted is False
    assert "BLOCKED" in reason

    # 7. HIGH risk level blocked by default policy
    high_analysis = analyzer.analyze("git reset --hard")
    permitted, reason = policy.check_permission(high_analysis)
    assert permitted is False
    assert "High-risk commands are blocked" in reason

    # 8. Missing executable
    empty_analysis = analyzer.analyze("   ")
    permitted, reason = policy.check_permission(empty_analysis)
    assert permitted is False

    # 9. Non-existent executable on disk or PATH
    unresolved_analysis = analyzer.analyze("fake_binary_tool_xyz --help")
    permitted, reason = policy.check_permission(unresolved_analysis)
    assert permitted is False
    assert "not found on PATH" in reason


def test_policy_fingerprint() -> None:
    """Verify policy fingerprint generates a unique representation."""
    policy1 = ExecutionPolicy(timeout_seconds=30)
    policy2 = ExecutionPolicy(timeout_seconds=45)
    assert policy1.get_fingerprint() != policy2.get_fingerprint()
