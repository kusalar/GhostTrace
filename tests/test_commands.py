"""Tests for the GhostTrace command parser, registry, and built-in commands."""

from ghosttrace.config.settings import Settings
from ghosttrace.terminal.command_parser import parse_command_line
from ghosttrace.terminal.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
)
from ghosttrace.terminal.commands import create_default_registry
from ghosttrace.terminal.history import SessionHistory
from rich.table import Table


def test_command_parser_basic_and_args() -> None:
    """Verify command parser tokenizes commands, arguments, and handles case."""
    parsed = parse_command_line("HELP")
    assert parsed is not None
    assert parsed.name == "help"
    assert parsed.args == []

    parsed_args = parse_command_line("help status about")
    assert parsed_args is not None
    assert parsed_args.name == "help"
    assert parsed_args.args == ["status", "about"]


def test_command_parser_quotes_and_fallback() -> None:
    """Verify quoted arguments parsing and graceful fallback on unmatched quotes."""
    parsed_quotes = parse_command_line('search "hello world"')
    assert parsed_quotes is not None
    assert parsed_quotes.args == ["hello world"]

    # Unmatched quote fallback
    parsed_unmatched = parse_command_line('search "broken quote')
    assert parsed_unmatched is not None
    assert parsed_unmatched.name == "search"
    assert len(parsed_unmatched.args) >= 1


def test_command_parser_empty_inputs() -> None:
    """Empty and whitespace strings return None."""
    assert parse_command_line("") is None
    assert parse_command_line("   ") is None
    assert parse_command_line("\t\n") is None


def test_registry_registration_and_aliases() -> None:
    """Verify registry registers primary names and aliases correctly."""
    registry = CommandRegistry()
    cmd = Command(
        name="testcmd",
        description="A test command",
        usage="testcmd",
        aliases=["t", "tc"],
        handler=lambda _args, _ctx: CommandResult(success=True, output="ok"),
    )
    registry.register(cmd)

    assert registry.get("testcmd") == cmd
    assert registry.get("TESTCMD") == cmd
    assert registry.get("t") == cmd
    assert registry.get("tc") == cmd
    assert registry.get("unknown") is None


def test_registry_execute_unknown_and_empty() -> None:
    """Verify registry execution for unknown commands and blank input."""
    registry = CommandRegistry()
    ctx = CommandContext(settings=Settings(), history=SessionHistory())

    # Blank execution
    empty_res = registry.execute("   ", ctx)
    assert empty_res.success is True
    assert empty_res.output == ""

    # Unknown command
    unknown_res = registry.execute("forbidden_spell", ctx)
    assert unknown_res.success is False
    assert "Unknown command: 'forbidden_spell'" in str(unknown_res.output)
    assert "help" in str(unknown_res.output)


def test_registry_handles_command_handler_exceptions() -> None:
    """Exceptions raised in command handlers must be caught and returned as errors."""
    registry = CommandRegistry()

    def buggy_handler(_args: list[str], _ctx: CommandContext) -> CommandResult:
        msg = "Simulated crash in handler"
        raise RuntimeError(msg)

    registry.register(Command(name="buggy", description="fails", handler=buggy_handler))
    ctx = CommandContext(settings=Settings(), history=SessionHistory())

    res = registry.execute("buggy", ctx)
    assert res.success is False
    assert "Error executing command 'buggy'" in str(res.output)
    assert "Simulated crash in handler" in str(res.output)


