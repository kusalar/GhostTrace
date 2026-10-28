"""Structured command explanations, previews, and safety reporting for GhostTrace Guardian."""

from __future__ import annotations

from ghosttrace.guardian.schemas import ApprovalRequest, CommandAnalysis, ExecutionResult, RiskLevel


def get_risk_badge(level: RiskLevel) -> str:
    """Format styled visual risk badge for console or Textual rendering."""
    match level:
        case RiskLevel.SAFE:
            return "[bold #33ff33][ SAFE ][/]"
        case RiskLevel.LOW:
            return "[bold #00ffcc][ LOW RISK ][/]"
        case RiskLevel.MEDIUM:
            return "[bold #ffcc00][ MEDIUM RISK ][/]"
        case RiskLevel.HIGH:
            return "[bold #ff7700][ HIGH RISK - BLOCKED ][/]"
        case RiskLevel.BLOCKED:
            return "[bold #ff3333][ BLOCKED - PROHIBITED ][/]"


def format_command_analysis(analysis: CommandAnalysis) -> str:
    """Render a detailed static analysis report of a command."""
    badge = get_risk_badge(analysis.risk_level)
    lines = [
        "COMMAND GUARDIAN: STATIC ANALYSIS REPORT",
        "==================================================",
        f"Command     : {analysis.original_command}",
        f"Executable  : {analysis.executable or 'NONE'}",
    ]

    if analysis.resolved_executable_path:
        lines.append(f"Resolved    : {analysis.resolved_executable_path}")
    else:
        lines.append("Resolved    : NOT FOUND ON PATH")

    args_repr = " ".join(f"'{a}'" if " " in a else a for a in analysis.args)
    lines.append(f"Arguments   : {args_repr if args_repr else '(none)'}")
    lines.append(f"Risk Level  : {badge}")
    perm_str = (
        "YES (Explicit Approval Required)" if analysis.is_permitted else "NO (BLOCKED BY POLICY)"
    )
    lines.append(f"Permitted   : {perm_str}")

    if analysis.risk_reasons:
        lines.append("--------------------------------------------------")
        lines.append("Risk Reasons:")
        for reason in analysis.risk_reasons:
            lines.append(f" • {reason}")

    if analysis.side_effects:
        lines.append("--------------------------------------------------")
        lines.append("Expected Side Effects:")
        for effect in analysis.side_effects:
            lines.append(f" • {effect}")

    if analysis.safer_alternative:
        lines.append("--------------------------------------------------")
        lines.append(f"Suggested Safer Alternative:\n  {analysis.safer_alternative}")

    lines.append("==================================================")
    lines.append("NOTE: Restricted direct execution (shell=False). Shell operators not permitted.")
    return "\n".join(lines)


def format_command_explanation(analysis: CommandAnalysis) -> str:
    """Format a conversational explanation of a command's purpose and safety."""
    badge = get_risk_badge(analysis.risk_level)
    lines = [
        "COMMAND EXPLANATION & PURPOSE",
        "==================================================",
        f"Command     : {analysis.original_command}",
        f"Assessment  : {badge}",
        "",
    ]

    if analysis.executable:
        exe_lower = analysis.executable.lower().replace(".exe", "")
        lines.append(f"Target Binary : '{exe_lower}'")

    if analysis.args:
        lines.append(f"Arguments     : {', '.join(analysis.args)}")
    else:
        lines.append("Arguments     : (none)")

    lines.append("")
    lines.append("Behavioral Summary:")
    for reason in analysis.risk_reasons:
        lines.append(f" • {reason}")

    if analysis.side_effects:
        lines.append("")
        lines.append("Operational Impact:")
        for effect in analysis.side_effects:
            lines.append(f" • {effect}")

    if analysis.safer_alternative:
        lines.append("")
        lines.append(f"Safer Practice: {analysis.safer_alternative}")

    lines.append("==================================================")
    return "\n".join(lines)


def format_approval_preview(
    request: ApprovalRequest,
    timeout_seconds: int,
    max_output_chars: int,
) -> str:
    """Format clear user confirmation preview for pending command execution."""
    analysis = request.analysis
    badge = get_risk_badge(analysis.risk_level)

    args_repr = " ".join(f"'{a}'" if " " in a else a for a in analysis.args)
    lines = [
        "COMMAND EXECUTION APPROVAL PREVIEW",
        "==================================================",
        f"Approval Token : {request.token}",
        f"Exact Command  : {analysis.original_command}",
        f"Executable     : {analysis.executable or 'NONE'}",
        f"Resolved Path  : {analysis.resolved_executable_path or 'NOT RESOLVED'}",
        f"Arguments      : {args_repr if args_repr else '(none)'}",
        f"Working Dir    : {request.working_dir}",
        f"Risk Level     : {badge}",
        f"Timeout Limit  : {timeout_seconds} seconds",
        f"Output Limit   : {max_output_chars} characters",
        "--------------------------------------------------",
        "Risk Assessment:",
    ]

    for reason in analysis.risk_reasons:
        lines.append(f" • {reason}")

    if analysis.side_effects:
        lines.append("Expected Side Effects:")
        for effect in analysis.side_effects:
            lines.append(f" • {effect}")

    lines.extend(
        [
            "==================================================",
            "Awaiting explicit user confirmation.",
            f"To execute : guard approve {request.token}",
            f"To cancel  : guard cancel {request.token}",
        ]
    )
    return "\n".join(lines)


def format_execution_result(result: ExecutionResult) -> str:
    """Format human-readable execution output and metadata summary."""
    status_label = f"[{result.status.value}]"
    if result.exit_code is not None:
        status_label += f" (Exit Code {result.exit_code})"

    lines = [
        "EXECUTION RESULT",
        "==================================================",
        f"Command  : {result.command}",
        f"Status   : {status_label}",
        f"Duration : {result.duration_seconds:.3f}s",
        f"Work Dir : {result.working_dir}",
    ]

    if result.error_message:
        lines.append(f"Error    : {result.error_message}")

    if result.stdout.strip():
        lines.append("----------------- Standard Output ----------------")
        lines.append(result.stdout.strip())

    if result.stderr.strip():
        lines.append("----------------- Standard Error -----------------")
        lines.append(result.stderr.strip())

    if not result.stdout.strip() and not result.stderr.strip() and not result.error_message:
        lines.append("(Process completed with no output)")

    if result.truncated:
        lines.append("[!] Notice: Output stream was truncated due to size limits.")

    lines.append("==================================================")
    return "\n".join(lines)
