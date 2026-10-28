"""Built-in command implementations and default registry factory for GhostTrace."""

from __future__ import annotations

import time

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
        "  • Status       : Step 10 / 10 — Final Release & Packaging (Complete)",
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

    dev_engine = context.dev_engine
    if dev_engine is None:
        dev_engine = ai_engine.developer_engine

    guard_engine = context.guardian_engine
    if guard_engine is None:
        from ghosttrace.guardian.engine import GuardianEngine

        guard_engine = GuardianEngine(context.settings)

    mem_engine = context.memory_engine
    if mem_engine is None:
        from ghosttrace.memory.engine import MemoryEngine

        mem_engine = MemoryEngine(context.settings)

    sys_engine = context.system_engine
    if sys_engine is None:
        from ghosttrace.system.engine import SystemEngine

        sys_engine = SystemEngine(context.settings)

    haunt_engine = context.haunt_engine
    if haunt_engine is None:
        from ghosttrace.haunt.engine import HauntEngine

        haunt_engine = HauntEngine(context.settings, ghost_engine=context.ghost_engine)

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

    dev_status_str = (
        "[OK] ACTIVE (STATIC ANALYSIS ON)"
        if (dev_engine.is_enabled and dev_engine._static_analysis_enabled)
        else ("[OK] ACTIVE" if dev_engine.is_enabled else "[!] DISABLED")
    )

    if not guard_engine.is_enabled:
        guard_status_str = "[!] DISABLED"
    elif not guard_engine.is_execution_enabled:
        guard_status_str = "[OK] ACTIVE (ANALYSIS ONLY)"
    elif guard_engine.policy.require_approval:
        guard_status_str = "[OK] ACTIVE (APPROVAL REQUIRED)"
    else:
        guard_status_str = "[OK] ACTIVE"

    if not mem_engine.is_enabled:
        mem_status_str = "[!] DISABLED"
    else:
        active_p = mem_engine.get_active_project()
        p_name = f" (PROJECT: {active_p.name})" if active_p else ""
        mem_status_str = f"[OK] ACTIVE (SQLITE){p_name}"

    sys_status_str = "[!] DISABLED" if not sys_engine.is_enabled else "[OK] ACTIVE (WIN32 / STDLIB)"

    if not haunt_engine.is_enabled:
        haunt_status_str = "[!] DISABLED"
    else:
        haunt_status_str = f"[OK] ACTIVE ({haunt_engine.mode.value.upper()})"

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
        f"  Developer Intel (Step 05)   : {dev_status_str}",
        f"  Command Guardian (Step 06)  : {guard_status_str}",
        f"  Persistent Memory (Step 07) : {mem_status_str}",
        f"  System Diagnostics (Step 08): {sys_status_str}",
        f"  Haunted Events (Step 09)    : {haunt_status_str}",
        "  Release Packaging (Step 10) : [OK] PRODUCTION READY",
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


