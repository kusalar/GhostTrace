"""Command line parsing utilities for GhostTrace terminal input."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedCommand:
    """Represents a validated, parsed command with arguments."""

    raw: str
    name: str
    args: list[str] = field(default_factory=list)


def parse_command_line(line: str) -> ParsedCommand | None:
    """Parse a raw terminal input string into a structured ParsedCommand.

    Returns None if the input is empty or contains only whitespace.
    Handles shell-like quoted arguments cleanly.
    """
    stripped = line.strip()
    if not stripped:
        return None

    try:
        tokens = shlex.split(stripped)
    except ValueError:
        # Fallback to standard whitespace splitting if quotation is unbalanced
        tokens = stripped.split()

    if not tokens:
        return None

    cmd_name = tokens[0].lower()
    cmd_args = tokens[1:]

    return ParsedCommand(raw=stripped, name=cmd_name, args=cmd_args)