def test_builtin_commands() -> None:
    """Verify all built-in commands behave as specified."""
    registry = create_default_registry()
    history = SessionHistory()
    ctx = CommandContext(settings=Settings(), history=history)

    # 1. help
    help_res = registry.execute("help", ctx)
    assert help_res.success is True
    assert isinstance(help_res.output, Table)

    help_specific = registry.execute("help status", ctx)
    assert help_specific.success is True
    assert "Usage: status" in str(help_specific.output)

    help_alias = registry.execute("help exit", ctx)
    assert help_alias.success is True
    assert "Aliases:" in str(help_alias.output)

    help_invalid = registry.execute("help nonexistent", ctx)
    assert help_invalid.success is False

    # 2. about
    about_res = registry.execute("about", ctx)
    assert about_res.success is True
    assert "GHOSTTRACE v0.4.0" in str(about_res.output)
    assert "Developer Assistant" in str(about_res.output)

    # 3. status
    status_res = registry.execute("status", ctx)
    assert status_res.success is True
    assert "Foundation (Step 01)" in str(status_res.output)
    assert "Terminal UI & CLI (Step 02)" in str(status_res.output)
    assert "Local AI Engine (Step 03)" in str(status_res.output)
    assert "Ghost Persona (Step 04)" in str(status_res.output)

    # 4. version
    version_res = registry.execute("version", ctx)
    assert version_res.success is True
    assert "GhostTrace v0.4.0" in str(version_res.output)

    # 5. clear
    clear_res = registry.execute("clear", ctx)
    assert clear_res.success is True
    assert clear_res.should_clear is True

    # 6. ghost
    ghost_res = registry.execute("ghost", ctx)
    assert ghost_res.success is True
    assert "GHOSTTRACE ENTITY" in str(ghost_res.output)

    # 7. ai
    ai_res = registry.execute("ai", ctx)
    assert ai_res.success is True
    assert "AI ENGINE STATUS" in str(ai_res.output)

    # 8. history
    history_res = registry.execute("history", ctx)
    assert history_res.success is True
    # Previous commands should have been recorded into history
    assert "CURRENT SESSION HISTORY:" in str(history_res.output)

    # 9. exit / quit
    exit_res = registry.execute("exit", ctx)
    assert exit_res.success is True
    assert exit_res.should_exit is True
    assert "The machine remembers." in str(exit_res.output)

    quit_res = registry.execute("quit", ctx)
    assert quit_res.success is True
    assert quit_res.should_exit is True


def test_builtin_history_empty_message() -> None:
    """When history is empty, history command outputs appropriate message."""
    registry = create_default_registry()
    empty_history = SessionHistory()
    ctx = CommandContext(settings=Settings(), history=empty_history)

    # 'history' command itself is not added to history
    res = registry.execute("history", ctx)
    assert res.success is True
    assert "No commands recorded in this session yet." in str(res.output)


def test_ai_subcommands_handling() -> None:
    """Verify ai subcommands (status, info, unload, clear, unknown) execute properly."""
    registry = create_default_registry()
    ctx = CommandContext(settings=Settings(), history=SessionHistory())

    # 1. ai status
    status_res = registry.execute("ai status", ctx)
    assert status_res.success is True
    assert "AI ENGINE STATUS" in str(status_res.output)
    assert "Runtime (llama.cpp)" in str(status_res.output)

    # 2. ai info
    info_res = registry.execute("ai info", ctx)
    assert info_res.success is True
    assert "LOCAL AI CONFIGURATION" in str(info_res.output)
    assert "Qwen2.5-1.5B-Instruct" in str(info_res.output)

    # 3. ai unload (when not loaded)
    unload_res = registry.execute("ai unload", ctx)
    assert unload_res.success is True
    assert "Model was not loaded" in str(unload_res.output)

    # 4. ai clear
    clear_res = registry.execute("ai clear", ctx)
    assert clear_res.success is True
    assert "cleared" in str(clear_res.output)

    # 5. ai unknown
    unknown_res = registry.execute("ai invalid_action", ctx)
    assert unknown_res.success is False
    assert "Unknown AI subcommand 'invalid_action'" in str(unknown_res.output)


def test_registry_ai_fallback_execution() -> None:
    """Verify registry delegates natural language to ai_engine when present in context."""
    from unittest.mock import MagicMock

    registry = create_default_registry()
    mock_engine = MagicMock()
    mock_engine.ask.return_value = MagicMock(text="Mocked explanation of Python decorators.")

    ctx = CommandContext(
        settings=Settings(),
        history=SessionHistory(),
        ai_engine=mock_engine,
    )

    res = registry.execute("Explain python decorators", ctx)
    assert res.success is True
    assert "Mocked explanation of Python decorators" in str(res.output)
    mock_engine.ask.assert_called_once_with("Explain python decorators")
