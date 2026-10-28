"""Command parser and static analysis subsystem for GhostTrace Command Guardian."""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path

from ghosttrace.guardian.patterns import (
    find_unquoted_shell_operators,
    match_dangerous_patterns,
    normalize_command_for_matching,
)
from ghosttrace.guardian.risk import classify_command_risk
from ghosttrace.guardian.schemas import CommandAnalysis


class CommandAnalyzer:
    """Performs static parsing, pattern scanning, and risk assessment on terminal commands."""

    def analyze(self, raw_command: str, cwd: str | None = None) -> CommandAnalysis:
        """Parse and statically analyze a command string without executing it.

        Args:
            raw_command: Raw command text entered by user.
            cwd: Optional working directory for executable path resolution.

        Returns:
            Fully populated CommandAnalysis object.
        """
        trimmed = raw_command.strip()
        normalized = normalize_command_for_matching(trimmed)

        if not trimmed:
            return CommandAnalysis(
                original_command=raw_command,
                normalized_command="",
                executable=None,
                resolved_executable_path=None,
                args=[],
                risk_level=classify_command_risk(None, [], [], [], is_malformed=True)[0],
                risk_reasons=["Empty command string."],
                side_effects=["None"],
                is_permitted=False,
                requires_approval=True,
                is_malformed=True,
            )

        # 1. Identify unquoted shell chaining or redirection operators
        unquoted_ops = find_unquoted_shell_operators(trimmed)
        has_shell_ops = len(unquoted_ops) > 0

        # 2. Tokenize command into executable and arguments using Windows-aware quoting
        is_malformed = False
        tokens: list[str] = []
        try:
            raw_tokens = shlex.split(trimmed, posix=False)
            # Strip outer enclosing quotes while preserving internal backslashes and paths
            for tok in raw_tokens:
                clean_tok = tok
                if (clean_tok.startswith('"') and clean_tok.endswith('"')) or (
                    clean_tok.startswith("'") and clean_tok.endswith("'")
                ):
                    clean_tok = clean_tok[1:-1]
                tokens.append(clean_tok)
        except ValueError:
            is_malformed = True
            tokens = trimmed.split()

        executable = tokens[0] if tokens else None
        args = tokens[1:] if len(tokens) > 1 else []

        # 3. Resolve executable path on disk or environment PATH
        resolved_path: str | None = None
        if executable and not is_malformed:
            resolved_path = self._resolve_executable_path(executable, cwd=cwd)

        # 4. Evaluate dangerous and suspicious pattern heuristics
        matched_rules = match_dangerous_patterns(trimmed)

        # 5. Classify risk level and operational policy
        risk_level, reasons, side_effects, safer_alt, is_permitted = classify_command_risk(
            executable=executable,
            args=args,
            matched_rules=matched_rules,
            unquoted_operators=unquoted_ops,
            is_malformed=is_malformed,
        )

        return CommandAnalysis(
            original_command=raw_command,
            normalized_command=normalized,
            executable=executable,
            resolved_executable_path=resolved_path,
            args=args,
            risk_level=risk_level,
            risk_reasons=reasons,
            side_effects=side_effects,
            is_permitted=is_permitted,
            requires_approval=True,
            safer_alternative=safer_alt,
            contains_shell_operators=has_shell_ops,
            rejected_operators=unquoted_ops,
            is_malformed=is_malformed,
        )

    def _resolve_executable_path(self, executable: str, cwd: str | None = None) -> str | None:
        """Resolve executable name to an existing binary path on disk or within system PATH."""
        # 1. Check relative or absolute file path
        candidate_path = Path(executable)
        if cwd and not candidate_path.is_absolute():
            candidate_path = Path(cwd) / executable

        if candidate_path.is_file():
            return str(candidate_path.resolve())

        # 2. Check system PATH using shutil.which
        # On Windows, shutil.which checks PATHEXT (.COM, .EXE, .BAT, .CMD)
        path_env = os.environ.get("PATH")
        if cwd:
            path_env = f"{cwd}{os.pathsep}{path_env}" if path_env else cwd

        resolved = shutil.which(executable, path=path_env)
        if resolved:
            return str(Path(resolved).resolve())

        return None
