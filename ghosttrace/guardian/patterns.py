"""Dangerous command patterns and suspicious execution detection for GhostTrace Guardian."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ghosttrace.guardian.schemas import RiskLevel


@dataclass(frozen=True)
class PatternRule:
    """Definition of a dangerous or suspicious command heuristic pattern."""

    rule_id: str
    name: str
    category: str
    risk_level: RiskLevel
    reason: str
    side_effects: list[str] = field(default_factory=list)
    safer_alternative: str | None = None
    pattern: re.Pattern[str] | None = None


# Operator tokens that indicate shell chaining, piping, or redirection
SHELL_OPERATORS = ("&&", "||", ">>", "|&", ";", "|", ">", "<", "&")


def find_unquoted_shell_operators(command: str) -> list[str]:
    """Identify shell operators present outside quoted strings.

    Returns a list of detected operator strings in order of occurrence.
    Does not flag operators inside single or double quotes.
    """
    found: list[str] = []
    i = 0
    n = len(command)
    in_single_quote = False
    in_double_quote = False
    escape = False

    while i < n:
        char = command[i]

        if escape:
            escape = False
            i += 1
            continue

        if char == "\\" and not in_single_quote:
            escape = True
            i += 1
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            i += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            i += 1
            continue

        if not in_single_quote and not in_double_quote:
            # Check 2-character operators first
            two_char = command[i : i + 2]
            if two_char in ("&&", "||", ">>", "|&"):
                found.append(two_char)
                i += 2
                continue

            # Check 1-character operators
            if char in (";", "|", ">", "<", "&"):
                found.append(char)
                i += 1
                continue

        i += 1

    return found


def normalize_command_for_matching(command: str) -> str:
    """Normalize whitespace and slashes for uniform pattern matching."""
    # Collapse consecutive whitespace to single space
    cleaned = re.sub(r"\s+", " ", command.strip())
    return cleaned


# Concrete heuristic rule definitions
PATTERN_RULES: list[PatternRule] = [
    # -------------------------------------------------------------
    # 1. DESTRUCTIVE FILESYSTEM OPERATIONS (BLOCKED / HIGH)
    # -------------------------------------------------------------
    PatternRule(
        rule_id="FS-001",
        name="Drive Format",
        category="filesystem",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(r"^\s*format\s+([a-zA-Z]:|/fs:)", re.IGNORECASE),
        reason="Drive formatting completely erases all partition data and filesystem structures.",
        side_effects=[
            "Irreversible total data loss on target volume",
            "Destruction of filesystem tables",
        ],
    ),
    PatternRule(
        rule_id="FS-002",
        name="Disk Partition Manipulation",
        category="filesystem",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(r"\b(diskpart|fdisk|parted|sfdisk|mkfs)\b", re.IGNORECASE),
        reason=(
            "Disk partitioning tools can corrupt, wipe, or repartition physical storage devices."
        ),
        side_effects=["Partition table corruption", "Volume destruction", "Boot failure"],
    ),
    PatternRule(
        rule_id="FS-003",
        name="System Volume / Root Recursive Wipe",
        category="filesystem",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"(rmdir|rd)\s+.*(/s|/q).*"
            r"(?:\s+[a-zA-Z]:\\|\s+\*|\s+/(?:\s|$|\*)|\s+~|\$env:SystemRoot|\bwindows\b|\bsystem32\b)|"
            r"del\s+.*(/[fqsa]).*"
            r"(?:\s+[a-zA-Z]:\\|\s+\*|\s+/(?:\s|$|\*)|\s+~|\bwindows\b|\bsystem32\b)|"
            r"rm\s+-r?f\s+(?:/|[a-zA-Z]:\\|\*|~|\$HOME)|"
            r"Remove-Item\s+.*(-Recurse|-r).*(-Force|-f).*"
            r"(?:\s+\*|\s+[a-zA-Z]:\\|\s+/(?:\s|$|\*)|\s+~|\$env:SystemRoot)",
            re.IGNORECASE,
        ),
        reason=(
            "Destructive recursive deletion targeting drive roots, system directories, "
            "or wildcard root paths."
        ),
        side_effects=["Irreversible system destruction", "Total loss of operating system files"],
    ),
    PatternRule(
        rule_id="FS-004",
        name="Targeted Recursive Directory Deletion",
        category="filesystem",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"(rmdir|rd)\s+.*(/s|/q)|"
            r"\brm\s+.*(-r|-R|--recursive)\b|"
            r"Remove-Item\s+.*(-Recurse|-r)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Recursive directory deletion permanently removes an entire directory tree "
            "and all files within it."
        ),
        side_effects=[
            "Permanent directory removal",
            "Destruction of all nested files and subfolders",
        ],
        safer_alternative=(
            "Inspect directory contents with 'dir' or move to a temporary backup directory first."
        ),
    ),
    PatternRule(
        rule_id="FS-005",
        name="Forced Bulk File Deletion",
        category="filesystem",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"\b(del|erase)\s+.*(/[fqsa])|"
            r"\b(del|erase)\s+.*\*|"
            r"\brm\s+.*-(f|--force)\s+\*",
            re.IGNORECASE,
        ),
        reason=(
            "Forced file deletion bypasses user confirmation prompts and permanently "
            "removes target files."
        ),
        side_effects=["Irreversible file deletion without prompt confirmation"],
        safer_alternative=(
            "Delete individual files explicitly or use a file manager with recycle bin support."
        ),
    ),
    PatternRule(
        rule_id="FS-006",
        name="Shadow Copy and Boot Destruction",
        category="filesystem",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"\b(vssadmin\s+delete\s+shadows|wbadmin\s+delete|bcdedit\s+/delete|bootrec\s+/fixmbr)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Deleting volume shadow copies or altering boot configurations destroys "
            "system recovery capabilities."
        ),
        side_effects=["Destruction of restore points", "Inability to boot Windows"],
    ),
    # -------------------------------------------------------------
    # 2. SYSTEM-LEVEL OPERATIONS (BLOCKED / HIGH)
    # -------------------------------------------------------------
    PatternRule(
        rule_id="SYS-001",
        name="System Shutdown or Reboot",
        category="system",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"\b(shutdown(\.exe)?(\s+.*)?|reboot|init\s+[06]|Stop-Computer|Restart-Computer)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Shutdown or restart commands immediately terminate active processes and "
            "cause data loss for unsaved work."
        ),
        side_effects=[
            "Termination of running applications",
            "Session disconnection",
            "Potential unsaved data loss",
        ],
    ),
    PatternRule(
        rule_id="SYS-002",
        name="Service Modification or Deletion",
        category="system",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"\b(sc(\.exe)?\s+(delete|stop|config)|net(\.exe)?\s+stop|Stop-Service|Set-Service)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Stopping or modifying system services can destabilize operating system components "
            "and network daemons."
        ),
        side_effects=[
            "Service termination",
            "Background daemon disruption",
            "System service state changes",
        ],
        safer_alternative=(
            "Review service dependencies using 'sc query' before making modifications."
        ),
    ),
    PatternRule(
        rule_id="SYS-003",
        name="Registry Modification",
        category="system",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"\b(reg(\.exe)?\s+(delete|import|copy|add)|regedit(\.exe)?\s+/s|"
            r"Set-ItemProperty\s+.*HKLM|Remove-ItemProperty\s+.*HKLM)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Modifying or deleting Windows Registry keys can cause irreversible system corruption."
        ),
        side_effects=["Registry corruption", "Application breakage", "System boot instability"],
    ),
    PatternRule(
        rule_id="SYS-004",
        name="User and Security Permission Modification",
        category="system",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"\b(net(\.exe)?\s+user|net(\.exe)?\s+localgroup|"
            r"icacls(\.exe)?\s+.*(/grant|/deny|/setowner)|takeown(\.exe)?|"
            r"chmod\s+(-R\s+)?777|chown)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Altering user accounts or file system Access Control Lists (ACLs) can introduce "
            "major security vulnerabilities."
        ),
        side_effects=[
            "Altered security boundaries",
            "Permission escalation",
            "Unintended file accessibility",
        ],
        safer_alternative=(
            "Inspect permissions using 'icacls <path>' before making ACL modifications."
        ),
    ),
    PatternRule(
        rule_id="SYS-005",
        name="Security and Firewall Disabling",
        category="system",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"\b(netsh(\.exe)?\s+advfirewall|Set-MpPreference\s+-DisableRealtimeMonitoring|"
            r"Disable-WindowsOptionalFeature|ufw\s+disable)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Disabling Windows Defender, firewalls, or security controls exposes the machine "
            "to network vulnerabilities."
        ),
        side_effects=["Disabled network firewall", "Deactivated endpoint antivirus protection"],
    ),
    PatternRule(
        rule_id="SYS-006",
        name="Administrative Privilege Elevation",
        category="system",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"\b(runas(\.exe)?|sudo|Start-Process\s+.*-Verb\s+runas|gsudo)\b",
            re.IGNORECASE,
        ),
        reason="Elevation requests attempt to bypass standard unprivileged execution boundaries.",
        side_effects=["Elevated token privileges", "Administrative access grant"],
        safer_alternative="Execute commands using standard user privileges wherever possible.",
    ),
    # -------------------------------------------------------------
    # 3. SUSPICIOUS EXECUTION PATTERNS (BLOCKED / HIGH)
    # -------------------------------------------------------------
    PatternRule(
        rule_id="SEC-001",
        name="Encoded PowerShell Execution",
        category="suspicious",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"(powershell|pwsh)(\.exe)?\s+.*(-e|-enc|-encodedcommand)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Encoded PowerShell commands conceal executable payload contents and prevent "
            "transparent inspection."
        ),
        side_effects=["Execution of opaque base64-encoded instructions", "Hidden script execution"],
    ),
    PatternRule(
        rule_id="SEC-002",
        name="Hidden or Obfuscated PowerShell Execution",
        category="suspicious",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"(powershell|pwsh)(\.exe)?\s+.*(-w\s+hidden|-windowstyle\s+hidden)",
            re.IGNORECASE,
        ),
        reason=(
            "Hidden window execution is an evasion tactic used to conceal running subprocesses "
            "from the user."
        ),
        side_effects=["Concealed background process execution"],
    ),
    PatternRule(
        rule_id="SEC-003",
        name="ExecutionPolicy Bypass",
        category="suspicious",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"(powershell|pwsh)(\.exe)?\s+.*"
            r"(-executionpolicy\s+(bypass|unrestricted)|-ep\s+(bypass|unrestricted))\b",
            re.IGNORECASE,
        ),
        reason=(
            "Bypassing PowerShell execution policies circumvents administrative "
            "execution restrictions."
        ),
        side_effects=["Unsigned script execution", "Weakened PowerShell policy enforcement"],
        safer_alternative="Run scripts from signed files or review script contents thoroughly.",
    ),
    PatternRule(
        rule_id="SEC-004",
        name="Download and Execute Pipeline",
        category="suspicious",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"(Invoke-Expression|\biex\b|curl.*\|\s*(bash|sh|powershell|pwsh|cmd)|"
            r"wget.*\|\s*(bash|sh)|certutil(\.exe)?\s+.*-urlcache|bitsadmin(\.exe)?\s+/transfer)",
            re.IGNORECASE,
        ),
        reason=(
            "Downloading and piping content directly into an interpreter executes untrusted "
            "remote code without inspection."
        ),
        side_effects=["Arbitrary remote payload execution", "System compromise"],
    ),
    PatternRule(
        rule_id="SEC-005",
        name="Remote Script Host Execution",
        category="suspicious",
        risk_level=RiskLevel.BLOCKED,
        pattern=re.compile(
            r"\b(mshta(\.exe)?|regsvr32(\.exe)?\s+.*(/i:http|/s)|rundll32(\.exe)?\s+.*javascript:)\b",
            re.IGNORECASE,
        ),
        reason=(
            "Using Windows script hosts or DLL loaders with remote URLs is a recognized "
            "living-off-the-land attack technique."
        ),
        side_effects=["Remote arbitrary code execution via system binaries"],
    ),
    # -------------------------------------------------------------
    # 4. VERSION CONTROL RISKS (HIGH / MEDIUM)
    # -------------------------------------------------------------
    PatternRule(
        rule_id="VCS-001",
        name="Git Hard Reset",
        category="version_control",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        reason=(
            "Hard git reset permanently discards all uncommitted modifications in tracked files."
        ),
        side_effects=[
            "Irreversible loss of uncommitted local changes",
            "Working tree reset to target commit",
        ],
        safer_alternative=(
            "Use 'git stash' to safely save changes, or 'git reset --soft' to keep changes staged."
        ),
    ),
    PatternRule(
        rule_id="VCS-002",
        name="Forced Git Clean",
        category="version_control",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(r"\bgit\s+clean\s+.*-[a-zA-Z]*f[a-zA-Z]*", re.IGNORECASE),
        reason=(
            "Forced git clean permanently deletes untracked files and directories "
            "from the repository."
        ),
        side_effects=["Permanent deletion of untracked files and build artifacts"],
        safer_alternative=(
            "Run 'git clean -n' first to dry-run and preview files before permanent deletion."
        ),
    ),
    PatternRule(
        rule_id="VCS-003",
        name="Forced Git Push",
        category="version_control",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(r"\bgit\s+push\s+.*(-f|--force)\b", re.IGNORECASE),
        reason=(
            "Forced push overwrites remote branch history and can discard commits "
            "published by collaborators."
        ),
        side_effects=[
            "Overwritten remote branch history",
            "Potential loss of collaborative commits",
        ],
        safer_alternative=(
            "Use 'git push --force-with-lease' to prevent overwriting commits "
            "you have not yet seen."
        ),
    ),
    PatternRule(
        rule_id="VCS-004",
        name="Forced Branch Deletion",
        category="version_control",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(r"\bgit\s+branch\s+-[a-zA-Z]*D[a-zA-Z]*\b", re.IGNORECASE),
        reason=(
            "Forced branch deletion deletes a Git branch regardless of whether "
            "its commits have been merged."
        ),
        side_effects=["Branch reference deletion", "Potential unmerged commit loss"],
        safer_alternative=(
            "Use 'git branch -d' (lowercase) to guarantee branch changes are merged first."
        ),
    ),
    PatternRule(
        rule_id="VCS-005",
        name="Destructive History Rewriting",
        category="version_control",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(r"\bgit\s+filter-branch\b", re.IGNORECASE),
        reason="git filter-branch permanently rewrites repository commit history.",
        side_effects=["Total repository history rewrite", "SHA-1 commit hash recalculation"],
        safer_alternative=(
            "Consider git-filter-repo or careful interactive rebase on local branches."
        ),
    ),
    # -------------------------------------------------------------
    # 5. PACKAGE & ENVIRONMENT RISKS (HIGH / MEDIUM)
    # -------------------------------------------------------------
    PatternRule(
        rule_id="PKG-001",
        name="Package Uninstallation",
        category="package_management",
        risk_level=RiskLevel.HIGH,
        pattern=re.compile(
            r"\b(pip\s+uninstall|npm\s+uninstall|pnpm\s+uninstall|yarn\s+remove)\b",
            re.IGNORECASE,
        ),
        reason="Uninstalling packages removes project dependencies and can break running software.",
        side_effects=["Dependency removal", "Potential runtime import errors"],
        safer_alternative=(
            "Verify package dependency trees or isolate installations in a virtual environment."
        ),
    ),
    PatternRule(
        rule_id="PKG-002",
        name="Global Package Installation",
        category="package_management",
        risk_level=RiskLevel.MEDIUM,
        pattern=re.compile(r"\b(npm\s+install\s+.*-g|pip\s+install\s+.*--user)\b", re.IGNORECASE),
        reason="Global package installation modifies system-wide runtime environments.",
        side_effects=[
            "System-wide environment modification",
            "Potential global version conflicts",
        ],
        safer_alternative="Install packages within a localized project virtual environment.",
    ),
    PatternRule(
        rule_id="PKG-003",
        name="Persistent Environment Variable Modification",
        category="environment",
        risk_level=RiskLevel.MEDIUM,
        pattern=re.compile(r"^\s*setx\b", re.IGNORECASE),
        reason=(
            "setx permanently modifies Windows user or system environment variables "
            "in the Registry."
        ),
        side_effects=["Permanent Registry environment variable modification"],
        safer_alternative=(
            "Set session-local environment variables using standard shell configuration."
        ),
    ),
]


def match_dangerous_patterns(command: str) -> list[PatternRule]:
    """Evaluate a normalized command string against all dangerous pattern heuristics.

    Returns all matched pattern rules.
    """
    normalized = normalize_command_for_matching(command)
    matches: list[PatternRule] = []

    for rule in PATTERN_RULES:
        if rule.pattern is not None and rule.pattern.search(normalized):
            matches.append(rule)

    return matches
