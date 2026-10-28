"""Unit tests for the GuardianEngine central facade and orchestration."""

from __future__ import annotations

import sys

import pytest
from ghosttrace.guardian.engine import GuardianEngine
from ghosttrace.guardian.schemas import ExecutionStatus, RiskLevel


def test_engine_initialization_defaults() -> None:
    """Verify GuardianEngine initializes sub-components with default policy."""
    engine = GuardianEngine()
    assert engine.is_enabled is True
    assert engine.is_execution_enabled is True
    assert engine.policy.require_approval is True

    status = engine.get_status()
    assert status.is_enabled is True
    assert status.pending_approval_count == 0


def test_engine_analyze_and_explain() -> None:
    """Verify analyze and explain methods return structured data and reports."""
    engine = GuardianEngine()

    analysis = engine.analyze("python --version")
    assert analysis.executable == "python"
    assert analysis.risk_level == RiskLevel.SAFE

    explanation = engine.explain("git reset --hard")
    assert "COMMAND EXPLANATION & PURPOSE" in explanation
    assert "HIGH RISK" in explanation


def test_engine_request_approval_and_execution_lifecycle(tmp_path) -> None:
    """Verify full approval and execution lifecycle for a harmless command."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    # 1. Request approval for harmless python version command
    req = engine.request_approval(f'"{sys.executable}" --version', cwd=work_dir)
    assert req.token is not None
    assert engine.get_status().pending_approval_count == 1

    # 2. Execute with valid approval token
    result = engine.execute_approved(
        token=req.token,
        command=f'"{sys.executable}" --version',
        cwd=work_dir,
    )
    assert result.status == ExecutionStatus.SUCCESS
    assert result.exit_code == 0
    assert "Python" in result.stdout or "Python" in result.stderr

    # Session history must have recorded this execution
    history = engine.get_history()
    assert len(history) == 1
    assert history[0].execution_status == ExecutionStatus.SUCCESS


def test_engine_request_approval_blocked_commands(tmp_path) -> None:
    """Verify request_approval raises PermissionError on BLOCKED and HIGH commands."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    with pytest.raises(PermissionError) as exc_info:
        engine.request_approval("format C:", cwd=work_dir)
    assert "BLOCKED" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        engine.request_approval("git reset --hard", cwd=work_dir)
    assert "High-risk commands are blocked" in str(exc_info.value)

    # Both rejected requests must be recorded in history as BLOCKED
    history = engine.get_history()
    assert len(history) == 2
    assert all(e.execution_status == ExecutionStatus.BLOCKED for e in history)


def test_engine_disabled_state(tmp_path) -> None:
    """Verify disabling the engine blocks request_approval."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    engine.disable()
    assert engine.is_enabled is False

    with pytest.raises(PermissionError) as exc_info:
        engine.request_approval("python --version", cwd=work_dir)
    assert "disabled" in str(exc_info.value).lower()

    engine.enable()
    assert engine.is_enabled is True


def test_engine_execution_disabled_state(tmp_path) -> None:
    """Verify disabling execution permits analysis but blocks request_approval."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    engine.disable_execution()
    assert engine.is_execution_enabled is False

    # Analysis must still work
    analysis = engine.analyze("python --version")
    assert analysis.risk_level == RiskLevel.SAFE

    # Request approval must be blocked
    with pytest.raises(PermissionError) as exc_info:
        engine.request_approval("python --version", cwd=work_dir)
    assert "static analysis only" in str(exc_info.value).lower()

    engine.enable_execution()
    assert engine.is_execution_enabled is True


def test_engine_execute_with_invalid_token(tmp_path) -> None:
    """Verify execute_approved returns CANCELLED result on invalid or expired token."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    result = engine.execute_approved(
        token="invalid_token_xyz",
        command="python --version",
        cwd=work_dir,
    )
    assert result.status == ExecutionStatus.CANCELLED
    assert "not found" in (result.error_message or "").lower()


def test_engine_cancel_approval(tmp_path) -> None:
    """Verify cancelling approval requests."""
    engine = GuardianEngine()
    work_dir = str(tmp_path)

    req = engine.request_approval("python --version", cwd=work_dir)
    assert engine.get_status().pending_approval_count == 1

    success, _msg = engine.cancel_approval(req.token)
    assert success is True
    assert engine.get_status().pending_approval_count == 0

    # History must record cancellation
    history = engine.get_history()
    assert any(e.execution_status == ExecutionStatus.CANCELLED for e in history)


def test_engine_clear_history() -> None:
    """Verify clear_history empties session records."""
    engine = GuardianEngine()
    engine.history.record("cmd", RiskLevel.SAFE, "APPROVED", ExecutionStatus.SUCCESS)
    assert len(engine.get_history()) == 1

    engine.clear_history()
    assert len(engine.get_history()) == 0


def test_explanations_formatting_branches() -> None:
    """Verify all formatting branches and badges in explanations."""
    from ghosttrace.guardian.analyzer import CommandAnalyzer
    from ghosttrace.guardian.explanations import (
        format_command_analysis,
        format_execution_result,
        get_risk_badge,
    )
    from ghosttrace.guardian.schemas import ExecutionResult, ExecutionStatus, RiskLevel

    # Test badges
    for lvl in RiskLevel:
        badge = get_risk_badge(lvl)
        assert lvl.value in badge

    analyzer = CommandAnalyzer()

    # Analysis with resolved path, args, safer alternative (HIGH)
    high_analysis = analyzer.analyze("git reset --hard")
    report_high = format_command_analysis(high_analysis)
    assert "Risk Level  :" in report_high
    assert "Suggested Safer Alternative:" in report_high

    # Execution result with stderr, error message, truncated notice
    res_err = ExecutionResult(
        command="test_cmd",
        working_dir="D:\\GhostTrace",
        status=ExecutionStatus.FAILED,
        exit_code=1,
        stdout="",
        stderr="fatal error output",
        duration_seconds=0.1,
        truncated=True,
        error_message="Non-zero exit",
    )
    rendered_err = format_execution_result(res_err)
    assert "fatal error output" in rendered_err
    assert "Notice: Output stream was truncated" in rendered_err

    # Empty execution output
    res_empty = ExecutionResult(
        command="empty_cmd",
        working_dir="D:\\GhostTrace",
        status=ExecutionStatus.SUCCESS,
        exit_code=0,
        stdout="",
        stderr="",
        duration_seconds=0.01,
    )
    rendered_empty = format_execution_result(res_empty)
    assert "completed with no output" in rendered_empty
