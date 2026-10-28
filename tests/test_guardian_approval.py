"""Unit tests for exact-command approval verification and token lifecycle."""

from __future__ import annotations

import time

import pytest
from ghosttrace.guardian.analyzer import CommandAnalyzer
from ghosttrace.guardian.approval import ApprovalManager
from ghosttrace.guardian.policy import ExecutionPolicy
from ghosttrace.guardian.schemas import ApprovalStatus


def test_approval_creation_and_consumption_success(tmp_path) -> None:
    """Verify approval request creation and successful one-time consumption."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager(default_ttl_seconds=60.0)
    policy = ExecutionPolicy()
    work_dir = str(tmp_path)

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    fingerprint = policy.get_fingerprint()

    # 1. Create request
    req = mgr.create_request(analysis, working_dir=work_dir, policy_fingerprint=fingerprint)
    assert req.token is not None
    assert req.status == ApprovalStatus.PENDING
    assert mgr.pending_count == 1
    assert mgr.get_latest_pending() == req

    # 2. Successfully validate and consume
    valid, _reason, consumed_req = mgr.validate_and_consume(
        token=req.token,
        command="python --version",
        working_dir=work_dir,
        policy_fingerprint=fingerprint,
    )
    assert valid is True
    assert consumed_req is not None
    assert consumed_req.status == ApprovalStatus.APPROVED
    assert mgr.pending_count == 0

    # 3. Reusing the same token must fail (strictly one-time use!)
    reused_valid, reused_reason, _ = mgr.validate_and_consume(
        token=req.token,
        command="python --version",
        working_dir=work_dir,
        policy_fingerprint=fingerprint,
    )
    assert reused_valid is False
    assert "already consumed" in reused_reason.lower()


def test_approval_high_and_blocked_commands_cannot_be_approved(tmp_path) -> None:
    """Verify HIGH and BLOCKED commands cannot be issued approval tokens."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager()
    policy = ExecutionPolicy()
    work_dir = str(tmp_path)
    fingerprint = policy.get_fingerprint()

    # High risk command
    high_analysis = analyzer.analyze("git reset --hard", cwd=work_dir)
    with pytest.raises(PermissionError) as exc_info:
        mgr.create_request(high_analysis, working_dir=work_dir, policy_fingerprint=fingerprint)
    assert "cannot issue approval" in str(exc_info.value).lower()

    # Blocked command
    blocked_analysis = analyzer.analyze("format C:", cwd=work_dir)
    with pytest.raises(PermissionError):
        mgr.create_request(blocked_analysis, working_dir=work_dir, policy_fingerprint=fingerprint)


def test_modified_command_invalidates_approval(tmp_path) -> None:
    """Verify modifying the command string invalidates the approval token."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager()
    policy = ExecutionPolicy()
    work_dir = str(tmp_path)
    fingerprint = policy.get_fingerprint()

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    req = mgr.create_request(analysis, working_dir=work_dir, policy_fingerprint=fingerprint)

    # Attempt execution with different command
    valid, reason, rejected_req = mgr.validate_and_consume(
        token=req.token,
        command="python -V",  # modified text
        working_dir=work_dir,
        policy_fingerprint=fingerprint,
    )
    assert valid is False
    assert "does not match the approved command" in reason
    assert rejected_req is not None
    assert rejected_req.status == ApprovalStatus.REJECTED


def test_changed_working_directory_invalidates_approval(tmp_path) -> None:
    """Verify changing working directory invalidates the approval token."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager()
    policy = ExecutionPolicy()
    work_dir = str(tmp_path / "dir1")
    other_dir = str(tmp_path / "dir2")
    fingerprint = policy.get_fingerprint()

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    req = mgr.create_request(analysis, working_dir=work_dir, policy_fingerprint=fingerprint)

    valid, reason, rejected_req = mgr.validate_and_consume(
        token=req.token,
        command="python --version",
        working_dir=other_dir,  # changed directory
        policy_fingerprint=fingerprint,
    )
    assert valid is False
    assert "integrity check failed" in reason
    assert rejected_req is not None
    assert rejected_req.status == ApprovalStatus.REJECTED


def test_changed_policy_invalidates_approval(tmp_path) -> None:
    """Verify changing security policy parameters invalidates the approval token."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager()
    policy1 = ExecutionPolicy(timeout_seconds=30)
    policy2 = ExecutionPolicy(timeout_seconds=60)
    work_dir = str(tmp_path)

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    req = mgr.create_request(
        analysis, working_dir=work_dir, policy_fingerprint=policy1.get_fingerprint()
    )

    valid, reason, rejected_req = mgr.validate_and_consume(
        token=req.token,
        command="python --version",
        working_dir=work_dir,
        policy_fingerprint=policy2.get_fingerprint(),  # changed policy
    )
    assert valid is False
    assert "integrity check failed" in reason
    assert rejected_req is not None
    assert rejected_req.status == ApprovalStatus.REJECTED


def test_expired_token_is_rejected(tmp_path) -> None:
    """Verify expired approval tokens are rejected upon evaluation."""
    analyzer = CommandAnalyzer()
    # Microsecond TTL
    mgr = ApprovalManager(default_ttl_seconds=0.01)
    policy = ExecutionPolicy()
    work_dir = str(tmp_path)
    fingerprint = policy.get_fingerprint()

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    req = mgr.create_request(
        analysis, working_dir=work_dir, policy_fingerprint=fingerprint, ttl_seconds=0.01
    )

    time.sleep(0.05)  # wait for expiration

    valid, reason, expired_req = mgr.validate_and_consume(
        token=req.token,
        command="python --version",
        working_dir=work_dir,
        policy_fingerprint=fingerprint,
    )
    assert valid is False
    assert "expired" in reason.lower()
    assert expired_req is not None
    assert expired_req.status == ApprovalStatus.EXPIRED


def test_cancel_approval_request(tmp_path) -> None:
    """Verify cancelling specific or all approval requests."""
    analyzer = CommandAnalyzer()
    mgr = ApprovalManager()
    policy = ExecutionPolicy()
    work_dir = str(tmp_path)
    fingerprint = policy.get_fingerprint()

    analysis = analyzer.analyze("python --version", cwd=work_dir)
    req1 = mgr.create_request(analysis, working_dir=work_dir, policy_fingerprint=fingerprint)
    req2 = mgr.create_request(analysis, working_dir=work_dir, policy_fingerprint=fingerprint)

    assert mgr.pending_count == 2

    # Cancel req1 by token
    success, _msg = mgr.cancel_request(req1.token)
    assert success is True
    assert mgr.pending_count == 1
    assert mgr.get_request(req1.token) is None
    assert mgr.get_request(req2.token) is not None

    # Cancel non-existent token
    success, _msg = mgr.cancel_request("invalid_token")
    assert success is False

    # Cancel all
    success, _msg = mgr.cancel_request()
    assert success is True
    assert mgr.pending_count == 0
