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
        "  • Status       : Step 06 / 10 — Command Guardian & Execution Safety",
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
            name="exit",
            description="Gracefully leave GhostTrace.",
            usage="exit",
            aliases=["quit", "q"],
            handler=handle_exit,
        )
    )

    return registry