def handle_dev(args: list[str], context: CommandContext) -> CommandResult:
    """Developer intelligence, code analysis, debugging, and code review."""
    ai_engine = context.ai_engine
    if ai_engine is None:
        from ghosttrace.ai.engine import AIEngine

        ai_engine = AIEngine(context.settings)

    dev_engine = context.dev_engine
    if dev_engine is None:
        dev_engine = ai_engine.developer_engine

    subcommand = args[0].lower() if args else "summary"
    sub_args = args[1:]
    content_arg = " ".join(sub_args).strip()

    if subcommand in ("help", "--help", "-h"):
        from ghosttrace.developer.responses import format_developer_help

        return CommandResult(success=True, output=format_developer_help())

    if subcommand in ("summary", "status") and not sub_args:
        lines = [
            "DEVELOPER ASSISTANT SUBSYSTEM",
            "==================================================",
            f"  Status          : {'ACTIVE' if dev_engine.is_enabled else 'DISABLED'}",
            (
                f"  Static Analysis : "
                f"{'ENABLED' if dev_engine._static_analysis_enabled else 'DISABLED'}"
            ),
            f"  Max Code Chars  : {dev_engine._max_code_chars}",
            f"  Max Context     : {dev_engine._max_context_chars}",
            "--------------------------------------------------",
            "  Available Workflows:",
            "    dev explain <code>   - Step-by-step logic and edge cases",
            "    dev debug <err/code> - Root cause analysis and minimal fix",
            "    dev review <code>    - Severity-rated code review",
            "    dev generate <spec>  - Idiomatic code generation",
            "    dev refactor <code>  - Modernization and simplification",
            "    dev tests <code>     - Pytest / unit test generation",
            "    dev language [hint]  - Language detection and info",
            "    dev analyze <code>   - Safe local static analysis (instant)",
            "==================================================",
            "Type 'dev help' for comprehensive instructions.",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "enable":
        dev_engine.enable()
        return CommandResult(success=True, output="Developer intelligence subsystem enabled.")

    if subcommand == "disable":
        dev_engine.disable()
        return CommandResult(success=True, output="Developer intelligence subsystem disabled.")

    if subcommand == "language":
        from ghosttrace.developer.languages import (
            detect_language,
            list_supported_languages,
        )

        if not content_arg:
            supported = list_supported_languages()
            names = ", ".join(f"{lang.name} ({lang.test_framework})" for lang in supported)
            return CommandResult(
                success=True,
                output=(
                    "SUPPORTED PROGRAMMING LANGUAGES:\n"
                    "==================================================\n"
                    f"{names}\n"
                    "==================================================\n"
                    "Usage: dev language <code_snippet_or_name>"
                ),
            )
        detected = detect_language(code=content_arg, query=content_arg, hint=content_arg)
        if detected:
            return CommandResult(
                success=True,
                output=(
                    f"DETECTED LANGUAGE: {detected.name} ({detected.id})\n"
                    f"• Default Test Framework : {detected.test_framework}\n"
                    f"• Comment Syntax         : {detected.comment_syntax}\n"
                    f"• File Extensions        : {', '.join(detected.extensions)}"
                ),
            )
        return CommandResult(
            success=True,
            output=(
                f"Could not identify language for: '{content_arg}'. "
                "Supported: python, js, ts, java, c, cpp, cs, go, rust, php, html, css, sql, "
                "bash, powershell."
            ),
        )

    if subcommand == "analyze":
        if not content_arg:
            return CommandResult(
                success=False,
                output=(
                    "Usage: dev analyze <code_snippet>\n"
                    "Runs safe local static analysis (AST parsing, functions, classes, imports) "
                    "without executing code."
                ),
            )
        report = dev_engine.format_static_analysis_report(content_arg)
        return CommandResult(success=True, output=report)

    # Workflow commands that dispatch to AI model:
    # explain, debug, review, generate, refactor, tests
    from ghosttrace.developer.schemas import DeveloperIntent

    intent_map = {
        "explain": DeveloperIntent.EXPLAIN_CODE,
        "debug": DeveloperIntent.DEBUG_CODE,
        "review": DeveloperIntent.REVIEW_CODE,
        "generate": DeveloperIntent.GENERATE_CODE,
        "refactor": DeveloperIntent.REFACTOR_CODE,
        "tests": DeveloperIntent.GENERATE_TESTS,
        "test": DeveloperIntent.GENERATE_TESTS,
        "optimize": DeveloperIntent.OPTIMIZE_CODE,
    }

    if subcommand in intent_map:
        target_intent = intent_map[subcommand]
        if not content_arg:
            return CommandResult(
                success=False,
                output=f"Usage: dev {subcommand} <code_snippet_or_requirements>",
            )

        status = ai_engine.get_status()
        if not status.runtime_available:
            return CommandResult(
                success=False,
                output=ai_engine.format_missing_runtime_message(),
            )
        if not status.model_exists:
            return CommandResult(
                success=False,
                output=ai_engine.format_missing_model_message(),
            )

        ctx, dev_instructions = dev_engine.prepare_developer_prompt(
            query=content_arg,
            intent_override=target_intent,
        )

        try:
            composed = ai_engine.ghost_engine.compose_system_prompt(
                user_query=content_arg,
                developer_instructions=dev_instructions,
            )
            ai_engine.conversation.update_system_prompt(composed)
            ai_engine.conversation.add_user_message(content_arg)
            messages = ai_engine.conversation.get_messages_for_llm()
            model = ai_engine.model_manager.load_model()
            res = ai_engine.inference_engine.generate(model, messages)
            ai_engine.conversation.add_assistant_message(res.text)

            from ghosttrace.developer.responses import format_task_headline

            headline = format_task_headline(target_intent, ctx.detected_language)
            output_text = f"[{headline}]\n\n{res.text}"
            return CommandResult(success=True, output=output_text)
        except Exception as exc:
            return CommandResult(
                success=False,
                output=f"Developer task failed during inference: {exc}",
            )

    return CommandResult(
        success=False,
        output=(
            f"Unknown dev subcommand '{subcommand}'. "
            "Available: dev, dev help, dev explain, dev debug, dev review, "
            "dev generate, dev refactor, dev tests, dev language, dev analyze"
        ),
    )


def handle_guard(args: list[str], context: CommandContext) -> CommandResult:
    """Manage Command Guardian, static command analysis, approval, and execution safety."""
    guard_engine = context.guardian_engine
    if guard_engine is None:
        from ghosttrace.guardian.engine import GuardianEngine

        guard_engine = GuardianEngine(context.settings)
        context.guardian_engine = guard_engine

    if not args:
        subcommand = "status"
        content_args: list[str] = []
    else:
        subcommand = args[0].lower()
        content_args = args[1:]

    if subcommand == "help":
        lines = [
            "GHOSTTRACE COMMAND GUARDIAN",
            "==================================================",
            "Safety-focused subsystem protecting your terminal and workspace from accidental",
            "destructive operations. Restricted execution model: shell=False, no shell wrappers,",
            "bounded stdout/stderr, and explicit per-command user approval.",
            "",
            "COMMAND REFERENCE:",
            "  guard                      Display Guardian subsystem status and configuration.",
            "  guard help                 Show this Guardian help and command reference.",
            "  guard status               Display active execution policy and settings.",
            "  guard analyze <command>    Statically analyze command risk without executing.",
            "  guard explain <command>    Explain command purpose and risk warnings.",
            "  guard run <command>        Analyze command and present an approval preview.",
            "  guard approve [token]      Confirm and execute an approved command (one-time).",
            "  guard cancel [token]       Cancel a pending command approval request.",
            "  guard history              Display bounded session execution history.",
            "  guard clear                Clear session execution history.",
            "  guard enable               Enable Command Guardian subsystem.",
            "  guard disable              Disable Command Guardian and halt command execution.",
            "",
            "EXAMPLES:",
            "  guard analyze git status",
            "  guard explain git reset --hard",
            "  guard run python --version",
            "  guard approve",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "status":
        status = guard_engine.get_status()
        lines = [
            "COMMAND GUARDIAN & EXECUTION SAFETY STATUS",
            "==================================================",
            f"  Guardian Subsystem : {'ACTIVE' if status.is_enabled else 'DISABLED'}",
            (
                "  Execution Permitted: "
                f"{'YES' if status.is_execution_enabled else 'NO (ANALYSIS ONLY)'}"
            ),
            f"  Approval Enforced  : {'YES (STRICT)' if status.requires_approval else 'NO'}",
            f"  Block High Risk    : {'YES' if status.block_high_risk else 'NO'}",
            (
                f"  Default Timeout    : {status.timeout_seconds}s "
                f"(max: {status.max_timeout_seconds}s)"
            ),
            f"  Max Output Chars   : {status.max_output_chars}",
            f"  Pending Approvals  : {status.pending_approval_count}",
            f"  Session History    : {status.history_count} / {status.history_limit} records",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "enable":
        guard_engine.enable()
        return CommandResult(success=True, output="Command Guardian subsystem enabled.")

    if subcommand == "disable":
        guard_engine.disable()
        return CommandResult(
            success=True,
            output="Command Guardian subsystem disabled. Controlled command execution is halted.",
        )

    if subcommand == "history":
        entries = guard_engine.get_history()
        if not entries:
            return CommandResult(
                success=True,
                output="No commands executed in this session yet.",
            )
        return CommandResult(success=True, output=guard_engine.history.format_table())

    if subcommand == "clear":
        guard_engine.clear_history()
        return CommandResult(
            success=True,
            output="Guardian session execution history cleared.",
        )

    if subcommand == "analyze":
        if not content_args:
            return CommandResult(
                success=False,
                output=(
                    "Usage: guard analyze <command>\n"
                    "Statically analyzes command risk without execution."
                ),
            )
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in content_args)
        from ghosttrace.guardian.explanations import format_command_analysis

        analysis = guard_engine.analyze(cmd_str)
        return CommandResult(success=True, output=format_command_analysis(analysis))

    if subcommand == "explain":
        if not content_args:
            return CommandResult(
                success=False,
                output=(
                    "Usage: guard explain <command>\nExplains command purpose and highlights risks."
                ),
            )
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in content_args)
        explanation = guard_engine.explain(cmd_str)
        return CommandResult(success=True, output=explanation)

    if subcommand == "run":
        if not content_args:
            return CommandResult(
                success=False,
                output=(
                    "Usage: guard run <command>\n"
                    "Analyzes command and requests approval before execution."
                ),
            )
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in content_args)
        from ghosttrace.guardian.explanations import format_approval_preview

        try:
            req = guard_engine.request_approval(cmd_str)
            preview = format_approval_preview(
                req,
                timeout_seconds=guard_engine.policy.timeout_seconds,
                max_output_chars=guard_engine.policy.max_output_chars,
            )
            return CommandResult(
                success=True,
                output=preview,
                command_name="guard_run",
            )
        except PermissionError as exc:
            return CommandResult(
                success=False,
                output=f"Execution request rejected:\n{exc}",
                command_name="guard_run",
            )

    if subcommand in ("approve", "confirm"):
        from ghosttrace.guardian.explanations import format_execution_result
        from ghosttrace.guardian.schemas import ExecutionStatus

        token = content_args[0].strip() if content_args else None
        if not token:
            latest = guard_engine.approval_mgr.get_latest_pending()
            if not latest:
                return CommandResult(
                    success=False,
                    output="No pending approval request found. Use 'guard run <command>' first.",
                )
            token = latest.token
            cmd_text = latest.analysis.original_command
        else:
            req = guard_engine.approval_mgr.get_request(token)
            if not req:
                return CommandResult(
                    success=False,
                    output=f"Approval request '{token}' not found, expired, or already consumed.",
                )
            cmd_text = req.analysis.original_command

        result = guard_engine.execute_approved(token=token, command=cmd_text)
        formatted = format_execution_result(result)
        return CommandResult(
            success=(result.status == ExecutionStatus.SUCCESS),
            output=formatted,
        )

    if subcommand == "cancel":
        token = content_args[0].strip() if content_args else None
        success, msg = guard_engine.cancel_approval(token)
        return CommandResult(success=success, output=msg)

    return CommandResult(
        success=False,
        output=(
            f"Unknown guard subcommand '{subcommand}'. Available:\n"
            "  guard, guard help, guard status, guard analyze, guard explain,\n"
            "  guard run, guard approve, guard cancel, guard history, guard clear,\n"
            "  guard enable, guard disable"
        ),
    )


