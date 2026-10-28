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
        "  • Status       : Step 04 / 10 — Ghost Personality & Behaviour Engine",
    ]
    return CommandResult(success=True, output="\n".join(lines))


def handle_status(args: list[str], context: CommandContext) -> CommandResult:
    """Display current system status distinguishing implemented from planned features."""
    ai_engine = context.ai_engine
    if ai_engine is None:
        from ghosttrace.ai.engine import AIEngine

        ai_engine = AIEngine(context.settings)

    ghost_engine = context.ghost_engine
    if ghost_engine is None:
        ghost_engine = ai_engine.ghost_engine

    ai_status = ai_engine.get_status()
    if not ai_status.runtime_available:
        ai_step_str = "[!] RUNTIME MISSING"
    elif ai_status.is_loaded:
        ai_step_str = "[OK] LOADED (READY)"
    elif ai_status.model_exists:
        ai_step_str = "[OK] READY (UNLOADED)"
    else:
        ai_step_str = "[!] STANDBY (NO WEIGHTS)"

    ghost_status_str = (
        f"[OK] ACTIVE ({ghost_engine.active_profile.name})"
        if ghost_engine.is_enabled
        else "[!] DISABLED"
    )

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
        f"  Ghost Persona (Step 04)     : {ghost_status_str}",
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
    """Display and manage ghost personality profiles, traits, and mood."""
    ghost_engine = context.ghost_engine
    if ghost_engine is None:
        if context.ai_engine and context.ai_engine.ghost_engine:
            ghost_engine = context.ai_engine.ghost_engine
        else:
            from ghosttrace.ghost.engine import GhostEngine

            ghost_engine = GhostEngine(context.settings)

    if not args:
        profile = ghost_engine.active_profile
        greeting = ghost_engine.get_greeting()
        state_badge = "ACTIVE" if ghost_engine.is_enabled else "DISABLED"
        mood_val = ghost_engine.current_mood.value.upper()
        lines = [
            f"GHOSTTRACE ENTITY: [bold #00ff66]{profile.name}[/]",
            f"Tagline: {profile.tagline}",
            f"Mood: [bold #33ff33]{mood_val}[/] | Engine: [bold]{state_badge}[/]",
            "",
            f'"{greeting}"',
            "",
            "Type 'ghost status' for details, 'ghost profiles' to list identities, "
            "or 'ghost set <profile>' to switch.",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    subcommand = args[0].lower()

    if subcommand == "status":
        status = ghost_engine.get_status()
        state_badge = "ENABLED" if status.is_enabled else "DISABLED"
        lines = [
            "GHOST PERSONALITY SUBSYSTEM STATUS",
            "==================================================",
            f"  Active Profile    : {status.profile_name} ({status.profile_id.value})",
            f"  Personality Layer : {state_badge}",
            f"  Session Mood      : {status.mood.value.upper()}",
            f"  Mood Rationale    : {ghost_engine.mood_tracker.last_reason}",
            f"  Mood Tracking     : {'ENABLED' if status.mood_enabled else 'DISABLED'}",
            f"  Tagline           : {status.tagline}",
            f"  Description       : {status.description}",
            "--------------------------------------------------",
            "TRAIT CONFIGURATION (0.0 - 1.0):",
        ]
        lines.extend(ghost_engine.traits.format_summary())
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "profiles":
        lines = [
            "AVAILABLE GHOST PERSONALITY PROFILES",
            "==================================================",
        ]
        active_id = ghost_engine.active_profile.id
        for p in ghost_engine.list_available_profiles():
            active_marker = " * [ACTIVE]" if p.id == active_id else ""
            lines.extend(
                [
                    f"• {p.name} [{p.id.value}]{active_marker}",
                    f"  Tagline : {p.tagline}",
                    f"  Style   : {p.speaking_style}",
                    "",
                ]
            )
        lines.append("Switch identity with: ghost set <profile_id>")
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "set":
        if len(args) < 2:
            return CommandResult(
                success=False,
                output=(
                    "Usage: ghost set <profile>\n"
                    "Available profiles: forgotten-machine, phantom-coder, guardian-spirit"
                ),
            )
        target = args[1].lower()
        try:
            new_profile = ghost_engine.set_profile(target)
            greeting = new_profile.get_greeting()
            lines = [
                f"Active personality switched to: [bold #00ff66]{new_profile.name}[/]",
                f'"{greeting}"',
                "Next AI responses will embody this identity.",
            ]
            return CommandResult(success=True, output="\n".join(lines))
        except ValueError as exc:
            return CommandResult(success=False, output=str(exc))

    if subcommand == "traits":
        lines = [
            f"PERSONALITY TRAITS: {ghost_engine.active_profile.name}",
            "==================================================",
        ]
        lines.extend(ghost_engine.traits.format_summary())
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "reset":
        reset_prof = ghost_engine.reset_profile()
        return CommandResult(
            success=True,
            output=(
                f"Personality reset to default profile: {reset_prof.name}\n"
                f"Session mood reset to: {ghost_engine.current_mood.value.upper()}"
            ),
        )

    if subcommand == "enable":
        ghost_engine.enable()
        return CommandResult(success=True, output="Ghost personality subsystem enabled.")

    if subcommand == "disable":
        ghost_engine.disable()
        return CommandResult(
            success=True,
            output=(
                "Ghost personality subsystem disabled. "
                "GhostTrace will operate as a neutral developer assistant."
            ),
        )

    return CommandResult(
        success=False,
        output=(
            f"Unknown ghost subcommand '{subcommand}'. "
            "Available: ghost, ghost status, ghost profiles, ghost set <profile>, "
            "ghost traits, ghost reset"
        ),
    )


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
            description="Display and configure ghost persona identities, mood, and traits.",
            usage="ghost [status|profiles|set <profile>|traits|reset]",
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
