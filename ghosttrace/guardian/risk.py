"""Risk classification and severity assessment engine for GhostTrace Command Guardian."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.guardian.patterns import PatternRule
from ghosttrace.guardian.schemas import RiskLevel

# Recognized read-only commands that produce zero persistent modifications
SAFE_INSPECTION_COMMANDS: dict[str, set[str] | None] = {
    "ipconfig": None,  # All args read-only (e.g. /all)
    "whoami": None,
    "systeminfo": None,
    "hostname": None,
    "where": None,
    "which": None,
    "dir": None,
    "echo": None,
    "ping": None,
}

# Subcommands or flag combinations for common tools classified as strictly SAFE (read-only)
SAFE_TOOL_SUBCOMMANDS: dict[str, set[str]] = {
    "git": {
        "status",
        "log",
        "diff",
        "show",
        "branch",  # plain branch listing
        "tag",  # plain tag listing
        "remote",  # e.g. -v
        "describe",
        "--version",
        "-v",
        "help",
        "--help",
    },
    "python": {"--version", "-v", "--help", "-h"},
    "py": {"--version", "-v", "--help", "-h"},
    "pytest": {"-q", "--version", "--help", "-h"},
    "pip": {"show", "list", "--version", "-v", "check", "cache"},
    "ruff": {"check", "--version", "--help"},
    "cargo": {"check", "--version", "help", "--help"},
    "rustc": {"--version", "-v", "--help"},
    "node": {"--version", "-v", "--help"},
    "npm": {"list", "view", "--version", "-v", "outdated"},
}

# Subcommands classified as LOW risk (ordinary local non-destructive dev operations)
LOW_RISK_DEV_SUBCOMMANDS: dict[str, set[str]] = {
    "git": {"add", "commit", "checkout", "switch", "stash", "fetch"},
    "pytest": {"-k", "-m", "-x", "-v", "--cov"},
    "pip": {"install"},
    "mkdir": set(),
    "md": set(),
    "ruff": {"format"},
}


def classify_command_risk(
    executable: str | None,
    args: list[str],
    matched_rules: list[PatternRule],
    unquoted_operators: list[str],
    is_malformed: bool = False,
) -> tuple[RiskLevel, list[str], list[str], str | None, bool]:
    """Classify the risk level of a parsed command and determine operational policy.

    Returns:
        (risk_level, risk_reasons, side_effects, safer_alternative, is_permitted)
    """
    reasons: list[str] = []
    side_effects: list[str] = []
    safer_alt: str | None = None

    # 1. Malformed input checks (unbalanced quotes, parsing errors)
    if is_malformed:
        reasons.append("Command syntax is malformed or contains unbalanced quotation marks.")
        side_effects.append("Unpredictable argument parsing behavior")
        return RiskLevel.BLOCKED, reasons, side_effects, None, False

    # 2. Unquoted shell operators (piping, redirection, chaining)
    if unquoted_operators:
        reasons.append(
            f"Command contains unquoted shell operators ({', '.join(unquoted_operators)}). "
            "Shell chaining and redirection are strictly prohibited in restricted execution mode."
        )
        side_effects.append("Arbitrary subshell command chaining")
        return RiskLevel.BLOCKED, reasons, side_effects, None, False

    # 3. Check matched heuristic pattern rules
    blocked_rules = [r for r in matched_rules if r.risk_level == RiskLevel.BLOCKED]
    if blocked_rules:
        for rule in blocked_rules:
            reasons.append(f"[{rule.rule_id}] {rule.name}: {rule.reason}")
            side_effects.extend(rule.side_effects)
            if rule.safer_alternative and not safer_alt:
                safer_alt = rule.safer_alternative
        return RiskLevel.BLOCKED, reasons, side_effects, safer_alt, False

    high_rules = [r for r in matched_rules if r.risk_level == RiskLevel.HIGH]
    if high_rules:
        for rule in high_rules:
            reasons.append(f"[{rule.rule_id}] {rule.name}: {rule.reason}")
            side_effects.extend(rule.side_effects)
            if rule.safer_alternative and not safer_alt:
                safer_alt = rule.safer_alternative
        # High risk is blocked by default policy
        return RiskLevel.HIGH, reasons, side_effects, safer_alt, False

    med_rules = [r for r in matched_rules if r.risk_level == RiskLevel.MEDIUM]
    if med_rules:
        for rule in med_rules:
            reasons.append(f"[{rule.rule_id}] {rule.name}: {rule.reason}")
            side_effects.extend(rule.side_effects)
            if rule.safer_alternative and not safer_alt:
                safer_alt = rule.safer_alternative
        return RiskLevel.MEDIUM, reasons, side_effects, safer_alt, True

    # 4. Unknown or missing executable evaluation
    if not executable:
        reasons.append("No executable or binary target specified.")
        return RiskLevel.BLOCKED, reasons, side_effects, None, False

    exe_lower = Path(executable).stem.lower()

    # Check for dedicated SAFE inspection tools
    if exe_lower in SAFE_INSPECTION_COMMANDS:
        reasons.append("Read-only system information or diagnostic query.")
        side_effects.append("None (Read-only console output)")
        return RiskLevel.SAFE, reasons, side_effects, None, True

    # Check subcommands of known development tools
    if exe_lower in SAFE_TOOL_SUBCOMMANDS:
        allowed_safe_subcmds = SAFE_TOOL_SUBCOMMANDS[exe_lower]
        first_arg = args[0].lower() if args else ""
        if (not args and "" in allowed_safe_subcmds) or (first_arg in allowed_safe_subcmds):
            reasons.append(f"Read-only query command for '{exe_lower}'.")
            side_effects.append("None (Read-only console output)")
            return RiskLevel.SAFE, reasons, side_effects, None, True

    # Check for LOW risk standard development commands
    if exe_lower in LOW_RISK_DEV_SUBCOMMANDS:
        first_arg = args[0].lower() if args else ""
        allowed_low = LOW_RISK_DEV_SUBCOMMANDS[exe_lower]
        if (
            not allowed_low
            or first_arg in allowed_low
            or any(arg.lower() in allowed_low for arg in args)
        ):
            reasons.append(f"Standard development operation using '{exe_lower}'.")
            side_effects.append("Local project or working tree modification")
            return RiskLevel.LOW, reasons, side_effects, None, True

    # Check general python invocation: running a script or test
    if exe_lower in ("python", "py"):
        if args and args[0] == "-c":
            reasons.append("Inline Python code evaluation (-c). Potential local side effects.")
            side_effects.append("Execution of inline script instructions")
            return RiskLevel.MEDIUM, reasons, side_effects, None, True
        reasons.append("Executing Python interpreter with script or arguments.")
        side_effects.append("Script execution within local working environment")
        return RiskLevel.LOW, reasons, side_effects, None, True

    # Check general pytest invocation without args (runs tests)
    if exe_lower == "pytest":
        reasons.append("Executing local automated test suite.")
        side_effects.append("Execution of test fixtures and assertions")
        return RiskLevel.LOW, reasons, side_effects, None, True

    # Check simple directory creation
    if exe_lower in ("mkdir", "md"):
        reasons.append("Creating new filesystem directory.")
        side_effects.append("New directory entry created on filesystem")
        return RiskLevel.LOW, reasons, side_effects, None, True

    # 5. Unknown or unrecognized commands:
    # "Unknown commands must not automatically receive SAFE classification."
    reasons.append(
        f"Unrecognized or custom executable '{executable}'. "
        "Conservative MEDIUM risk assigned due to unverified parameter semantics."
    )
    side_effects.append("Unknown process execution and potential system modifications")
    return (
        RiskLevel.MEDIUM,
        reasons,
        side_effects,
        "Verify tool documentation before executing.",
        True,
    )
