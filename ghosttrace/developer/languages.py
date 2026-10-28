"""Lightweight programming language detection and metadata without filesystem access."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageInfo:
    """Metadata describing a supported programming language."""

    id: str
    name: str
    aliases: tuple[str, ...]
    extensions: tuple[str, ...]
    test_framework: str
    comment_syntax: str
    code_fence: str


SUPPORTED_LANGUAGES: tuple[LanguageInfo, ...] = (
    LanguageInfo(
        id="python",
        name="Python",
        aliases=("python", "py", "python3"),
        extensions=(".py", ".pyw", ".pyi"),
        test_framework="pytest",
        comment_syntax="#",
        code_fence="python",
    ),
    LanguageInfo(
        id="javascript",
        name="JavaScript",
        aliases=("javascript", "js", "node"),
        extensions=(".js", ".mjs", ".cjs"),
        test_framework="jest",
        comment_syntax="//",
        code_fence="javascript",
    ),
    LanguageInfo(
        id="typescript",
        name="TypeScript",
        aliases=("typescript", "ts"),
        extensions=(".ts", ".tsx", ".mts"),
        test_framework="vitest",
        comment_syntax="//",
        code_fence="typescript",
    ),
    LanguageInfo(
        id="java",
        name="Java",
        aliases=("java",),
        extensions=(".java",),
        test_framework="JUnit 5",
        comment_syntax="//",
        code_fence="java",
    ),
    LanguageInfo(
        id="c",
        name="C",
        aliases=("c",),
        extensions=(".c", ".h"),
        test_framework="Unity / CTest",
        comment_syntax="//",
        code_fence="c",
    ),
    LanguageInfo(
        id="cpp",
        name="C++",
        aliases=("cpp", "c++", "cxx", "cc"),
        extensions=(".cpp", ".hpp", ".cc", ".cxx"),
        test_framework="GoogleTest",
        comment_syntax="//",
        code_fence="cpp",
    ),
    LanguageInfo(
        id="csharp",
        name="C#",
        aliases=("csharp", "c#", "cs"),
        extensions=(".cs",),
        test_framework="xUnit / NUnit",
        comment_syntax="//",
        code_fence="csharp",
    ),
    LanguageInfo(
        id="go",
        name="Go",
        aliases=("go", "golang"),
        extensions=(".go",),
        test_framework="testing (go test)",
        comment_syntax="//",
        code_fence="go",
    ),
    LanguageInfo(
        id="rust",
        name="Rust",
        aliases=("rust", "rs"),
        extensions=(".rs",),
        test_framework="cargo test",
        comment_syntax="//",
        code_fence="rust",
    ),
    LanguageInfo(
        id="php",
        name="PHP",
        aliases=("php",),
        extensions=(".php",),
        test_framework="PHPUnit",
        comment_syntax="//",
        code_fence="php",
    ),
    LanguageInfo(
        id="html",
        name="HTML",
        aliases=("html", "htm"),
        extensions=(".html", ".htm"),
        test_framework="Playwright / Cypress",
        comment_syntax="<!-- -->",
        code_fence="html",
    ),
    LanguageInfo(
        id="css",
        name="CSS",
        aliases=("css", "scss", "sass"),
        extensions=(".css", ".scss", ".sass"),
        test_framework="Stylelint",
        comment_syntax="/* */",
        code_fence="css",
    ),
    LanguageInfo(
        id="sql",
        name="SQL",
        aliases=("sql", "psql", "mysql"),
        extensions=(".sql",),
        test_framework="pgTAP / tSQLt",
        comment_syntax="--",
        code_fence="sql",
    ),
    LanguageInfo(
        id="bash",
        name="Bash / Shell",
        aliases=("bash", "sh", "shell", "zsh"),
        extensions=(".sh", ".bash"),
        test_framework="BATS",
        comment_syntax="#",
        code_fence="bash",
    ),
    LanguageInfo(
        id="powershell",
        name="PowerShell",
        aliases=("powershell", "ps1", "pwsh"),
        extensions=(".ps1", ".psm1", ".psd1"),
        test_framework="Pester",
        comment_syntax="#",
        code_fence="powershell",
    ),
)

_LANGUAGE_BY_ALIAS: dict[str, LanguageInfo] = {}
for lang in SUPPORTED_LANGUAGES:
    for alias in lang.aliases:
        _LANGUAGE_BY_ALIAS[alias.lower()] = lang
    for ext in lang.extensions:
        _LANGUAGE_BY_ALIAS[ext.lower()] = lang
    _LANGUAGE_BY_ALIAS[lang.id.lower()] = lang
    _LANGUAGE_BY_ALIAS[lang.name.lower()] = lang


# Syntax patterns for conservative pattern detection
_SYNTAX_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s*#!\s*/bin/(?:bash|sh)\b", re.MULTILINE), "bash"),
    (re.compile(r"<\?php\b"), "php"),
    (re.compile(r"<!DOCTYPE\s+html|<html\b|<body\b", re.IGNORECASE), "html"),
    (re.compile(r"\bpublic\s+class\s+\w+|\bpublic\s+static\s+void\s+main\b"), "java"),
    (re.compile(r"\busing\s+System(?:\.\w+)*\s*;|\bConsole\.WriteLine\b"), "csharp"),
    (re.compile(r"#include\s*<iostream>|\bstd::cout\b|\bstd::vector\b"), "cpp"),
    (re.compile(r"#include\s*<\w+\.h>|\bprintf\s*\(|\bint\s+main\s*\("), "c"),
    (re.compile(r"\bfn\s+\w+\s*\(|\bpub\s+fn\b|\blet\s+mut\s+|\bimpl\s+\w+"), "rust"),
    (re.compile(r"\bfunc\s+\w+\s*\(|\bpackage\s+\w+\b"), "go"),
    (re.compile(r"\bdef\s+\w+\s*\(|\bimport\s+\w+|\bfrom\s+\w+\s+import\b"), "python"),
    (
        re.compile(r"\binterface\s+\w+|\btype\s+\w+\s*=|:\s*(?:string|number|boolean|any)\b"),
        "typescript",
    ),
    (
        re.compile(r"\bconst\s+\w+\s*=|function\s+\w+\s*\(|console\.log\s*\(|=>\s*\{"),
        "javascript",
    ),
    (
        re.compile(
            r"\bSELECT\s+.+\s+FROM\s+\w+|\bINSERT\s+INTO\b|\bCREATE\s+TABLE\b",
            re.IGNORECASE,
        ),
        "sql",
    ),
    (
        re.compile(
            r"\$(?:PSScriptRoot|env:|LASTEXITCODE)\b|\bGet-Process\b|\bWrite-Host\b",
            re.IGNORECASE,
        ),
        "powershell",
    ),
    (
        re.compile(
            r"[.#]?[\w.-]+\s*\{[^\}]*?(?:color|margin|padding|display)\s*:",
            re.DOTALL,
        ),
        "css",
    ),
)


def get_language(name_or_alias: str) -> LanguageInfo | None:
    """Lookup supported language by name, alias, or file extension."""
    clean = name_or_alias.strip().lower()
    return _LANGUAGE_BY_ALIAS.get(clean)


def list_supported_languages() -> list[LanguageInfo]:
    """Return all supported language descriptors."""
    return list(SUPPORTED_LANGUAGES)


def detect_language(
    code: str = "",
    query: str = "",
    hint: str | None = None,
) -> LanguageInfo | None:
    """Detect programming language using hint, code fence, extension, or syntax patterns.

    Never accesses or inspects the local filesystem.
    """
    if hint:
        found = get_language(hint)
        if found is not None:
            return found

    # 1. Inspect fenced markdown code blocks (e.g. ```python)
    fence_match = re.search(r"```([a-zA-Z0-9_+#-]+)", query + "\n" + code)
    if fence_match:
        tag = fence_match.group(1).lower()
        found = get_language(tag)
        if found is not None:
            return found

    # 2. Inspect query for explicit file extensions (e.g. main.go, app.py)
    ext_matches = re.findall(r"\.([a-zA-Z0-9]+)\b", query)
    for ext in ext_matches:
        found = get_language(f".{ext}")
        if found is not None:
            return found

    # 3. Inspect query for explicit language keywords
    words = re.findall(r"\b[a-zA-Z0-9_+#-]+\b", query)
    for word in words:
        found = get_language(word)
        if found is not None:
            return found

    # 4. Syntax pattern heuristics across supplied code
    snippet = code.strip() if code else query.strip()
    if snippet:
        for pattern, lang_id in _SYNTAX_PATTERNS:
            if pattern.search(snippet):
                return get_language(lang_id)

    return None
