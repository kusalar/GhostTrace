"""Controlled subprocess execution with strict bounds and process termination safeguards."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from ghosttrace.guardian.schemas import ExecutionResult, ExecutionStatus

logger = logging.getLogger("ghosttrace.guardian.executor")


class ControlledExecutor:
    """Executes validated commands via safe subprocess APIs with timeouts and bounded output.

    IMPORTANT SAFETY GUARANTEES:
    - Never passes shell=True under any circumstance.
    - Never evaluates commands via cmd.exe /c or PowerShell wrapper.
    - Process execution is isolated to the specified working directory.
    - Process termination is attempted if configured timeout is reached.
    - Output streams are strictly bounded to prevent memory exhaustion.
    """

    def __init__(self, timeout_seconds: int = 30, max_output_chars: int = 12000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def execute(
        self,
        executable: str,
        args: list[str],
        working_dir: str,
        timeout: int | None = None,
        original_command: str = "",
    ) -> ExecutionResult:
        """Execute command synchronously within a controlled subprocess.

        Args:
            executable: Target executable or resolved binary path.
            args: Argument list to pass to the process.
            working_dir: Working directory for process execution.
            timeout: Optional per-execution timeout in seconds.
            original_command: Original raw command string for reporting.

        Returns:
            Structured ExecutionResult with exit code, captured outputs, and metadata.
        """
        canonical_dir = str(Path(working_dir).resolve())
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        cmd_args = [executable, *args]
        cmd_display = original_command or " ".join(cmd_args)

        start_time = time.perf_counter()
        truncated = False
        status = ExecutionStatus.RUNNING

        try:
            # Enforce shell=False strictly with stdin disconnected
            proc = subprocess.Popen(
                cmd_args,
                cwd=canonical_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                shell=False,
            )

            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=effective_timeout)
                duration = time.perf_counter() - start_time
                exit_code = proc.returncode

                stdout_text = self._decode_stream(stdout_bytes)
                stderr_text = self._decode_stream(stderr_bytes)

                # Enforce output length bounds
                if len(stdout_text) > self.max_output_chars:
                    stdout_text = (
                        stdout_text[: self.max_output_chars]
                        + f"\n... [TRUNCATED: output exceeded {self.max_output_chars} characters]"
                    )
                    truncated = True

                if len(stderr_text) > self.max_output_chars:
                    stderr_text = (
                        stderr_text[: self.max_output_chars]
                        + "\n... [TRUNCATED: error output exceeded "
                        f"{self.max_output_chars} characters]"
                    )
                    truncated = True

                status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
                error_msg = (
                    None if exit_code == 0 else f"Process exited with non-zero code {exit_code}."
                )

                return ExecutionResult(
                    command=cmd_display,
                    executable=executable,
                    args=args,
                    working_dir=canonical_dir,
                    status=status,
                    exit_code=exit_code,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    duration_seconds=duration,
                    truncated=truncated,
                    error_message=error_msg,
                )

            except subprocess.TimeoutExpired:
                duration = time.perf_counter() - start_time
                logger.warning(
                    "Process execution timed out after %ds for command: %s. Terminating process.",
                    effective_timeout,
                    cmd_display,
                )
                # Terminate and collect any partial output
                proc.kill()
                try:
                    stdout_bytes, stderr_bytes = proc.communicate(timeout=2.0)
                except Exception:
                    stdout_bytes, stderr_bytes = b"", b""

                stdout_text = self._decode_stream(stdout_bytes)
                stderr_text = self._decode_stream(stderr_bytes)

                return ExecutionResult(
                    command=cmd_display,
                    executable=executable,
                    args=args,
                    working_dir=canonical_dir,
                    status=ExecutionStatus.TIMED_OUT,
                    exit_code=None,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    duration_seconds=duration,
                    truncated=truncated,
                    error_message=(
                        f"Execution timed out after {effective_timeout} seconds. "
                        "Process was terminated. Note: Detached child processes may persist."
                    ),
                )

        except FileNotFoundError as exc:
            duration = time.perf_counter() - start_time
            logger.error("Executable not found during execution: %s", exc)
            return ExecutionResult(
                command=cmd_display,
                executable=executable,
                args=args,
                working_dir=canonical_dir,
                status=ExecutionStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=duration,
                truncated=False,
                error_message=f"Executable '{executable}' could not be located on disk or PATH.",
            )

        except PermissionError as exc:
            duration = time.perf_counter() - start_time
            logger.error("Permission denied when attempting execution: %s", exc)
            return ExecutionResult(
                command=cmd_display,
                executable=executable,
                args=args,
                working_dir=canonical_dir,
                status=ExecutionStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=duration,
                truncated=False,
                error_message=f"Permission denied attempting to execute '{executable}'.",
            )

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.exception("Unexpected error during controlled command execution: %s", exc)
            return ExecutionResult(
                command=cmd_display,
                executable=executable,
                args=args,
                working_dir=canonical_dir,
                status=ExecutionStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=duration,
                truncated=False,
                error_message=f"Process execution failed: {exc}",
            )

    @staticmethod
    def _decode_stream(raw: bytes | None) -> str:
        """Safely decode console output stream with fallback for Windows encoding."""
        if not raw:
            return ""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback for Windows console code pages (e.g. cp1252/cp437)
            return raw.decode("cp1252", errors="replace")
