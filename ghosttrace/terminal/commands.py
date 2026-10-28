"""Built-in command implementations and default registry factory for GhostTrace."""

from __future__ import annotations

from rich.table import Table

from ghosttrace.terminal.command_registry import (
    Command,
    CommandContext,
    CommandRegistry,
    CommandResult,
)


def handle_help(args: list[str], context: CommandContext) -> CommandResult:
    """Display available commands or details about a specific command."""
    registry = create_default_registry()

    if args:
        target = args[0].lower()
        cmd = registry.get(target)
        if cmd:
            usage = f"Usage: {cmd.usage}" if cmd.usage else f"Usage: {cmd.name}"
            aliases = f"Aliases: {', '.join(cmd.aliases)}" if cmd.aliases else ""
            details = [f"COMMAND: {cmd.name}", cmd.description, usage]
            if aliases:
                details.append(aliases)
            return CommandResult(success=True, output="\n".join(details))
        return CommandResult(
            success=False,
            output=f"Unknown command '{target}' in help request. Type 'help' to see all commands.",
        )

    table = Table(title="AVAILABLE COMMANDS", border_style="dim green", show_header=True)
    table.add_column("Command", style="bold #00ff66", no_wrap=True)
    table.add_column("Description", style="#99aa99")

    for cmd in registry.list_commands():
        alias_note = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
        table.add_row(f"{cmd.name}{alias_note}", cmd.description)

    return CommandResult(success=True, output=table)


def handle_about(args: list[str], context: CommandContext) -> CommandResult:
    """Display project identity, architecture, and technology stack."""
    lines = [
        f"GHOSTTRACE v{context.settings.app_version}",
        f'"{context.settings.app_description}"',
        "",
        "IDENTITY TRINITY:",
        "  1. Developer Assistant — Local programming, command, and debugging assistance.",
        "  2. Digital Ghost       — Atmospheric terminal presence with contextual behavior.",
        "  3. Terminal Guardian   — Command analysis and protection against destructive actions.",
        "",
        "SPECIFICATIONS:",
        "  • Architecture : Fully offline-first, local CPU inference",
        "  • Platform     : Windows 10/11 64-bit native",
        "  • Target Spec  : Intel Core i3-1115G4, 12 GB RAM, Intel UHD graphics",
        "  • Status       : Step 03 / 10 — Local AI Integration",
    ]
    return CommandResult(success=True, output="\n".join(lines))


def handle_status(args: list[str], context: CommandContext) -> CommandResult:
    """Display current system status distinguishing implemented from planned features."""
    ai_engine = context.ai_engine
    if ai_engine is None:
        from ghosttrace.ai.engine import AIEngine

        ai_engine = AIEngine(context.settings)

    ai_status = ai_engine.get_status()
    if not ai_status.runtime_available:
        ai_step_str = "[!] RUNTIME MISSING"
    elif ai_status.is_loaded:
        ai_step_str = "[OK] LOADED (READY)"
    elif ai_status.model_exists:
        ai_step_str = "[OK] READY (UNLOADED)"
    else:
        ai_step_str = "[!] STANDBY (NO WEIGHTS)"

    lines = [
        "APPLICATION SUBSYSTEM STATUS",
        "==================================================",
        f"  App Version       : v{context.settings.app_version}",
        f"  Environment       : {context.settings.env}",
        f"  Debug Mode        : {context.settings.debug}",
        f"  Log Level         : {context.settings.log_level}",
        f"  Session Commands  : {context.history.count}",
        "--------------------------------------------------",
        "  Foundation (Step 01)        : [OK] IMPLEMENTED",
        "  Terminal UI & CLI (Step 02) : [OK] ACTIVE",
        f"  Local AI Engine (Step 03)   : {ai_step_str}",
        "  Ghost Persona (Step 04)     : [..] NOT IMPLEMENTED",
        "  Developer Intel (Step 05)   : [..] NOT IMPLEMENTED",
        "  Command Guardian (Step 06)  : [..] NOT IMPLEMENTED",
        "  Persistent Memory (Step 07) : [..] NOT IMPLEMENTED",
        "  System Diagnostics (Step 08): [..] NOT IMPLEMENTED",
        "==================================================",
    ]
    return CommandResult(success=True, output="\n".join(lines))


def handle_version(args: list[str], context: CommandContext) -> CommandResult:
    """Display the application version."""
    return CommandResult(
        success=True,
        output=f"GhostTrace v{context.settings.app_version}",
    )


def handle_clear(args: list[str], context: CommandContext) -> CommandResult:
    """Clear the interactive conversation log."""
    return CommandResult(
        success=True,
        output="Conversation cleared.",
        should_clear=True,
    )


def handle_history(args: list[str], context: CommandContext) -> CommandResult:
    """Display session command history."""
    entries = context.history.get_history()
    if not entries:
        return CommandResult(
            success=True,
            output="No commands recorded in this session yet.",
        )

    lines = ["CURRENT SESSION HISTORY:"]
    for idx, entry in enumerate(entries, start=1):
        lines.append(f"  {idx:2d}. {entry}")

    return CommandResult(success=True, output="\n".join(lines))


def handle_exit(args: list[str], context: CommandContext) -> CommandResult:
    """Gracefully terminate the GhostTrace session."""
    return CommandResult(
        success=True,
        output="The machine remembers.\nGhostTrace session terminated.",
        should_exit=True,
    )


def handle_ghost(args: list[str], context: CommandContext) -> CommandResult:
    """Display ghost personality subsystem status."""
    msg = (
        "PERSONALITY ENGINE: NOT IMPLEMENTED\n"
        "Personality engine and atmospheric behavior are scheduled for Step 04."
    )
    return CommandResult(success=True, output=msg)


