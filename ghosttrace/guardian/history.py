"""Bounded, session-only in-memory execution history for GhostTrace Command Guardian."""

from __future__ import annotations

import datetime
import uuid
from collections import deque

from rich.table import Table

from ghosttrace.guardian.schemas import (
    ApprovalStatus,
    ExecutionResult,
    ExecutionStatus,
    HistoryEntry,
    RiskLevel,
)


class GuardianHistory:
    """Session-only bounded FIFO queue storing command execution audit records."""

    def __init__(self, limit: int = 50) -> None:
        self.limit = max(1, min(limit, 500))
        self._entries: deque[HistoryEntry] = deque(maxlen=self.limit)

    def record(
        self,
        command: str,
        risk_level: RiskLevel,
        approval_outcome: ApprovalStatus,
        execution_status: ExecutionStatus,
        exit_code: int | None = None,
        duration_seconds: float = 0.0,
        truncated: bool = False,
        working_dir: str = "",
    ) -> HistoryEntry:
        """Create and store a sanitized execution history record."""
        sanitized_cmd = self._sanitize_command(command)
        now_str = datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")

        entry = HistoryEntry(
            entry_id=uuid.uuid4().hex[:8],
            timestamp=now_str,
            command=sanitized_cmd,
            risk_level=risk_level,
            approval_outcome=approval_outcome,
            execution_status=execution_status,
            exit_code=exit_code,
            duration_seconds=duration_seconds,
            truncated=truncated,
            working_dir=working_dir,
        )

        self._entries.append(entry)
        return entry

    def record_result(
        self,
        result: ExecutionResult,
        risk_level: RiskLevel,
        approval_outcome: ApprovalStatus = ApprovalStatus.APPROVED,
    ) -> HistoryEntry:
        """Record outcome directly from an ExecutionResult object."""
        return self.record(
            command=result.command,
            risk_level=risk_level,
            approval_outcome=approval_outcome,
            execution_status=result.status,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
            truncated=result.truncated,
            working_dir=result.working_dir,
        )

    def get_entries(self) -> list[HistoryEntry]:
        """Return a snapshot list of current session history entries."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear all session history records."""
        self._entries.clear()

    @property
    def count(self) -> int:
        """Return the number of entries currently stored."""
        return len(self._entries)

    def format_table(self) -> Table:
        """Render a formatted Rich Table representing session command history."""
        table = Table(
            title="GUARDIAN SESSION EXECUTION HISTORY",
            border_style="dim green",
            show_header=True,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Time", style="#88aa88", width=10)
        table.add_column("Risk", width=10)
        table.add_column("Command", style="bold #00ff66")
        table.add_column("Approval", style="#ffcc00", width=12)
        table.add_column("Status", width=12)
        table.add_column("Exit", width=6)
        table.add_column("Duration", style="dim", width=10)

        for idx, entry in enumerate(self._entries, start=1):
            risk_style = {
                RiskLevel.SAFE: "#33ff33",
                RiskLevel.LOW: "#00ffcc",
                RiskLevel.MEDIUM: "#ffcc00",
                RiskLevel.HIGH: "#ff7700",
                RiskLevel.BLOCKED: "#ff3333",
            }.get(entry.risk_level, "#ffffff")

            status_style = {
                ExecutionStatus.SUCCESS: "#33ff33",
                ExecutionStatus.FAILED: "#ff5555",
                ExecutionStatus.TIMED_OUT: "#ffaa00",
                ExecutionStatus.CANCELLED: "#888888",
                ExecutionStatus.BLOCKED: "#ff3333",
            }.get(entry.execution_status, "#aaaaaa")

            exit_str = str(entry.exit_code) if entry.exit_code is not None else "-"
            dur_str = f"{entry.duration_seconds:.2f}s" if entry.duration_seconds > 0 else "-"

            table.add_row(
                str(idx),
                entry.timestamp,
                f"[{risk_style}]{entry.risk_level.value}[/]",
                entry.command,
                entry.approval_outcome.value,
                f"[{status_style}]{entry.execution_status.value}[/]",
                exit_str,
                dur_str,
            )

        return table

    @staticmethod
    def _sanitize_command(command: str) -> str:
        """Sanitize passwords or API tokens if embedded in common CLI argument patterns."""
        # Simple redacting of obvious sensitive patterns like --password <val> or token=<val>
        import re

        sanitized = re.sub(
            r"(--password|--token|--api[-_]?key|-p)\s+([^\s]+)",
            r"\1 [REDACTED]",
            command,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            r"(password|token|apikey|secret)=([^\s&;]+)",
            r"\1=[REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )
        return sanitized
