"""Command registration and dispatch architecture for GhostTrace."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from rich.console import RenderableType

from ghosttrace.config.settings import Settings
from ghosttrace.terminal.command_parser import parse_command_line
from ghosttrace.terminal.history import SessionHistory

logger = logging.getLogger("ghosttrace.terminal.commands")


@dataclass
class CommandContext:
    """Runtime context passed to command execution handlers."""

    settings: Settings
    history: SessionHistory


@dataclass
class CommandResult:
    """Result returned by a command execution handler."""

    success: bool
    output: str | RenderableType
    should_exit: bool = False
    should_clear: bool = False
    command_name: str = ""


@dataclass
class Command:
    """Specification of an interactive GhostTrace command."""

    name: str
    description: str
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    handler: Callable[[list[str], CommandContext], CommandResult] = field(
        default=lambda _args, _ctx: CommandResult(success=True, output="")
    )


class CommandRegistry:
    """Registry managing available commands, alias resolution, and execution routing."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._alias_map: dict[str, str] = {}

    def register(self, command: Command) -> None:
        """Register a command and its aliases."""
        primary_name = command.name.lower()
        self._commands[primary_name] = command

        for alias in command.aliases:
            self._alias_map[alias.lower()] = primary_name

    def get(self, name: str) -> Command | None:
        """Look up a command by its primary name or alias."""
        clean_name = name.strip().lower()
        if clean_name in self._commands:
            return self._commands[clean_name]

        target_name = self._alias_map.get(clean_name)
        if target_name and target_name in self._commands:
            return self._commands[target_name]

        return None

    def list_commands(self) -> list[Command]:
        """Return a sorted list of all unique registered primary commands."""
        return sorted(self._commands.values(), key=lambda c: c.name)

    def execute(self, line: str, context: CommandContext) -> CommandResult:
        """Parse input, route to appropriate handler, and return CommandResult."""
        parsed = parse_command_line(line)
        if parsed is None:
            return CommandResult(success=True, output="")

        # Record to history (SessionHistory automatically filters out empty & 'history')
        context.history.add(parsed.raw)

        command = self.get(parsed.name)
        if command is None:
            return CommandResult(
                success=False,
                output=f"Unknown command: '{parsed.name}'. Type 'help' to see available commands.",
                command_name=parsed.name,
            )

        try:
            result = command.handler(parsed.args, context)
            result.command_name = command.name
            return result
        except Exception as exc:
            logger.exception("Error executing command '%s' with args %s", command.name, parsed.args)
            return CommandResult(
                success=False,
                output=f"Error executing command '{command.name}': {exc}",
                command_name=command.name,
            )
