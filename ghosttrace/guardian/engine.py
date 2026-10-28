"""Guardian facade engine coordinating analysis, policy, approval, execution, and history."""

from __future__ import annotations

import logging
import os

from ghosttrace.config.settings import Settings
from ghosttrace.guardian.analyzer import CommandAnalyzer
from ghosttrace.guardian.approval import ApprovalManager
from ghosttrace.guardian.executor import ControlledExecutor
from ghosttrace.guardian.explanations import format_command_explanation
from ghosttrace.guardian.history import GuardianHistory
from ghosttrace.guardian.policy import ExecutionPolicy
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

logger = logging.getLogger("ghosttrace.guardian.engine")


class GuardianEngine:
    """Central facade coordinating the Command Guardian and execution safety subsystem."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings
        self.policy = ExecutionPolicy.from_settings(settings) if settings else ExecutionPolicy()
        self.analyzer = CommandAnalyzer()
        self.approval_mgr = ApprovalManager(default_ttl_seconds=60.0)
        self.executor = ControlledExecutor(
            timeout_seconds=self.policy.timeout_seconds,
            max_output_chars=self.policy.max_output_chars,
        )
        self.history = GuardianHistory(limit=self.policy.history_limit)

    @property
    def is_enabled(self) -> bool:
        """Return whether Guardian subsystem is active."""
        return self.policy.enabled

    @property
    def is_execution_enabled(self) -> bool:
        """Return whether command execution is enabled."""
        return self.policy.execution_enabled

    def enable(self) -> None:
        """Enable Guardian subsystem and restore policy enforcement."""
        self.policy.enabled = True
        logger.info("Command Guardian subsystem enabled.")

    def disable(self) -> None:
        """Disable Command Guardian subsystem and halt execution."""
        self.policy.enabled = False
        logger.info("Command Guardian subsystem disabled.")

    def enable_execution(self) -> None:
        """Enable controlled command execution."""
        self.policy.execution_enabled = True
        logger.info("Guardian command execution enabled.")

    def disable_execution(self) -> None:
        """Disable controlled command execution (static analysis only mode)."""
        self.policy.execution_enabled = False
        logger.info("Guardian command execution disabled (analysis only mode).")

    def analyze(self, command: str, cwd: str | None = None) -> CommandAnalysis:
        """Perform static risk and pattern analysis on a command without execution."""
        working_dir = cwd or os.getcwd()
        return self.analyzer.analyze(command, cwd=working_dir)

    def explain(self, command: str, cwd: str | None = None) -> str:
        """Generate human-readable explanation of command purpose and safety."""
        analysis = self.analyze(command, cwd=cwd)
        return format_command_explanation(analysis)

    def request_approval(
        self,
        command: str,
        cwd: str | None = None,
        ttl_seconds: float = 60.0,
    ) -> ApprovalRequest:
        """Perform static analysis and issue a single-use approval request if permitted.

        Raises:
            PermissionError: If command policy prevents execution or command is HIGH/BLOCKED.
        """
        working_dir = cwd or os.getcwd()
        analysis = self.analyze(command, cwd=working_dir)

        permitted, reason = self.policy.check_permission(analysis)
        if not permitted:
            # Record blocked attempt in session history
            self.history.record(
                command=command,
                risk_level=analysis.risk_level,
                approval_outcome=ApprovalStatus.BLOCKED,
                execution_status=ExecutionStatus.BLOCKED,
                working_dir=working_dir,
            )
            raise PermissionError(reason)

        request = self.approval_mgr.create_request(
            analysis=analysis,
            working_dir=working_dir,
            policy_fingerprint=self.policy.get_fingerprint(),
            ttl_seconds=ttl_seconds,
        )
        return request

    def execute_approved(
        self,
        token: str,
        command: str,
        cwd: str | None = None,
    ) -> ExecutionResult:
        """Validate single-use approval token and execute command under controlled conditions."""
        working_dir = cwd or os.getcwd()

        valid, reason, request = self.approval_mgr.validate_and_consume(
            token=token,
            command=command,
            working_dir=working_dir,
            policy_fingerprint=self.policy.get_fingerprint(),
        )

        if not valid or request is None:
            # Record failed approval attempt
            risk_lvl = request.analysis.risk_level if request else RiskLevel.MEDIUM
            outcome_status = request.status if request else ApprovalStatus.REJECTED
            self.history.record(
                command=command,
                risk_level=risk_lvl,
                approval_outcome=outcome_status,
                execution_status=ExecutionStatus.CANCELLED,
                working_dir=working_dir,
            )
            return ExecutionResult(
                command=command,
                working_dir=working_dir,
                status=ExecutionStatus.CANCELLED,
                error_message=reason,
            )

        analysis = request.analysis

        # Re-check policy before invocation
        permitted, policy_reason = self.policy.check_permission(analysis)
        if not permitted:
            self.history.record(
                command=command,
                risk_level=analysis.risk_level,
                approval_outcome=ApprovalStatus.BLOCKED,
                execution_status=ExecutionStatus.BLOCKED,
                working_dir=working_dir,
            )
            return ExecutionResult(
                command=command,
                working_dir=working_dir,
                status=ExecutionStatus.BLOCKED,
                error_message=f"Execution blocked by policy: {policy_reason}",
            )

        target_executable = analysis.resolved_executable_path or analysis.executable or ""

        # Execute command via controlled subprocess
        result = self.executor.execute(
            executable=target_executable,
            args=analysis.args,
            working_dir=working_dir,
            timeout=self.policy.timeout_seconds,
            original_command=analysis.original_command,
        )

        # Record outcome in session history
        self.history.record_result(
            result=result,
            risk_level=analysis.risk_level,
            approval_outcome=ApprovalStatus.APPROVED,
        )

        return result

    def cancel_approval(self, token: str | None = None) -> tuple[bool, str]:
        """Cancel a pending approval request or all pending requests."""
        if token:
            req = self.approval_mgr.get_request(token)
            if req:
                self.history.record(
                    command=req.analysis.original_command,
                    risk_level=req.analysis.risk_level,
                    approval_outcome=ApprovalStatus.CANCELLED,
                    execution_status=ExecutionStatus.CANCELLED,
                    working_dir=req.working_dir,
                )
        else:
            for pending_req in list(self.approval_mgr._pending_requests.values()):
                self.history.record(
                    command=pending_req.analysis.original_command,
                    risk_level=pending_req.analysis.risk_level,
                    approval_outcome=ApprovalStatus.CANCELLED,
                    execution_status=ExecutionStatus.CANCELLED,
                    working_dir=pending_req.working_dir,
                )
        return self.approval_mgr.cancel_request(token)

    def get_status(self) -> GuardianStatus:
        """Compile a typed status snapshot of the Guardian subsystem."""
        return GuardianStatus(
            is_enabled=self.policy.enabled,
            is_execution_enabled=self.policy.execution_enabled,
            requires_approval=self.policy.require_approval,
            block_high_risk=self.policy.block_high_risk,
            timeout_seconds=self.policy.timeout_seconds,
            max_timeout_seconds=self.policy.max_timeout_seconds,
            max_output_chars=self.policy.max_output_chars,
            history_count=self.history.count,
            history_limit=self.history.limit,
            pending_approval_count=self.approval_mgr.pending_count,
        )

    def get_history(self) -> list[HistoryEntry]:
        """Return execution history records."""
        return self.history.get_entries()

    def clear_history(self) -> None:
        """Clear execution history records."""
        self.history.clear()
