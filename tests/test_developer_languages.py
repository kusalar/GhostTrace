"""Unit tests for language detection and metadata registry."""

from __future__ import annotations

import pytest
from ghosttrace.developer.languages import (
    detect_language,
    get_language,
    list_supported_languages,
)


def test_list_supported_languages() -> None:
    languages = list_supported_languages()
    assert len(languages) >= 15
    ids = {lang.id for lang in languages}
    expected_ids = {
        "python",
        "javascript",
        "typescript",
        "java",
        "c",
        "cpp",
        "csharp",
        "go",
        "rust",
        "php",
        "html",
        "css",
        "sql",
        "bash",
        "powershell",
    }
    assert expected_ids.issubset(ids)


@pytest.mark.parametrize(
    ("alias", "expected_id"),
    [
        ("python", "python"),
        ("py", "python"),
        ("python3", "python"),
        (".py", "python"),
        ("js", "javascript"),
        ("javascript", "javascript"),
        (".js", "javascript"),
        ("ts", "typescript"),
        ("typescript", "typescript"),
        (".ts", "typescript"),
        ("java", "java"),
        (".java", "java"),
        ("c", "c"),
        (".c", "c"),
        ("cpp", "cpp"),
        ("c++", "cpp"),
        (".cpp", "cpp"),
        ("csharp", "csharp"),
        ("c#", "csharp"),
        (".cs", "csharp"),
        ("go", "go"),
        ("golang", "go"),
        (".go", "go"),
        ("rust", "rust"),
        ("rs", "rust"),
        (".rs", "rust"),
        ("php", "php"),
        (".php", "php"),
        ("html", "html"),
        ("htm", "html"),
        ("css", "css"),
        ("sql", "sql"),
        ("bash", "bash"),
        ("sh", "bash"),
        ("powershell", "powershell"),
        ("ps1", "powershell"),
        ("pwsh", "powershell"),
    ],
)
def test_get_language_aliases(alias: str, expected_id: str) -> None:
    lang = get_language(alias)
    assert lang is not None
    assert lang.id == expected_id


def test_detect_language_by_hint() -> None:
    detected = detect_language(code="x = 10", hint="python")
    assert detected is not None
    assert detected.id == "python"

    detected_rs = detect_language(code="let x = 10;", hint="rs")
    assert detected_rs is not None
    assert detected_rs.id == "rust"


def test_detect_language_by_code_fence() -> None:
    query = "Look at this code:\n```typescript\ninterface User { id: number; }\n```"
    detected = detect_language(query=query)
    assert detected is not None
    assert detected.id == "typescript"


def test_detect_language_by_extension_in_query() -> None:
    query = "Check this file main.go for race conditions"
    detected = detect_language(query=query)
    assert detected is not None
    assert detected.id == "go"


@pytest.mark.parametrize(
    ("code", "expected_id"),
    [
        ("def calculate_sum(a: int, b: int) -> int:\n    return a + b", "python"),
        ('fn main() {\n    println!("Hello, world!");\n}', "rust"),
        ("func ProcessItems(items []string) error {\n    return nil\n}", "go"),
        ("public class OrderService {\n    public static void main(String[] args) {}\n}", "java"),
        ("using System;\nclass Program {\n    static void Main() {}\n}", "csharp"),
        ("#include <iostream>\nint main() {\n    std::cout << 42;\n}", "cpp"),
        ('#include <stdio.h>\nint main() {\n    printf("hi");\n}', "c"),
        ("SELECT id, name FROM users WHERE active = 1;", "sql"),
        ("#!/bin/bash\necho 'deploying application'", "bash"),
        ("$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path", "powershell"),
        ("<?php\n$user = $_GET['user'];\necho $user;", "php"),
        ("<!DOCTYPE html>\n<html><body><h1>Test</h1></body></html>", "html"),
        ("div.container {\n    display: flex;\n    margin: 0 auto;\n}", "css"),
    ],
)
def test_detect_language_by_syntax_patterns(code: str, expected_id: str) -> None:
    detected = detect_language(code=code)
    assert detected is not None
    assert detected.id == expected_id


def test_detect_language_unknown() -> None:
    detected = detect_language(code="12345 67890", query="hello world")
    assert detected is None