def handle_ai(args: list[str], context: CommandContext) -> CommandResult:
    """Display and manage the local AI inference subsystem."""
    ai_engine = context.ai_engine
    if ai_engine is None:
        from ghosttrace.ai.engine import AIEngine

        ai_engine = AIEngine(context.settings)

    subcommand = args[0].lower() if args else "status"

    if subcommand == "status":
        status = ai_engine.get_status()
        runtime_badge = (
            f"[OK] INSTALLED (v{status.runtime_version})"
            if status.runtime_available
            else "[X] NOT INSTALLED"
        )
        model_exists_badge = "FOUND" if status.model_exists else "NOT FOUND"
        loaded_badge = "LOADED (in RAM)" if status.is_loaded else "UNLOADED (standby)"
        busy_badge = "GENERATING" if status.is_busy else "IDLE"

        lines = [
            "AI ENGINE STATUS",
            "==================================================",
            f"  Runtime (llama.cpp) : {runtime_badge}",
            f"  Model Status        : {status.model_status.value}",
            f"  Model Path          : {status.model_path}",
            f"  Model Weights       : {model_exists_badge}",
            f"  Memory State        : {loaded_badge}",
            f"  Engine State        : {busy_badge}",
            f"  Session Exchanges   : {status.history_count}",
            "--------------------------------------------------",
            f"  Context Window      : {status.context_size} tokens",
            f"  Max Output Tokens   : {status.max_tokens} tokens",
            f"  CPU Threads         : {status.threads}",
            f"  GPU Offload Layers  : {status.gpu_layers} (CPU-only)",
            "==================================================",
        ]
        if not status.runtime_available:
            lines.append("\nTo install the runtime:\n  pip install llama-cpp-python")
        elif not status.model_exists:
            lines.append(
                f"\nTo configure model weights:\n"
                f"  Place Qwen2.5-1.5B-Instruct GGUF at:\n  {status.model_path}\n"
                f"  or configure GHOSTTRACE_MODEL_PATH."
            )
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "load":
        try:
            ai_engine.load_model()
            meta = ai_engine.model_manager.get_metadata()
            msg = (
                f"Model loaded successfully: {meta.model_path.name}\n"
                f"Size: {meta.file_size_mb} MB | Context: {context.settings.ai_context_size} | "
                f"Threads: {context.settings.ai_threads}"
            )
            return CommandResult(success=True, output=msg)
        except Exception as exc:
            return CommandResult(success=False, output=f"Failed to load model:\n{exc}")

    if subcommand == "unload":
        unloaded = ai_engine.unload_model()
        if unloaded:
            return CommandResult(
                success=True, output="Model unloaded from memory. System resources released."
            )
        return CommandResult(success=True, output="Model was not loaded in memory.")

    if subcommand == "info":
        lines = [
            "LOCAL AI CONFIGURATION & HARDWARE PARAMETERS",
            "==================================================",
            "  Target Architecture : Qwen2.5-1.5B-Instruct",
            "  Format & Precision  : GGUF (Q4_K_M)",
            f"  Model Path          : {ai_engine.model_manager.model_path}",
            f"  AI Inference Active : {context.settings.ai_enabled}",
            f"  Context Window      : {context.settings.ai_context_size} tokens",
            f"  Max Output Tokens   : {context.settings.ai_max_tokens} tokens",
            f"  Temperature         : {context.settings.ai_temperature}",
            f"  Top-P Sampling      : {context.settings.ai_top_p}",
            f"  CPU Threads         : {context.settings.ai_threads}",
            f"  GPU Offload Layers  : {context.settings.ai_gpu_layers} (CPU-only)",
            f"  Batch Size          : {context.settings.ai_batch_size}",
            f"  History Limit       : {context.settings.ai_history_limit} exchanges",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "clear":
        ai_engine.clear_conversation()
        return CommandResult(success=True, output="AI conversation context buffer cleared.")

    return CommandResult(
        success=False,
        output=(
            f"Unknown AI subcommand '{subcommand}'. "
            "Available: ai status, ai load, ai unload, ai info, ai clear"
        ),
    )


def create_default_registry() -> CommandRegistry:
    """Create and populate a CommandRegistry with all standard GhostTrace commands."""
    registry = CommandRegistry()

    registry.register(
        Command(
            name="help",
            description="Display available commands and usage instructions.",
            usage="help [command]",
            aliases=["?"],
            handler=handle_help,
        )
    )
    registry.register(
        Command(
            name="about",
            description="Display project information, purpose, and technology details.",
            usage="about",
            aliases=["info"],
            handler=handle_about,
        )
    )
    registry.register(
        Command(
            name="status",
            description="Display current application and subsystem status.",
            usage="status",
            handler=handle_status,
        )
    )
    registry.register(
        Command(
            name="version",
            description="Display GhostTrace version.",
            usage="version",
            aliases=["v"],
            handler=handle_version,
        )
    )
    registry.register(
        Command(
            name="clear",
            description="Clear the conversation display.",
            usage="clear",
            aliases=["cls"],
            handler=handle_clear,
        )
    )
    registry.register(
        Command(
            name="history",
            description="Display commands entered during the current session.",
            usage="history",
            aliases=["hist"],
            handler=handle_history,
        )
    )
    registry.register(
        Command(
            name="ghost",
            description="Display ghost persona subsystem status.",
            usage="ghost",
            handler=handle_ghost,
        )
    )
    registry.register(
        Command(
            name="ai",
            description="Display and manage the local AI inference engine.",
            usage="ai [status|load|unload|info|clear]",
            handler=handle_ai,
        )
    )
    registry.register(
        Command(
            name="exit",
            description="Gracefully leave GhostTrace.",
            usage="exit",
            aliases=["quit", "q"],
            handler=handle_exit,
        )
    )

    return registry
