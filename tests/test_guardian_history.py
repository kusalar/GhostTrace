"""Unit tests for Guardian in-memory execution history and sanitization."""

from __future__ import annotations

from ghosttrace.guardian.history import GuardianHistory
from ghosttrace.guardian.schemas import (
    ApprovalStatus,
    ExecutionResult,
    ExecutionStatus,
    RiskLevel,
)
from rich.table import Table


def test_history_record_and_get() -> None:
    """Verify recording and retrieving history entries."""
    hist = GuardianHistory(limit=10)
    assert hist.count == 0

    entry = hist.record(
        command="python --version",
        risk_level=RiskLevel.SAFE,
        approval_outcome=ApprovalStatus.APPROVED,
        execution_status=ExecutionStatus.SUCCESS,
        exit_code=0,
        duration_seconds=0.08,
        truncated=False,
        working_dir="/app",
    )
    assert hist.count == 1
    assert entry.command == "python --version"
    assert entry.risk_level == RiskLevel.SAFE

    entries = hist.get_entries()
    assert len(entries) == 1
    assert entries[0] == entry


def test_history_record_from_result() -> None:
    """Verify recording directly from an ExecutionResult object."""
    hist = GuardianHistory(limit=10)
    result = ExecutionResult(
        command="git status",
        executable="git",
        args=["status"],
        working_dir="/repo",
        status=ExecutionStatus.SUCCESS,
        exit_code=0,
        stdout="clean",
        duration_seconds=0.12,
    )
    entry = hist.record_result(result, risk_level=RiskLevel.SAFE)
    assert hist.count == 1
    assert entry.command == "git status"
    assert entry.exit_code == 0


def test_history_bounded_capacity_fifo() -> None:
    """Verify FIFO queue drops oldest entries when limit is reached."""
    hist = GuardianHistory(limit=3)

    hist.record("cmd1", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    hist.record("cmd2", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    hist.record("cmd3", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    assert hist.count == 3

    # Adding 4th must evict cmd1
    hist.record("cmd4", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    assert hist.count == 3
    commands = [e.command for e in hist.get_entries()]
    assert commands == ["cmd2", "cmd3", "cmd4"]


def test_history_clear() -> None:
    """Verify clear resets all history entries."""
    hist = GuardianHistory(limit=10)
    hist.record("cmd1", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    hist.record("cmd2", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS)
    assert hist.count == 2

    hist.clear()
    assert hist.count == 0
    assert hist.get_entries() == []


def test_history_sanitize_sensitive_credentials() -> None:
    """Verify passwords and API keys are redacted from recorded command strings."""
    hist = GuardianHistory(limit=10)

    entry1 = hist.record(
        command="curl -u user:pass --token secret_token_xyz http://api.com",
        risk_level=RiskLevel.MEDIUM,
        approval_outcome=ApprovalStatus.APPROVED,
        execution_status=ExecutionStatus.SUCCESS,
    )
    assert "secret_token_xyz" not in entry1.command
    assert "[REDACTED]" in entry1.command

    entry2 = hist.record(
        command="tool --password SuperSecretP@ss123",
        risk_level=RiskLevel.MEDIUM,
        approval_outcome=ApprovalStatus.APPROVED,
        execution_status=ExecutionStatus.SUCCESS,
    )
    assert "SuperSecretP@ss123" not in entry2.command
    assert "[REDACTED]" in entry2.command


def test_history_format_table() -> None:
    """Verify table generation returns a valid Rich Table."""
    hist = GuardianHistory(limit=10)
    hist.record(
        "git status", RiskLevel.SAFE, ApprovalStatus.APPROVED, ExecutionStatus.SUCCESS, exit_code=0
    )
    hist.record("format C:", RiskLevel.BLOCKED, ApprovalStatus.BLOCKED, ExecutionStatus.BLOCKED)

    table = hist.format_table()
    assert isinstance(table, Table)
    assert table.row_count == 2
