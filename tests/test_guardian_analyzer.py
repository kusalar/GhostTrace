"""Unit tests for CommandAnalyzer static parsing and path resolution."""

from __future__ import annotations

import sys
from pathlib import Path

from ghosttrace.guardian.analyzer import CommandAnalyzer
from ghosttrace.guardian.schemas import RiskLevel


def test_analyzer_empty_command() -> None:
    """Verify analyzer handles empty command strings gracefully."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze("   ")
    assert res.is_malformed is True
    assert res.is_permitted is False
    assert res.risk_level == RiskLevel.BLOCKED
    assert res.executable is None


def test_analyzer_safe_command_parsing() -> None:
    """Verify parsing and resolution of standard safe commands."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze("python --version")
    assert res.executable == "python"
    assert res.args == ["--version"]
    assert res.risk_level == RiskLevel.SAFE
    assert res.is_permitted is True
    assert res.contains_shell_operators is False
    assert res.resolved_executable_path is not None


def test_analyzer_quoted_arguments_preservation() -> None:
    """Verify quotes are cleanly stripped from arguments without mangling."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze('git commit -m "feat: user authentication"')
    assert res.executable == "git"
    assert res.args == ["commit", "-m", "feat: user authentication"]
    assert res.risk_level == RiskLevel.LOW
    assert res.is_permitted is True


def test_analyzer_windows_paths_and_backslashes() -> None:
    """Verify Windows backslashes are preserved in arguments."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze(r"python C:\Users\HP\Projects\script.py")
    assert res.executable == "python"
    assert res.args == [r"C:\Users\HP\Projects\script.py"]
    assert res.risk_level == RiskLevel.LOW
    assert res.is_permitted is True


def test_analyzer_quoted_executable() -> None:
    """Verify quoted executable names are parsed and resolved."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze(f'"{sys.executable}" --version')
    assert res.executable == sys.executable
    assert res.args == ["--version"]
    assert res.risk_level == RiskLevel.SAFE
    assert res.is_permitted is True
    assert res.resolved_executable_path == str(Path(sys.executable).resolve())


def test_analyzer_mixed_case_normalization() -> None:
    """Verify mixed-case commands are properly normalized and classified."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze("PyThOn --VeRsIoN")
    assert res.executable == "PyThOn"
    assert res.risk_level == RiskLevel.SAFE
    assert res.is_permitted is True


def test_analyzer_shell_chaining_operators_detected() -> None:
    """Verify unquoted shell operators trigger operator rejection and BLOCKED classification."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze("git status && dir")
    assert res.contains_shell_operators is True
    assert res.rejected_operators == ["&&"]
    assert res.risk_level == RiskLevel.BLOCKED
    assert res.is_permitted is False

    res2 = analyzer.analyze("pytest || echo failed")
    assert res2.contains_shell_operators is True
    assert res2.rejected_operators == ["||"]
    assert res2.risk_level == RiskLevel.BLOCKED

    res3 = analyzer.analyze("cat file.txt | grep error")
    assert res3.contains_shell_operators is True
    assert res3.rejected_operators == ["|"]
    assert res3.risk_level == RiskLevel.BLOCKED


def test_analyzer_quoted_operators_ignored() -> None:
    """Verify shell operators inside quoted strings are not treated as shell chaining."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze('git commit -m "foo & bar && baz | qux"')
    assert res.contains_shell_operators is False
    assert res.rejected_operators == []
    assert res.risk_level == RiskLevel.LOW


def test_analyzer_unbalanced_quotes_flagged_malformed() -> None:
    """Verify unbalanced quotation marks flag the command as malformed and BLOCKED."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze('git commit -m "unclosed string')
    assert res.is_malformed is True
    assert res.risk_level == RiskLevel.BLOCKED
    assert res.is_permitted is False


def test_analyzer_high_and_blocked_commands() -> None:
    """Verify high-risk and blocked commands are accurately flagged."""
    analyzer = CommandAnalyzer()

    # git reset --hard -> HIGH
    res_high = analyzer.analyze("git reset --hard HEAD~1")
    assert res_high.risk_level == RiskLevel.HIGH
    assert res_high.is_permitted is False
    assert res_high.safer_alternative is not None

    # format C: -> BLOCKED
    res_blocked = analyzer.analyze("format C:")
    assert res_blocked.risk_level == RiskLevel.BLOCKED
    assert res_blocked.is_permitted is False


def test_analyzer_unresolvable_executable() -> None:
    """Verify executables that do not exist on PATH have None resolved path."""
    analyzer = CommandAnalyzer()
    res = analyzer.analyze("nonexistent_binary_tool_xyz_999 --help")
    assert res.executable == "nonexistent_binary_tool_xyz_999"
    assert res.resolved_executable_path is None
    assert res.risk_level == RiskLevel.MEDIUM
