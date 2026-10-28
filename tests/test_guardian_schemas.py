"""Unit tests for Guardian schemas, data models, and enums."""

from __future__ import annotations

import pytest
from ghosttrace.guardian.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    CommandAnalysis,
    ExecutionResult,
    ExecutionStatus,
    GuardianStatus,
    HistoryEntry,
    RiskLevel,
)
from pydantic import ValidationError


def test_enums_values() -> None:
    """Verify all risk, approval, and execution enum values."""
    assert RiskLevel.SAFE == "SAFE"
    assert RiskLevel.LOW == "LOW"
    assert RiskLevel.MEDIUM == "MEDIUM"
    assert RiskLevel.HIGH == "HIGH"
    assert RiskLevel.BLOCKED == "BLOCKED"

    assert ApprovalStatus.PENDING == "PENDING"
    assert ApprovalStatus.APPROVED == "APPROVED"
    assert ApprovalStatus.REJECTED == "REJECTED"
    assert ApprovalStatus.CANCELLED == "CANCELLED"
    assert ApprovalStatus.EXPIRED == "EXPIRED"
    assert ApprovalStatus.BLOCKED == "BLOCKED"

    assert ExecutionStatus.NOT_EXECUTED == "NOT_EXECUTED"
    assert ExecutionStatus.RUNNING == "RUNNING"
    assert ExecutionStatus.SUCCESS == "SUCCESS"
    assert ExecutionStatus.FAILED == "FAILED"
    assert ExecutionStatus.TIMED_OUT == "TIMED_OUT"
    assert ExecutionStatus.CANCELLED == "CANCELLED"
    assert ExecutionStatus.BLOCKED == "BLOCKED"


def test_command_analysis_instantiation_and_frozen() -> None:
    """Verify CommandAnalysis validation, defaults, and immutability."""
    analysis = CommandAnalysis(
        original_command="git status",
        normalized_command="git status",
        executable="git",
        resolved_executable_path="/usr/bin/git",
        args=["status"],
        risk_level=RiskLevel.SAFE,
        risk_reasons=["Read-only command"],
        side_effects=["None"],
        is_permitted=True,
    )
    assert analysis.original_command == "git status"
    assert analysis.executable == "git"
    assert analysis.requires_approval is True
    assert analysis.contains_shell_operators is False
    assert analysis.rejected_operators == []
    assert analysis.is_malformed is False

    # Verify frozen immutability
    with pytest.raises(ValidationError):
        analysis.executable = "other"  # type: ignore[misc]


def test_approval_request_model() -> None:
    """Verify ApprovalRequest creation and field defaults."""
    analysis = CommandAnalysis(
        original_command="python --version",
        normalized_command="python --version",
        executable="python",
        risk_level=RiskLevel.SAFE,
        is_permitted=True,
    )
    req = ApprovalRequest(
        token="tok12345",
        analysis=analysis,
        working_dir="/workspace",
        created_at=100.0,
        expires_at=160.0,
        digest="digest123",
    )
    assert req.token == "tok12345"
    assert req.status == ApprovalStatus.PENDING
    assert req.working_dir == "/workspace"


def test_execution_result_model() -> None:
    """Verify ExecutionResult fields and defaults."""
    res = ExecutionResult(
        command="pytest -q",
        executable="pytest",
        args=["-q"],
        working_dir="/app",
        status=ExecutionStatus.SUCCESS,
        exit_code=0,
        stdout="5 passed",
        stderr="",
        duration_seconds=0.45,
        truncated=False,
    )
    assert res.status == ExecutionStatus.SUCCESS
    assert res.exit_code == 0
    assert res.duration_seconds == 0.45
    assert res.error_message is None


def test_history_entry_model() -> None:
    """Verify HistoryEntry fields."""
    entry = HistoryEntry(
        entry_id="abc12345",
        timestamp="14:00:00",
        command="dir",
        risk_level=RiskLevel.SAFE,
        approval_outcome=ApprovalStatus.APPROVED,
        execution_status=ExecutionStatus.SUCCESS,
        exit_code=0,
        duration_seconds=0.05,
        truncated=False,
        working_dir="/home",
    )
    assert entry.entry_id == "abc12345"
    assert entry.risk_level == RiskLevel.SAFE
    assert entry.exit_code == 0


def test_guardian_status_model() -> None:
    """Verify GuardianStatus telemetry snapshot model."""
    status = GuardianStatus(
        is_enabled=True,
        is_execution_enabled=True,
        requires_approval=True,
        block_high_risk=True,
        timeout_seconds=30,
        max_timeout_seconds=120,
        max_output_chars=12000,
        history_count=5,
        history_limit=50,
        pending_approval_count=1,
    )
    assert status.is_enabled is True
    assert status.history_count == 5
    assert status.pending_approval_count == 1
