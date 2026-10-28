"""Unit tests for safe local static code analysis without execution."""

from __future__ import annotations

from ghosttrace.developer.code_analysis import (
    analyze_code_snippet,
    analyze_generic_code,
    analyze_python_code,
)


def test_analyze_python_code_valid() -> None:
    code = (
        "import os\n"
        "from pathlib import Path\n\n"
        "class FileManager:\n"
        '    """Manages files."""\n'
        "    def read_file(self, path: Path) -> str:\n"
        '        """Read file text."""\n'
        "        return path.read_text()\n\n"
        "def helper():\n"
        "    pass\n"
    )
    result = analyze_python_code(code)
    assert result.language == "python"
    assert result.is_valid_syntax is True
    assert result.error_message is None
    assert "read_file" in result.functions
    assert "helper" in result.functions
    assert "FileManager" in result.classes
    assert "os" in result.imports
    assert "pathlib.Path" in result.imports
    assert result.line_count > 0
    assert result.char_count > 0
    # Function helper has no docstring observation
    assert any("Function 'helper' has no docstring" in obs for obs in result.observations)


def test_analyze_python_code_syntax_error() -> None:
    malformed_code = "def broken(\n    return 42"
    result = analyze_python_code(malformed_code)
    assert result.is_valid_syntax is False
    assert result.error_message is not None
    assert result.error_line is not None
    assert any("SyntaxError" in obs for obs in result.observations)


def test_analyze_python_code_bare_except_and_infinite_loop() -> None:
    code = (
        "def risky():\n"
        "    try:\n"
        "        do_something()\n"
        "    except:\n"
        "        pass\n\n"
        "def loop():\n"
        "    while True:\n"
        "        do_work()\n"
    )
    result = analyze_python_code(code)
    assert result.is_valid_syntax is True
    assert any("Bare except clause detected" in obs for obs in result.observations)
    assert any("has no immediate break statement" in obs for obs in result.observations)


def test_analyze_generic_code_balanced_and_unbalanced() -> None:
    clean_js = "function calculate(x) {\n  return x * 2;\n}"
    res_clean = analyze_generic_code(clean_js, language="javascript")
    assert res_clean.is_valid_syntax is True
    assert "calculate" in res_clean.functions
    assert not res_clean.observations

    broken_js = "function calculate(x) {\n  return x * 2;\n"
    res_broken = analyze_generic_code(broken_js, language="javascript")
    assert res_broken.is_valid_syntax is False
    assert any("Unbalanced braces" in obs for obs in res_broken.observations)


def test_analyze_code_snippet_dispatch_and_empty() -> None:
    empty_res = analyze_code_snippet("")
    assert empty_res.line_count == 0
    assert empty_res.char_count == 0

    py_res = analyze_code_snippet("def add(a, b): return a + b", language="python")
    assert py_res.language == "python"
    assert "add" in py_res.functions

    go_res = analyze_code_snippet("func Run() {}", language="go")
    assert go_res.language == "go"
    assert "Run" in go_res.functions
