"""Terminal subsystem package for user interface and interactive sessions."""

from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.command_parser import ParsedCommand, parse_command_line
from ghosttrace.terminal.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
)
from ghosttrace.terminal.commands import create_default_registry
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.interface import render_cli_status, run_terminal_app

__all__ = [
    "Command",
    "CommandContext",
    "CommandRegistry",
    "CommandResult",
    "GhostTraceApp",
    "ParsedCommand",
    "SessionHistory",
    "create_default_registry",
    "parse_command_line",
    "render_cli_status",
    "run_terminal_app",
]
