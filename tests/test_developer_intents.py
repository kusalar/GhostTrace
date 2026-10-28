"""Unit tests for developer intent classification."""

from __future__ import annotations

import pytest
from ghosttrace.developer.intents import classify_developer_intent
from ghosttrace.developer.schemas import DeveloperIntent


@pytest.mark.parametrize(
    ("query", "code", "expected"),
    [
        ("Explain this Python function to me", "def foo(): pass", DeveloperIntent.EXPLAIN_CODE),
        ("How does this algorithm work?", None, DeveloperIntent.EXPLAIN_CODE),
        ("What does this code do step by step?", None, DeveloperIntent.EXPLAIN_CODE),
        ("Walk me through this method", None, DeveloperIntent.EXPLAIN_CODE),
        ("Debug this error: IndexError list index out of range", None, DeveloperIntent.DEBUG_CODE),
        ("Fix this broken code: segfault occurs on line 12", None, DeveloperIntent.DEBUG_CODE),
        ("Why does this fail when running async?", None, DeveloperIntent.DEBUG_CODE),
        (
            "Traceback (most recent call last):\n  File 'a.py', line 1",
            None,
            DeveloperIntent.DEBUG_CODE,
        ),
        ("Review this code for security issues", "def query(): pass", DeveloperIntent.REVIEW_CODE),
        ("Please perform a code review on this snippet", None, DeveloperIntent.REVIEW_CODE),
        ("Find bugs and code smells in this function", None, DeveloperIntent.REVIEW_CODE),
        ("Generate a Python CLI script for file hashing", None, DeveloperIntent.GENERATE_CODE),
        ("Write a function to calculate Fibonacci numbers", None, DeveloperIntent.GENERATE_CODE),
        ("Create a class representing a binary search tree", None, DeveloperIntent.GENERATE_CODE),
        ("Implement a rate limiter in Go", None, DeveloperIntent.GENERATE_CODE),
        (
            "Refactor this messy function to improve readability",
            None,
            DeveloperIntent.REFACTOR_CODE,
        ),
        ("Simplify this complex nested loop", None, DeveloperIntent.REFACTOR_CODE),
        ("Reduce duplication in this class", None, DeveloperIntent.REFACTOR_CODE),
        ("Write pytest unit tests for this function", None, DeveloperIntent.GENERATE_TESTS),
        ("Generate test cases for boundary conditions", None, DeveloperIntent.GENERATE_TESTS),
        ("Create a test suite using unittest", None, DeveloperIntent.GENERATE_TESTS),
        ("Optimize this function to reduce time complexity", None, DeveloperIntent.OPTIMIZE_CODE),
        ("Make this faster and reduce memory footprint", None, DeveloperIntent.OPTIMIZE_CODE),
        (
            "Explain the concept of recursion vs iteration",
            None,
            DeveloperIntent.GENERAL_PROGRAMMING,
        ),
        (
            "How does database indexing work under the hood?",
            None,
            DeveloperIntent.GENERAL_PROGRAMMING,
        ),
        (
            "What is polymorphism in object oriented design?",
            None,
            DeveloperIntent.GENERAL_PROGRAMMING,
        ),
        ("", "def foo(): pass", DeveloperIntent.EXPLAIN_CODE),
        ("   ", None, DeveloperIntent.UNKNOWN),
        ("Tell me a fictional ghost story", None, DeveloperIntent.UNKNOWN),
        ("What is the weather outside?", None, DeveloperIntent.UNKNOWN),
        ("ai status", None, DeveloperIntent.UNKNOWN),
        ("ghost set phantom-coder", None, DeveloperIntent.UNKNOWN),
        ("help dev", None, DeveloperIntent.UNKNOWN),
        ("status", None, DeveloperIntent.UNKNOWN),
        ("clear", None, DeveloperIntent.UNKNOWN),
        ("exit", None, DeveloperIntent.UNKNOWN),
    ],
)
def test_classify_developer_intent(
    query: str,
    code: str | None,
    expected: DeveloperIntent,
) -> None:
    assert classify_developer_intent(query, code=code) == expected