def handle_memory(args: list[str], context: CommandContext) -> CommandResult:
    """Manage persistent conversation and developer memory."""
    mem_engine = context.memory_engine
    if mem_engine is None:
        from ghosttrace.memory.engine import MemoryEngine

        mem_engine = MemoryEngine(context.settings)

    subcommand = args[0].lower() if args else "status"
    sub_args = args[1:] if len(args) > 1 else []

    if subcommand in ("help", "--help", "-h"):
        help_lines = [
            "MEMORY SUBSYSTEM COMMANDS",
            "==================================================",
            "  memory                       — Show memory subsystem status",
            "  memory help                  — Show this help screen",
            "  memory status                — Show detailed database and context status",
            "  memory list [category]       — List recent memories, optionally filtered",
            "  memory search <query>        — Full-text search over memories",
            "  memory show <id>             — Display full details of a memory item",
            "  memory save <cat> <content>  — Explicitly store a memory item",
            "  memory edit <id> <content>   — Update memory item content",
            "  memory delete <id>           — Delete a memory item by ID",
            "  memory clear [--force]       — Clear all memories (requires confirmation)",
            "  memory stats                 — Show memory category and database statistics",
            "  memory export <file.json>    — Export memories to a JSON file",
            "  memory import <file.json>    — Import memories from a JSON file",
            "==================================================",
            "Categories: USER_PREFERENCE, USER_PROFILE, PROJECT_CONTEXT,",
            "            TECHNICAL_DECISION, WORKFLOW, LEARNING, GENERAL",
        ]
        return CommandResult(success=True, output="\n".join(help_lines))

    if subcommand == "status":
        status = mem_engine.get_status()
        active = mem_engine.get_active_project()
        active_proj_str = f"{active.name} ({active.root_path})" if active else "None"
        lines = [
            "PERSISTENT MEMORY STATUS",
            "==================================================",
            f"  Memory Subsystem : {'ENABLED' if status.is_enabled else 'DISABLED'}",
            f"  Database Path    : {status.database_path}",
            f"  Database Size    : {status.database_size_bytes:,} bytes",
            f"  WAL Mode Active  : {status.wal_mode}",
            f"  FTS5 Search      : {'ENABLED' if status.fts5_available else 'FALLBACK (LIKE)'}",
            f"  Total Memories   : {status.total_memories} / {status.max_items}",
            f"  Conversations    : {status.total_conversations}",
            f"  Messages Stored  : {status.total_messages}",
            f"  Projects (Total) : {status.total_projects}",
            f"  Project Files    : {status.total_project_files}",
            f"  Active Project   : {active_proj_str}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "list":
        category = sub_args[0].upper() if sub_args else None
        memories = mem_engine.list_memories(category=category, limit=50)
        if not memories:
            msg = f"No memories found{f' in category {category}' if category else ''}."
            return CommandResult(success=True, output=msg)

        table = Table(
            title=f"STORED MEMORIES{' (' + category + ')' if category else ''}",
            border_style="dim green",
            show_header=True,
        )
        table.add_column("ID", style="bold #00ff66", no_wrap=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Imp", style="yellow", no_wrap=True)
        table.add_column("Content Snippet", style="#99aa99")
        table.add_column("Created", style="dim", no_wrap=True)

        for m in memories:
            snippet = m.content.replace("\n", " ")
            if len(snippet) > 60:
                snippet = snippet[:57] + "..."
            created_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.created_at))
            table.add_row(
                str(m.id),
                m.category.value,
                str(m.importance),
                snippet,
                created_str,
            )
        return CommandResult(success=True, output=table)

    if subcommand == "search":
        if not sub_args:
            return CommandResult(success=False, output="Usage: memory search <query>")
        query = " ".join(sub_args)
        results = mem_engine.search_memories(query=query, limit=20)
        if not results:
            return CommandResult(success=True, output=f"No memories matched query: '{query}'")

        table = Table(
            title=f"MEMORY SEARCH RESULTS: '{query}'",
            border_style="dim green",
            show_header=True,
        )
        table.add_column("ID", style="bold #00ff66", no_wrap=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Score", style="yellow", no_wrap=True)
        table.add_column("Snippet / Match", style="#99aa99")

        for r in results:
            snippet = r.snippet.replace("\n", " ")
            if len(snippet) > 65:
                snippet = snippet[:62] + "..."
            table.add_row(
                str(r.memory.id),
                r.memory.category.value,
                f"{r.score:.2f}",
                snippet,
            )
        return CommandResult(success=True, output=table)

    if subcommand == "show":
        if not sub_args:
            return CommandResult(success=False, output="Usage: memory show <id>")
        try:
            mem_id = int(sub_args[0])
        except ValueError:
            return CommandResult(success=False, output=f"Invalid memory ID: {sub_args[0]}")
        item = mem_engine.get_memory(mem_id)
        if item is None:
            return CommandResult(success=False, output=f"Memory #{mem_id} not found.")

        created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.created_at))
        updated_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.updated_at))
        lines = [
            f"MEMORY ITEM #{item.id}",
            "==================================================",
            f"  Category   : {item.category.value}",
            f"  Source     : {item.source.value}",
            f"  Importance : {item.importance}/10",
            f"  Created At : {created_str}",
            f"  Updated At : {updated_str}",
            "--------------------------------------------------",
            "CONTENT:",
            item.content,
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "save":
        if len(sub_args) < 2:
            return CommandResult(
                success=False,
                output=(
                    "Usage: memory save <category> <content>\n"
                    "Categories: USER_PREFERENCE, USER_PROFILE, PROJECT_CONTEXT,\n"
                    "            TECHNICAL_DECISION, WORKFLOW, LEARNING, GENERAL"
                ),
            )
        from ghosttrace.memory.schemas import MemoryCategory, MemorySource

        cat_input = sub_args[0].upper()
        content = " ".join(sub_args[1:]).strip()

        matched_cat = MemoryCategory.GENERAL
        for cat in MemoryCategory:
            if cat.value == cat_input or cat.name == cat_input:
                matched_cat = cat
                break

        item = mem_engine.save_memory(
            category=matched_cat,
            content=content,
            source=MemorySource.EXPLICIT_USER,
            importance=5,
        )
        return CommandResult(
            success=True,
            output=f"Memory #{item.id} saved in category '{item.category.value}'.",
        )

    if subcommand == "edit":
        if len(sub_args) < 2:
            return CommandResult(success=False, output="Usage: memory edit <id> <new_content>")
        try:
            mem_id = int(sub_args[0])
        except ValueError:
            return CommandResult(success=False, output=f"Invalid memory ID: {sub_args[0]}")
        new_content = " ".join(sub_args[1:]).strip()
        updated = mem_engine.update_memory(mem_id, content=new_content)
        if updated is None:
            return CommandResult(success=False, output=f"Memory #{mem_id} not found.")
        return CommandResult(success=True, output=f"Memory #{mem_id} updated successfully.")

    if subcommand == "delete":
        if not sub_args:
            return CommandResult(success=False, output="Usage: memory delete <id>")
        try:
            mem_id = int(sub_args[0])
        except ValueError:
            return CommandResult(success=False, output=f"Invalid memory ID: {sub_args[0]}")
        deleted = mem_engine.delete_memory(mem_id)
        if deleted:
            return CommandResult(success=True, output=f"Memory #{mem_id} permanently deleted.")
        return CommandResult(success=False, output=f"Memory #{mem_id} not found.")

    if subcommand == "clear":
        force = any(a in ("--force", "-f") for a in sub_args)
        if not force:
            return CommandResult(
                success=False,
                output=(
                    "WARNING: This will permanently delete all saved memories.\n"
                    "To proceed, run: memory clear --force"
                ),
            )
        count = mem_engine.clear_all_memories()
        return CommandResult(success=True, output=f"Cleared {count} memories from database.")

    if subcommand == "stats":
        stats = mem_engine.get_memory_stats()
        lines = [
            "MEMORY SUBSYSTEM STATISTICS",
            "==================================================",
            f"  Total Memories   : {stats.get('total_memories', 0)}",
            f"  Conversations    : {stats.get('total_conversations', 0)}",
            f"  Messages Stored  : {stats.get('total_messages', 0)}",
            f"  Database Size    : {stats.get('database_size_bytes', 0):,} bytes",
            "--------------------------------------------------",
            "Memories by Category:",
        ]
        by_cat = stats.get("by_category", {})
        if isinstance(by_cat, dict):
            for cat_name, cnt in by_cat.items():
                lines.append(f"  • {cat_name:<20}: {cnt}")
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "export":
        if not sub_args:
            return CommandResult(success=False, output="Usage: memory export <path.json>")
        from pathlib import Path

        path = Path(" ".join(sub_args).strip().strip('"').strip("'"))
        try:
            count = mem_engine.export_memories(path)
            return CommandResult(
                success=True,
                output=f"Successfully exported {count} memories to {path}",
            )
        except Exception as exc:
            return CommandResult(success=False, output=f"Export failed: {exc}")

    if subcommand == "import":
        if not sub_args:
            return CommandResult(success=False, output="Usage: memory import <path.json>")
        from pathlib import Path

        path = Path(" ".join(sub_args).strip().strip('"').strip("'"))
        try:
            count = mem_engine.import_memories(path)
            return CommandResult(
                success=True,
                output=f"Successfully imported {count} memories from {path}",
            )
        except Exception as exc:
            return CommandResult(success=False, output=f"Import failed: {exc}")

    return CommandResult(
        success=False,
        output=(
            f"Unknown memory subcommand '{subcommand}'.\n"
            "Use 'memory help' to view available subcommands."
        ),
    )


def handle_project(args: list[str], context: CommandContext) -> CommandResult:
    """Manage registered projects, project switching, scanning, and indexing."""
    mem_engine = context.memory_engine
    if mem_engine is None:
        from ghosttrace.memory.engine import MemoryEngine

        mem_engine = MemoryEngine(context.settings)

    subcommand = args[0].lower() if args else "status"
    sub_args = args[1:] if len(args) > 1 else []

    if subcommand in ("help", "--help", "-h"):
        help_lines = [
            "PROJECT CONTEXT COMMANDS",
            "==================================================",
            "  project                      — Show current active project",
            "  project help                 — Show this help screen",
            "  project status               — Show active project status and statistics",
            "  project add <path> [name]    — Register a project directory",
            "  project list                 — List all registered projects",
            "  project use <name_or_path>   — Switch active project context",
            "  project info [name_or_path]  — Display detailed project configuration",
            "  project scan [name_or_path]  — Scan and index project files into database",
            "  project refresh              — Re-scan and re-index active project",
            "  project remove <name_or_path>— Unregister project and delete its indexed files",
            "  project clear                — Deselect active project context",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(help_lines))

    if subcommand == "status":
        active = mem_engine.get_active_project()
        if not active:
            return CommandResult(
                success=True,
                output=(
                    "No active project selected.\n"
                    "Use 'project add <path>' or 'project use <name>' to select one."
                ),
            )
        info = mem_engine.get_project_info(active.name)
        lines = [
            f"ACTIVE PROJECT: {active.name}",
            "==================================================",
            f"  ID           : {active.id}",
            f"  Root Path    : {active.root_path}",
            f"  Indexed Files: {info.get('file_count', 0)}",
            f"  Total Bytes  : {info.get('total_bytes', 0):,} bytes",
            f"  Last Indexed : {active.last_indexed_at or 'Never'}",
            f"  Registered   : {active.created_at}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "list":
        projects = mem_engine.list_projects()
        if not projects:
            return CommandResult(
                success=True,
                output="No projects registered. Register one with: project add <path> [name]",
            )
        active = mem_engine.get_active_project()
        table = Table(
            title="REGISTERED PROJECTS",
            border_style="dim green",
            show_header=True,
        )
        table.add_column("Active", style="bold #00ff66", no_wrap=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Files", style="yellow", no_wrap=True)
        table.add_column("Root Path", style="#99aa99")
        table.add_column("Last Indexed", style="dim", no_wrap=True)

        for p in projects:
            is_active = "*" if (active and active.id == p.id) else ""
            info = mem_engine.get_project_info(p.name)
            last_indexed_str = "Never"
            if p.last_indexed_at:
                last_indexed_str = time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(p.last_indexed_at)
                )
            table.add_row(
                is_active,
                p.name,
                str(info.get("file_count", 0)),
                p.root_path,
                last_indexed_str,
            )
        return CommandResult(success=True, output=table)

    if subcommand == "add":
        if not sub_args:
            return CommandResult(success=False, output="Usage: project add <path> [name]")
        from pathlib import Path

        path_str = sub_args[0].strip('"').strip("'")
        custom_name = sub_args[1].strip() if len(sub_args) > 1 else None
        try:
            proj = mem_engine.add_project(Path(path_str), name=custom_name)
            return CommandResult(
                success=True,
                output=(
                    f"Registered project '{proj.name}' at: {proj.root_path}\n"
                    f"To index its files, run: project scan {proj.name}"
                ),
            )
        except Exception as exc:
            return CommandResult(success=False, output=f"Failed to add project: {exc}")

    if subcommand == "use":
        if not sub_args:
            return CommandResult(success=False, output="Usage: project use <name_or_path>")
        name_or_path = " ".join(sub_args).strip().strip('"').strip("'")
        try:
            proj = mem_engine.set_active_project(name_or_path)
            return CommandResult(
                success=True,
                output=f"Switched active project to '{proj.name}' ({proj.root_path}).",
            )
        except Exception as exc:
            return CommandResult(success=False, output=f"Failed to switch project: {exc}")

    if subcommand == "clear":
        mem_engine.clear_active_project()
        return CommandResult(success=True, output="Cleared active project context.")

    if subcommand == "info":
        name_or_path = " ".join(sub_args).strip().strip('"').strip("'") if sub_args else None
        try:
            info = mem_engine.get_project_info(name_or_path)
            lines = [
                f"PROJECT INFORMATION: {info.get('name', 'Unknown')}",
                "==================================================",
                f"  ID           : {info.get('id')}",
                f"  Root Path    : {info.get('root_path')}",
                f"  Indexed Files: {info.get('file_count', 0)}",
                f"  Total Bytes  : {info.get('total_bytes', 0):,} bytes",
                f"  Last Indexed : {info.get('last_indexed_at') or 'Never'}",
                "--------------------------------------------------",
                "Languages:",
            ]
            langs = info.get("languages", {})
            if isinstance(langs, dict):
                for lang, count in langs.items():
                    lines.append(f"  • {lang:<15}: {count} files")
            lines.append("==================================================")
            return CommandResult(success=True, output="\n".join(lines))
        except Exception as exc:
            return CommandResult(success=False, output=f"Could not retrieve project info: {exc}")

    if subcommand in ("scan", "index"):
        name_or_path = " ".join(sub_args).strip().strip('"').strip("'") if sub_args else None
        try:
            res = mem_engine.scan_project(name_or_path)
            lines = [
                f"INDEXING COMPLETE: {res.project_name}",
                "==================================================",
                f"  Files Scanned : {res.scanned_files}",
                f"  Files Added   : {res.indexed_files}",
                f"  Files Updated : {res.updated_files}",
                f"  Files Stale   : {res.stale_files_removed} (removed)",
                f"  Total Bytes   : {res.total_bytes:,} bytes",
                f"  Elapsed Time  : {res.elapsed_seconds:.2f}s",
                "==================================================",
            ]
            if res.errors:
                lines.append("Errors encountered:")
                for err in res.errors[:5]:
                    lines.append(f"  • {err}")
            return CommandResult(success=True, output="\n".join(lines))
        except Exception as exc:
            return CommandResult(success=False, output=f"Project scan failed: {exc}")

    if subcommand == "refresh":
        try:
            res = mem_engine.refresh_active_project()
            lines = [
                f"ACTIVE PROJECT REFRESHED: {res.project_name}",
                "==================================================",
                f"  Files Scanned : {res.scanned_files}",
                f"  Files Added   : {res.indexed_files}",
                f"  Files Updated : {res.updated_files}",
                f"  Files Stale   : {res.stale_files_removed} (removed)",
                f"  Total Bytes   : {res.total_bytes:,} bytes",
                f"  Elapsed Time  : {res.elapsed_seconds:.2f}s",
                "==================================================",
            ]
            return CommandResult(success=True, output="\n".join(lines))
        except Exception as exc:
            return CommandResult(success=False, output=f"Project refresh failed: {exc}")

    if subcommand in ("remove", "delete", "rm"):
        if not sub_args:
            return CommandResult(success=False, output="Usage: project remove <name_or_path>")
        name_or_path = " ".join(sub_args).strip().strip('"').strip("'")
        try:
            removed = mem_engine.remove_project(name_or_path)
            if removed:
                return CommandResult(
                    success=True,
                    output=f"Unregistered project '{name_or_path}' and removed its indexed files.",
                )
            return CommandResult(
                success=False,
                output=f"Project '{name_or_path}' not found.",
            )
        except Exception as exc:
            return CommandResult(success=False, output=f"Failed to remove project: {exc}")

    return CommandResult(
        success=False,
        output=(
            f"Unknown project subcommand '{subcommand}'.\n"
            "Use 'project help' to view available subcommands."
        ),
    )


def handle_system(args: list[str], context: CommandContext) -> CommandResult:
    """System awareness, host telemetry, and internal health diagnostics."""
    sys_engine = context.system_engine
    if sys_engine is None:
        from ghosttrace.system.engine import SystemEngine

        sys_engine = SystemEngine(context.settings)

    haunt_engine = context.haunt_engine
    if haunt_engine is None:
        from ghosttrace.haunt.engine import HauntEngine

        haunt_engine = HauntEngine(context.settings, ghost_engine=context.ghost_engine)

    subcommand = args[0].lower() if args else "overview"
    sub_args = args[1:]

    if subcommand in ("help", "-h", "--help"):
        lines = [
            "SYSTEM AWARENESS & DIAGNOSTICS COMMANDS",
            "==================================================",
            "  system [overview]        — Display host hardware, OS, and resource snapshot",
            "  system status            — Display subsystem telemetry and cache configuration",
            "  system cpu               — Display CPU model, core counts, and utilization",
            "  system memory            — Display physical RAM and page-file utilization",
            "  system disk              — Display storage capacity on application drives",
            "  system processes         — Display aggregate process count & app footprint",
            "  system uptime            — Display operating system and application uptime",
            "  system health            — Run non-destructive internal subsystem health checks",
            "  system diagnostics [out] — Compile full diagnostic report (optional JSON export)",
            "==================================================",
            "Aliases: sys",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "status":
        lines = [
            "SYSTEM AWARENESS TELEMETRY STATUS",
            "==================================================",
            f"  Subsystem State    : {'ENABLED' if sys_engine.is_enabled else 'DISABLED'}",
            f"  Cache Duration     : {sys_engine.collector.cache_ttl} seconds",
            f"  Include Hostname   : "
            f"{bool(getattr(context.settings, 'system_include_hostname', False))}",
            f"  Process Details    : "
            f"{bool(getattr(context.settings, 'system_process_details', False))}",
            f"  Diagnostics Export : "
            f"{bool(getattr(context.settings, 'system_diagnostics_export', False))}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "cpu":
        cpu = sys_engine.get_cpu_info()
        usage_str = f"{cpu.cpu_percent}%" if cpu.cpu_percent is not None else "Unavailable"
        lines = [
            "CPU HARDWARE TELEMETRY",
            "==================================================",
            f"  Processor Model   : {cpu.model_name}",
            f"  Logical Cores     : {cpu.logical_cores or 'Unknown'}",
            f"  Physical Cores    : {cpu.physical_cores or 'Unknown / N/A'}",
            f"  Current Usage     : {usage_str}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand in ("memory", "ram"):
        mem = sys_engine.get_memory_info()
        lines = [
            "PHYSICAL RAM TELEMETRY",
            "==================================================",
            f"  Total Physical RAM : {mem.total_gb} GB ({mem.total_bytes:,} bytes)",
            f"  Available RAM      : {mem.available_gb} GB ({mem.available_bytes:,} bytes)",
            f"  Used RAM           : {mem.used_gb} GB ({mem.used_bytes:,} bytes)",
            f"  Memory Utilization : {mem.percent_used}%",
        ]
        if mem.pagefile_total_bytes is not None and mem.pagefile_available_bytes is not None:
            pf_total_gb = round(mem.pagefile_total_bytes / (1024**3), 2)
            pf_avail_gb = round(mem.pagefile_available_bytes / (1024**3), 2)
            lines.extend(
                [
                    "--------------------------------------------------",
                    f"  Page-file Total    : {pf_total_gb} GB",
                    f"  Page-file Avail    : {pf_avail_gb} GB",
                ]
            )
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "disk":
        disk = sys_engine.get_disk_info()
        if not disk.drives:
            return CommandResult(success=True, output="No accessible disk volumes found.")
        table = Table(title="DISK STORAGE VOLUMES", border_style="dim green")
        table.add_column("Volume", style="bold #00ff66")
        table.add_column("Free Space", style="#ffffff")
        table.add_column("Total Capacity", style="#99bb99")
        table.add_column("Used %", style="bold")
        for d in disk.drives:
            table.add_row(
                d.path,
                f"{d.free_gb} GB",
                f"{d.total_gb} GB",
                f"{d.percent_used}%",
            )
        return CommandResult(success=True, output=table)

    if subcommand in ("processes", "proc"):
        proc = sys_engine.get_process_info()
        p_count_str = (
            f"{proc.total_processes}" if proc.total_processes is not None else "Unavailable"
        )
        ws_str = (
            f"{proc.ghosttrace_working_set_mb} MB"
            if proc.ghosttrace_working_set_mb is not None
            else "Unavailable"
        )
        lines = [
            "PROCESS TELEMETRY & FOOTPRINT",
            "==================================================",
            f"  Total Running Processes : {p_count_str}",
            f"  GhostTrace PID          : {proc.ghosttrace_pid}",
            f"  GhostTrace Resident RAM : {ws_str}",
        ]
        if proc.ghosttrace_uptime_seconds is not None:
            from ghosttrace.system.uptime import format_duration

            lines.append(
                f"  GhostTrace Process Time : {format_duration(proc.ghosttrace_uptime_seconds)}"
            )
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "uptime":
        up = sys_engine.get_uptime_info()
        lines = [
            "SYSTEM & APPLICATION UPTIME",
            "==================================================",
            f"  Operating System Uptime : {up.system_uptime_formatted}",
            f"  GhostTrace App Uptime   : {up.app_uptime_formatted}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "health":
        health = sys_engine.check_health(
            ai_engine=context.ai_engine,
            ghost_engine=context.ghost_engine,
            dev_engine=context.dev_engine,
            guardian_engine=context.guardian_engine,
            memory_engine=context.memory_engine,
        )
        table = Table(
            title=f"SUBSYSTEM HEALTH DIAGNOSTICS [{health.overall_status.value}]",
            border_style="dim green",
        )
        table.add_column("Subsystem", style="bold #00ff66", width=22)
        table.add_column("Status", style="bold", width=14)
        table.add_column("Details", style="#99bb99")
        for name, sub in health.subsystems.items():
            color = (
                "#00ff66"
                if sub.status.value == "HEALTHY"
                else ("#ffaa00" if sub.status.value in ("DEGRADED", "DISABLED") else "#ff5555")
            )
            table.add_row(name, f"[{color}]{sub.status.value}[/]", sub.details)
        return CommandResult(success=True, output=table)

    if subcommand == "diagnostics":
        export_target = sub_args[0] if sub_args else None
        report = sys_engine.generate_diagnostics(
            ai_engine=context.ai_engine,
            ghost_engine=context.ghost_engine,
            dev_engine=context.dev_engine,
            guardian_engine=context.guardian_engine,
            memory_engine=context.memory_engine,
        )
        if export_target:
            try:
                dest = sys_engine.export_diagnostics_json(
                    target_path=export_target,
                    report=report,
                    overwrite=True,
                )
                msg = f"Diagnostic report exported successfully to: {dest}"
                return CommandResult(success=True, output=msg)
            except Exception as err:
                return CommandResult(success=False, output=f"Failed exporting diagnostics: {err}")

        # Display formatted report
        health_val = (
            report.snapshot.health.overall_status.value if report.snapshot.health else "UNKNOWN"
        )
        lines = [
            "==================================================",
            f"GHOSTTRACE DIAGNOSTIC REPORT (v{report.app_version})",
            "==================================================",
            (
                f"Platform   : {report.snapshot.platform.os_name} "
                f"{report.snapshot.platform.os_release} "
                f"({report.snapshot.platform.architecture})"
            ),
            f"Python     : {report.python_version} "
            f"({report.snapshot.platform.python_executable_arch})",
            (
                f"CPU        : {report.snapshot.cpu.model_name} "
                f"({report.snapshot.cpu.logical_cores} cores, "
                f"usage: {report.snapshot.cpu.cpu_percent}%)"
            ),
            (
                f"RAM        : {report.snapshot.memory.available_gb} GB avail / "
                f"{report.snapshot.memory.total_gb} GB total "
                f"({report.snapshot.memory.percent_used}% used)"
            ),
            (
                f"Uptime     : OS {report.snapshot.uptime.system_uptime_formatted} | "
                f"App {report.snapshot.uptime.app_uptime_formatted}"
            ),
            f"Health     : {health_val}",
        ]
        if report.warnings:
            lines.append("--------------------------------------------------")
            lines.append("Warnings:")
            for w in report.warnings:
                lines.append(f"  • {w}")
        if report.unavailable_metrics:
            lines.append("--------------------------------------------------")
            lines.append("Unavailable Metrics:")
            for u in report.unavailable_metrics:
                lines.append(f"  • {u}")
        lines.append("==================================================")
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "overview":
        snap = sys_engine.get_snapshot()
        health = sys_engine.check_health(
            ai_engine=context.ai_engine,
            ghost_engine=context.ghost_engine,
            dev_engine=context.dev_engine,
            guardian_engine=context.guardian_engine,
            memory_engine=context.memory_engine,
        )
        cpu_usage_str = (
            f"{snap.cpu.cpu_percent}% usage" if snap.cpu.cpu_percent is not None else "N/A"
        )
        cpu_str = f"{snap.cpu.model_name} ({snap.cpu.logical_cores} cores) — {cpu_usage_str}"
        mem_str = (
            f"{snap.memory.available_gb} GB free of {snap.memory.total_gb} GB "
            f"({snap.memory.percent_used}% used)"
        )
        disk_parts = [f"{d.path} ({d.free_gb} GB free)" for d in snap.disk.drives]
        disk_str = ", ".join(disk_parts) if disk_parts else "N/A"
        lines = [
            "SYSTEM & RESOURCE OVERVIEW",
            "==================================================",
            (
                f"  Host Platform : {snap.platform.os_name} {snap.platform.os_release} "
                f"({snap.platform.architecture})"
            ),
            (
                f"  Python Build  : {snap.platform.python_version} "
                f"({snap.platform.python_executable_arch})"
            ),
            f"  Processor     : {cpu_str}",
            f"  Physical RAM  : {mem_str}",
            f"  Disk Drives   : {disk_str}",
            f"  System Uptime : {snap.uptime.system_uptime_formatted}",
            f"  GhostTrace Up : {snap.uptime.app_uptime_formatted}",
            f"  Overall Health: [{health.overall_status.value}] {health.summary}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    return CommandResult(
        success=False,
        output=f"Unknown system subcommand: '{subcommand}'. Type 'system help' for usage.",
    )


def handle_haunt(args: list[str], context: CommandContext) -> CommandResult:
    """Haunted experience, experience modes, and interactive atmospheric ghost events."""
    haunt_engine = context.haunt_engine
    if haunt_engine is None:
        from ghosttrace.haunt.engine import HauntEngine

        haunt_engine = HauntEngine(context.settings, ghost_engine=context.ghost_engine)

    subcommand = args[0].lower() if args else "status"
    sub_args = args[1:]

    if subcommand in ("help", "-h", "--help"):
        lines = [
            "HAUNTED EXPERIENCE & ATMOSPHERIC EVENTS COMMANDS",
            "==================================================",
            "  haunt [status]         — Display active mode, frequency, and event budget",
            "  haunt mode [name]      — Set experience mode (normal, ambient, haunted, focus)",
            "  haunt events           — List supported supernatural event categories and counts",
            "  haunt intensity [lvl]  — Adjust event frequency and cooldowns (low, medium, high)",
            "  haunt history          — View bounded session event history log",
            "  haunt clear            — Clear session event history log",
            "  haunt idle [on|off]    — Toggle subtle atmospheric messages during terminal idle",
            "  haunt preview [cat]    — Preview an atmospheric event harmlessly without saving",
            "  haunt enable|disable   — Toggle the haunted experience subsystem",
            "==================================================",
            "Aliases: hunt",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "enable":
        haunt_engine.enable()
        return CommandResult(
            success=True,
            output="[bold #00ff66]Haunted experience subsystem enabled.[/]",
        )

    if subcommand == "disable":
        haunt_engine.disable()
        return CommandResult(
            success=True,
            output="[dim #ff5555]Haunted experience subsystem disabled.[/] (All events suppressed)",
        )

    if subcommand == "status":
        st = haunt_engine.get_status()
        state_badge = "[bold #00ff66]ENABLED[/]" if st.enabled else "[dim #ff5555]DISABLED[/]"
        lines = [
            "HAUNTED EXPERIENCE STATUS",
            "==================================================",
            f"  Subsystem State    : {state_badge}",
            f"  Experience Mode    : [bold #00ff66]{st.mode.value.upper()}[/]",
            f"  Event Intensity    : {st.intensity.value.upper()}",
            f"  Active Profile     : {st.active_profile}",
            f"  Current Mood       : {st.current_mood.upper()}",
            (
                f"  Session Budget     : {st.total_events_triggered} / "
                f"{st.max_events_per_session} triggered ({st.session_events_remaining} remaining)"
            ),
            f"  Base Cooldown      : {st.cooldown_seconds}s",
            (
                f"  Idle Whispers      : {'ENABLED' if st.idle_enabled else 'DISABLED'} "
                f"(Threshold: {st.idle_threshold_seconds}s)"
            ),
            f"  Reduced Motion     : {'ON' if st.reduced_motion else 'OFF'}",
            "==================================================",
        ]
        return CommandResult(success=True, output="\n".join(lines))

    if subcommand == "mode":
        if not sub_args:
            return CommandResult(
                success=True,
                output=(
                    f"Current experience mode: [bold #00ff66]{haunt_engine.mode.value.upper()}[/]\n"
                    "Available modes: normal (safe default), ambient, haunted, focus\n"
                    "Use 'haunt mode <name>' to switch immediately."
                ),
            )
        target_mode = sub_args[0].lower()
        from ghosttrace.haunt.schemas import HauntMode

        try:
            new_mode = haunt_engine.set_mode(target_mode)
            desc_map = {
                HauntMode.NORMAL: "Standard terminal experience. No unsolicited events.",
                HauntMode.AMBIENT: "Subtle atmospheric messages and occasional ghost reactions.",
                HauntMode.HAUNTED: "Expressive supernatural events and personality reactions.",
                HauntMode.FOCUS: "Quiet focus mode. All unsolicited events suppressed.",
            }
            formatted_mode = f"[bold #00ff66]{new_mode.value.upper()}[/]"
            return CommandResult(
                success=True,
                output=(
                    f"Haunted experience mode switched to {formatted_mode}.\n"
                    f"{desc_map.get(new_mode, '')}"
                ),
            )
        except ValueError:
            return CommandResult(
                success=False,
                output=(
                    f"Invalid experience mode '{target_mode}'. "
                    "Must be one of: normal, ambient, haunted, focus."
                ),
            )

    if subcommand == "intensity":
        if not sub_args:
            current_lvl = f"[bold #00ff66]{haunt_engine.intensity.value.upper()}[/]"
            return CommandResult(
                success=True,
                output=(
                    f"Current event intensity: {current_lvl}\n"
                    "Available levels: low (1.5x cooldown), medium (1.0x), high (0.6x)\n"
                    "Use 'haunt intensity <level>' to adjust."
                ),
            )
        lvl_arg = sub_args[0].lower()

        try:
            new_intensity = haunt_engine.set_intensity(lvl_arg)
            return CommandResult(
                success=True,
                output=f"Event intensity set to [bold #00ff66]{new_intensity.value.upper()}[/].",
            )
        except ValueError:
            return CommandResult(
                success=False,
                output=f"Invalid intensity '{lvl_arg}'. Must be one of: low, medium, high.",
            )

    if subcommand == "events":
        from ghosttrace.haunt.schemas import EventCategory

        table = Table(
            title="SUPERTERRESTRIAL EVENT CATEGORIES",
            border_style="#005522",
            show_header=True,
            header_style="bold #00ff66",
        )
        table.add_column("Category", style="bold #33ff33", width=20)
        table.add_column("Eligible Modes", style="#88cc88", width=22)
        table.add_column("Registered Events", style="#ddffdd", width=18)

        for cat in EventCategory:
            evs = haunt_engine.catalog.filter_by_category(cat)
            modes_str = ", ".join(m.value.upper() for m in (evs[0].eligible_modes if evs else []))
            table.add_row(cat.value, modes_str, f"{len(evs)} event(s)")

        return CommandResult(success=True, output=table)

    if subcommand == "history":
        history_entries = haunt_engine.get_history()
        if not history_entries:
            return CommandResult(
                success=True,
                output="No atmospheric events triggered in this session yet.",
            )
        table = haunt_engine.render_history_table()
        return CommandResult(success=True, output=table)

    if subcommand == "clear":
        haunt_engine.clear_history()
        return CommandResult(
            success=True,
            output="Session haunted event history cleared.",
        )

    if subcommand == "idle":
        if not sub_args:
            st = "ENABLED" if haunt_engine.scheduler.idle_enabled else "DISABLED"
            return CommandResult(
                success=True,
                output=f"Idle whisper events: {st}. Use 'haunt idle on' or 'haunt idle off'.",
            )
        setting = sub_args[0].lower()
        if setting in ("on", "true", "enable", "1"):
            haunt_engine.set_idle_events(True)
            return CommandResult(
                success=True,
                output="Idle whisper events [bold #00ff66]ENABLED[/].",
            )
        if setting in ("off", "false", "disable", "0"):
            haunt_engine.set_idle_events(False)
            return CommandResult(
                success=True,
                output="Idle whisper events [dim #ff5555]DISABLED[/].",
            )
        return CommandResult(
            success=False,
            output=f"Invalid idle setting '{setting}'. Use 'haunt idle on' or 'haunt idle off'.",
        )

    if subcommand == "preview":
        from ghosttrace.haunt.atmosphere import format_haunt_banner

        cat_arg = sub_args[0] if sub_args else None
        res = haunt_engine.preview_event(category=cat_arg)
        if not res.fired or res.rendered_text is None:
            return CommandResult(
                success=False,
                output=f"Preview generation failed: {res.reason}",
            )
        prof_id = (
            context.ghost_engine.active_profile.id.value if context.ghost_engine else "default"
        )
        banner = format_haunt_banner(
            title="PREVIEW RESONANCE",
            text=res.rendered_text,
            glyph=True,
            profile_id=prof_id,
        )
        return CommandResult(success=True, output=banner)

    return CommandResult(
        success=False,
        output=f"Unknown haunt subcommand: '{subcommand}'. Type 'haunt help' for usage.",
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
            name="dev",
            description="Developer intelligence, code analysis, debugging, and code review.",
            usage="dev [help|explain|debug|review|generate|refactor|tests|language|analyze]",
            handler=handle_dev,
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
            name="guard",
            description="Command Guardian & execution safety subsystem.",
            usage=(
                "guard [help|status|analyze|explain|run|approve|"
                "cancel|history|clear|enable|disable]"
            ),
            aliases=["guardian", "safety"],
            handler=handle_guard,
        )
    )
    registry.register(
        Command(
            name="memory",
            description="Persistent memory management (save, list, search, clear, stats).",
            usage=(
                "memory [help|status|list|search|show|save|edit|delete|clear|stats|export|import]"
            ),
            aliases=["mem"],
            handler=handle_memory,
        )
    )
    registry.register(
        Command(
            name="project",
            description="Project context indexing and management (add, list, use, scan, info).",
            usage="project [help|status|add|list|use|info|scan|refresh|remove|clear]",
            aliases=["proj"],
            handler=handle_project,
        )
    )
    registry.register(
        Command(
            name="system",
            description="System awareness, host telemetry, and internal health diagnostics.",
            usage="system [overview|status|cpu|memory|disk|processes|uptime|health|diagnostics]",
            aliases=["sys"],
            handler=handle_system,
        )
    )
    registry.register(
        Command(
            name="haunt",
            description="Haunted experience, experience modes, and interactive ghost events.",
            usage="haunt [help|status|mode|events|intensity|history|clear|idle|preview]",
            aliases=["hunt"],
            handler=handle_haunt,
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
