"""Data models, enums, and schemas for the GhostTrace Command Guardian subsystem."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(StrEnum):
    """Command safety risk classifications."""

    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class ApprovalStatus(StrEnum):
    """Status lifecycle states for command approval requests."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"


class ExecutionStatus(StrEnum):
    """Subprocess execution lifecycle states."""

    NOT_EXECUTED = "NOT_EXECUTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class CommandAnalysis(BaseModel):
    """Comprehensive static analysis and risk classification of a terminal command."""

    model_config = ConfigDict(frozen=True)

    original_command: str = Field(description="Raw terminal command string as supplied by user.")
    normalized_command: str = Field(
        description="Normalized command string used for pattern evaluation."
    )
    executable: str | None = Field(
        default=None, description="Extracted primary executable or binary name."
    )
    resolved_executable_path: str | None = Field(
        default=None, description="Resolved absolute path to executable on PATH or disk, if found."
    )
    args: list[str] = Field(default_factory=list, description="Parsed arguments and options.")
    risk_level: RiskLevel = Field(description="Assessed risk classification level.")
    risk_reasons: list[str] = Field(
        default_factory=list, description="Explanations justifying the assigned risk level."
    )
    side_effects: list[str] = Field(
        default_factory=list, description="Predicted operational side effects of execution."
    )
    is_permitted: bool = Field(
        description="Whether execution is permitted under active security policy."
    )
    requires_approval: bool = Field(
        default=True,
        description="Whether explicit user confirmation is strictly mandatory prior to execution.",
    )
    safer_alternative: str | None = Field(
        default=None,
        description="Recommended alternative command offering safer operational semantics.",
    )
    contains_shell_operators: bool = Field(
        default=False,
        description="Flag indicating presence of unquoted shell chaining or redirection operators.",
    )
    rejected_operators: list[str] = Field(
        default_factory=list, description="List of unquoted shell operators detected in command."
    )
    is_malformed: bool = Field(
        default=False, description="Flag indicating syntactic syntax errors or unbalanced quotes."
    )


class ApprovalRequest(BaseModel):
    """Cryptographically anchored approval request for single-use command execution."""

    model_config = ConfigDict(frozen=True)

    token: str = Field(description="Unique single-use approval token identifier.")
    analysis: CommandAnalysis = Field(
        description="Associated static analysis of the command to execute."
    )
    working_dir: str = Field(description="Validated execution working directory.")
    created_at: float = Field(description="Epoch timestamp when request was generated.")
    expires_at: float = Field(description="Epoch timestamp when request expires.")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Current approval status."
    )
    digest: str = Field(
        description="Cryptographic HMAC digest locking command parameters and context."
    )


class ExecutionResult(BaseModel):
    """Structured outcome of a controlled command execution."""

    model_config = ConfigDict(frozen=True)

    command: str = Field(description="Executed command string.")
    executable: str | None = Field(default=None, description="Executed binary or executable name.")
    args: list[str] = Field(default_factory=list, description="Executed argument list.")
    working_dir: str = Field(description="Working directory where command was executed.")
    status: ExecutionStatus = Field(description="Terminal execution status.")
    exit_code: int | None = Field(
        default=None, description="Process exit code (None if terminated or blocked)."
    )
    stdout: str = Field(default="", description="Captured standard output (bounded).")
    stderr: str = Field(default="", description="Captured standard error (bounded).")
    duration_seconds: float = Field(default=0.0, description="Execution elapsed time in seconds.")
    truncated: bool = Field(
        default=False, description="Whether output stream exceeded configured size bounds."
    )
    error_message: str | None = Field(
        default=None, description="Internal executor error or timeout details."
    )


class HistoryEntry(BaseModel):
    """Bounded in-memory execution history audit record."""

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(description="Unique record identifier.")
    timestamp: str = Field(description="ISO 8601 formatted timestamp of execution event.")
    command: str = Field(description="Command string subjected to execution.")
    risk_level: RiskLevel = Field(description="Risk level at time of execution.")
    approval_outcome: ApprovalStatus = Field(description="Outcome of user approval stage.")
    execution_status: ExecutionStatus = Field(description="Final execution outcome status.")
    exit_code: int | None = Field(default=None, description="Process exit code if executed.")
    duration_seconds: float = Field(default=0.0, description="Duration of command execution.")
    truncated: bool = Field(default=False, description="Whether output was truncated.")
    working_dir: str = Field(default="", description="Working directory of execution.")


class GuardianStatus(BaseModel):
    """Runtime telemetry snapshot of the Command Guardian subsystem."""

    model_config = ConfigDict(frozen=True)

    is_enabled: bool = Field(description="Whether the Guardian subsystem is active.")
    is_execution_enabled: bool = Field(description="Whether command execution is permitted.")
    requires_approval: bool = Field(description="Whether explicit approval is strictly enforced.")
    block_high_risk: bool = Field(description="Whether high-risk commands are blocked by policy.")
    timeout_seconds: int = Field(description="Configured default execution timeout in seconds.")
    max_timeout_seconds: int = Field(description="Configured maximum allowable execution timeout.")
    max_output_chars: int = Field(description="Configured maximum captured output characters.")
    history_count: int = Field(
        description="Number of command execution records in session history."
    )
    history_limit: int = Field(description="Maximum bounded capacity of session history.")
    pending_approval_count: int = Field(
        description="Number of currently active pending approval tokens."
    )
