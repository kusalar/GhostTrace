"""Execution policy and permission enforcement for GhostTrace Command Guardian."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.guardian.schemas import CommandAnalysis, RiskLevel


class ExecutionPolicy:
    """Enforces execution rules, risk restrictions, and configuration safeguards."""

    def __init__(
        self,
        enabled: bool = True,
        execution_enabled: bool = True,
        require_approval: bool = True,
        block_high_risk: bool = True,
        timeout_seconds: int = 30,
        max_timeout_seconds: int = 120,
        max_output_chars: int = 12000,
        history_limit: int = 50,
    ) -> None:
        self.enabled = enabled
        self.execution_enabled = execution_enabled
        # In accordance with safety requirements, require_approval is strictly enforced
        self.require_approval = True
        self.block_high_risk = block_high_risk
        self.max_timeout_seconds = max(1, min(max_timeout_seconds, 600))
        self.timeout_seconds = max(1, min(timeout_seconds, self.max_timeout_seconds))
        self.max_output_chars = max(100, min(max_output_chars, 1_000_000))
        self.history_limit = max(1, min(history_limit, 500))

    @classmethod
    def from_settings(cls, settings: Settings) -> ExecutionPolicy:
        """Instantiate ExecutionPolicy directly from application settings."""
        return cls(
            enabled=getattr(settings, "guard_enabled", True),
            execution_enabled=getattr(settings, "guard_execution_enabled", True),
            require_approval=getattr(settings, "guard_require_approval", True),
            block_high_risk=getattr(settings, "guard_block_high_risk", True),
            timeout_seconds=getattr(settings, "guard_timeout_seconds", 30),
            max_timeout_seconds=getattr(settings, "guard_max_timeout_seconds", 120),
            max_output_chars=getattr(settings, "guard_max_output_chars", 12000),
            history_limit=getattr(settings, "guard_history_limit", 50),
        )

    def check_permission(self, analysis: CommandAnalysis) -> tuple[bool, str]:
        """Verify whether the command analysis meets all safety criteria for execution.

        Returns:
            (is_permitted, reason_message)
        """
        if not self.enabled:
            return False, "Command Guardian subsystem is currently disabled."

        if not self.execution_enabled:
            return False, "Command execution is disabled by configuration (static analysis only)."

        if analysis.is_malformed:
            return False, "Command is malformed or contains unbalanced quotation marks."

        if analysis.contains_shell_operators:
            ops = ", ".join(analysis.rejected_operators)
            return (
                False,
                f"Unsupported shell chaining or redirection operators detected ({ops}). "
                "Restricted execution does not permit subshell evaluation.",
            )

        if analysis.risk_level == RiskLevel.BLOCKED:
            return (
                False,
                "Command is classified as BLOCKED and can never be executed under any "
                "circumstances.",
            )

        if analysis.risk_level == RiskLevel.HIGH and self.block_high_risk:
            return False, "High-risk commands are blocked by default execution safety policy."

        if not analysis.executable:
            return False, "No valid executable or binary specified in command."

        if not analysis.resolved_executable_path:
            return False, f"Executable '{analysis.executable}' was not found on PATH or filesystem."

        return True, "Execution is permitted subject to explicit user approval."

    def get_fingerprint(self) -> str:
        """Return a string fingerprint representing active policy constraints."""
        return (
            f"en={self.enabled}:exec={self.execution_enabled}:appr={self.require_approval}:"
            f"bhr={self.block_high_risk}:to={self.timeout_seconds}:max_out={self.max_output_chars}"
        )
