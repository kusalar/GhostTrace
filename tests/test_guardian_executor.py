"""Unit tests for ControlledExecutor subprocess execution and safeguards."""

from __future__ import annotations

import sys

from ghosttrace.guardian.executor import ControlledExecutor
from ghosttrace.guardian.schemas import ExecutionStatus


def test_executor_successful_execution(tmp_path) -> None:
    """Verify controlled execution of a harmless python command."""
    executor = ControlledExecutor(timeout_seconds=10, max_output_chars=1000)
    res = executor.execute(
        executable=sys.executable,
        args=["-c", "print('hello harmless execution')"],
        working_dir=str(tmp_path),
    )
    assert res.status == ExecutionStatus.SUCCESS
    assert res.exit_code == 0
    assert "hello harmless execution" in res.stdout
    assert res.stderr == ""
    assert res.truncated is False
    assert res.duration_seconds > 0.0


def test_executor_nonzero_exit_code(tmp_path) -> None:
    """Verify capturing non-zero process exit codes."""
    executor = ControlledExecutor(timeout_seconds=10, max_output_chars=1000)
    res = executor.execute(
        executable=sys.executable,
        args=["-c", "import sys; sys.stderr.write('error occurred'); sys.exit(42)"],
        working_dir=str(tmp_path),
    )
    assert res.status == ExecutionStatus.FAILED
    assert res.exit_code == 42
    assert "error occurred" in res.stderr
    assert "42" in (res.error_message or "")


def test_executor_timeout_termination(tmp_path) -> None:
    """Verify process termination when execution timeout is exceeded."""
    executor = ControlledExecutor(timeout_seconds=30, max_output_chars=1000)
    # Sleep 3 seconds with 0.1s timeout
    res = executor.execute(
        executable=sys.executable,
        args=["-c", "import time; time.sleep(3.0)"],
        working_dir=str(tmp_path),
        timeout=0.2,
    )
    assert res.status == ExecutionStatus.TIMED_OUT
    assert res.exit_code is None
    assert "timed out after 0.2" in (res.error_message or "")


def test_executor_output_truncation(tmp_path) -> None:
    """Verify stdout and stderr truncation when exceeding max_output_chars."""
    executor = ControlledExecutor(timeout_seconds=10, max_output_chars=50)
    res = executor.execute(
        executable=sys.executable,
        args=["-c", "print('A' * 300)"],
        working_dir=str(tmp_path),
    )
    assert res.status == ExecutionStatus.SUCCESS
    assert res.truncated is True
    assert "[TRUNCATED:" in res.stdout
    assert len(res.stdout) < 300

    # Stderr truncation
    res_err = executor.execute(
        executable=sys.executable,
        args=["-c", "import sys; sys.stderr.write('E' * 300)"],
        working_dir=str(tmp_path),
    )
    assert res_err.truncated is True
    assert "[TRUNCATED:" in res_err.stderr


def test_executor_permission_error_and_unexpected(tmp_path) -> None:
    """Verify handling of PermissionError and unexpected errors in executor."""
    from unittest.mock import patch

    executor = ControlledExecutor()

    # PermissionError
    with patch("subprocess.Popen", side_effect=PermissionError("Permission denied")):
        res = executor.execute(
            executable=sys.executable,
            args=["--version"],
            working_dir=str(tmp_path),
        )
        assert res.status == ExecutionStatus.FAILED
        assert "Permission denied" in (res.error_message or "")

    # Unexpected RuntimeError
    with patch("subprocess.Popen", side_effect=RuntimeError("Subprocess failure")):
        res = executor.execute(
            executable=sys.executable,
            args=["--version"],
            working_dir=str(tmp_path),
        )
        assert res.status == ExecutionStatus.FAILED
        assert "Subprocess failure" in (res.error_message or "")


def test_executor_nonexistent_executable(tmp_path) -> None:
    """Verify safe error handling when target executable does not exist."""
    executor = ControlledExecutor()
    res = executor.execute(
        executable="totally_fake_binary_never_exists_xyz",
        args=["--version"],
        working_dir=str(tmp_path),
    )
    assert res.status == ExecutionStatus.FAILED
    assert res.exit_code is None
    assert "could not be located" in (res.error_message or "")


def test_executor_decode_stream_fallback() -> None:
    """Verify safe stream decoding handles non-utf8 bytes via fallback."""
    raw_cp1252 = "Hällö Wörld".encode("cp1252")
    decoded = ControlledExecutor._decode_stream(raw_cp1252)
    assert len(decoded) > 0
    assert ControlledExecutor._decode_stream(None) == ""
