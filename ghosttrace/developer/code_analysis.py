"""Safe local static analysis of explicitly supplied code snippets without execution."""

from __future__ import annotations

import ast
import re

from ghosttrace.developer.schemas import CodeAnalysisResult


def analyze_python_code(code: str) -> CodeAnalysisResult:
    """Safely analyze explicitly supplied Python code using ast.parse without execution.

    Never executes, imports, or evaluates user-supplied code.
    """
    lines = code.splitlines()
    line_count = len(lines)
    char_count = len(code)

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    observations: list[str] = []

    try:
        tree = ast.parse(code)
        is_valid = True
        err_msg: str | None = None
        err_line: int | None = None
        err_col: int | None = None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                # Check for missing docstring
                if not ast.get_docstring(node):
                    observations.append(f"Function '{node.name}' has no docstring.")
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                if not ast.get_docstring(node):
                    observations.append(f"Class '{node.name}' has no docstring.")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    observations.append(
                        "Bare except clause detected: catches SystemExit and KeyboardInterrupt; "
                        "prefer 'except Exception:'."
                    )
            elif isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
                    # Check if break exists inside body
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        observations.append(
                            "Loop 'while True:' has no immediate break statement; "
                            "verify termination conditions."
                        )

    except SyntaxError as exc:
        is_valid = False
        err_msg = exc.msg
        err_line = exc.lineno
        err_col = exc.offset
        observations.append(f"SyntaxError on line {exc.lineno}, column {exc.offset}: {exc.msg}")

    # Deduplicate imports and functions while preserving order
    dedup_funcs = list(dict.fromkeys(functions))
    dedup_classes = list(dict.fromkeys(classes))
    dedup_imports = list(dict.fromkeys(imports))
    dedup_obs = list(dict.fromkeys(observations))

    return CodeAnalysisResult(
        language="python",
        is_valid_syntax=is_valid,
        error_message=err_msg,
        error_line=err_line,
        error_column=err_col,
        functions=dedup_funcs,
        classes=dedup_classes,
        imports=dedup_imports,
        line_count=line_count,
        char_count=char_count,
        observations=dedup_obs,
    )


def analyze_generic_code(code: str, language: str) -> CodeAnalysisResult:
    """Safe, conservative structural analysis for non-Python languages using regex.

    Never executes user-supplied code or shell commands.
    """
    lines = code.splitlines()
    line_count = len(lines)
    char_count = len(code)

    observations: list[str] = []
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []

    # Check parentheses and brace balance
    open_curly = code.count("{")
    close_curly = code.count("}")
    if open_curly != close_curly:
        observations.append(
            f"Unbalanced braces: {open_curly} open ('{{') vs {close_curly} closed ('}}')."
        )

    open_paren = code.count("(")
    close_paren = code.count(")")
    if open_paren != close_paren:
        observations.append(
            f"Unbalanced parentheses: {open_paren} open ('(') vs {close_paren} closed (')')."
        )

    # Generic function signature pattern: fn/func/function/def/type name(...)
    func_pattern = re.compile(
        r"\b(?:function|func|fn|def|public\s+\w+|private\s+\w+)\s+([a-zA-Z_]\w*)\s*\(",
        re.MULTILINE,
    )
    for match in func_pattern.finditer(code):
        fn_name = match.group(1)
        if fn_name not in ("if", "for", "while", "switch", "catch"):
            functions.append(fn_name)

    # Generic class/struct pattern
    class_pattern = re.compile(
        r"\b(?:class|struct|interface|trait|type)\s+([a-zA-Z_]\w*)\b",
        re.MULTILINE,
    )
    for match in class_pattern.finditer(code):
        classes.append(match.group(1))

    # Generic import/include pattern
    import_pattern = re.compile(
        r"^(?:import|using|#include|require|from)\s+([^\n;]+)",
        re.MULTILINE,
    )
    for match in import_pattern.finditer(code):
        imports.append(match.group(1).strip().strip("<>\"'"))

    dedup_funcs = list(dict.fromkeys(functions))
    dedup_classes = list(dict.fromkeys(classes))
    dedup_imports = list(dict.fromkeys(imports))

    is_syntax_valid = open_curly == close_curly and open_paren == close_paren

    return CodeAnalysisResult(
        language=language,
        is_valid_syntax=is_syntax_valid if (open_curly > 0 or open_paren > 0) else None,
        error_message="Unbalanced delimiters detected" if not is_syntax_valid else None,
        functions=dedup_funcs,
        classes=dedup_classes,
        imports=dedup_imports,
        line_count=line_count,
        char_count=char_count,
        observations=observations,
    )


def analyze_code_snippet(code: str, language: str = "python") -> CodeAnalysisResult:
    """Dispatch safe local static analysis based on language.

    Never executes, imports, or evaluates arbitrary user-supplied code.
    """
    clean_code = code.strip()
    if not clean_code:
        return CodeAnalysisResult(
            language=language,
            is_valid_syntax=True,
            line_count=0,
            char_count=0,
            observations=["No code supplied to analyze."],
        )

    norm_lang = language.strip().lower()
    if norm_lang in ("python", "py"):
        return analyze_python_code(clean_code)

    return analyze_generic_code(clean_code, language=norm_lang)
