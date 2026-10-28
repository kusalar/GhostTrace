"""Tests for memory retrieval, FTS5/LIKE search, and bounding."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.repository import MemoryRepository
from ghosttrace.memory.retrieval import MemoryRetriever
from ghosttrace.memory.schemas import MemoryCategory


def test_memory_retrieval_and_search(tmp_path: Path) -> None:
    """Ensure relevant memories are retrieved by query keywords."""
    db_mgr = DatabaseManager(tmp_path / "search.db")
    apply_migrations(db_mgr)
    settings = Settings(
        memory_max_retrieved=3,
        memory_max_context_chars=1000,
    )
    repo = MemoryRepository(db_mgr, settings)
    retriever = MemoryRetriever(db_mgr, repo, settings)

    repo.create_memory(
        category=MemoryCategory.USER_PREFERENCE,
        content="User prefers Python 3.11 with Ruff linter and strict type hints.",
        importance=4.5,
    )
    repo.create_memory(
        category=MemoryCategory.TECHNICAL_DECISION,
        content="GhostTrace uses SQLite WAL mode for local database persistence.",
        importance=4.0,
    )
    repo.create_memory(
        category=MemoryCategory.GENERAL,
        content="Intel Core i3-1115G4 is the primary target CPU benchmark.",
        importance=3.0,
    )

    # Search for SQLite
    results = retriever.search_memories("SQLite", limit=5)
    assert len(results) >= 1
    assert any("SQLite" in r.memory.content for r in results)

    # Relevant retrieval for prompt
    relevant = retriever.retrieve_relevant("How is SQLite configured in GhostTrace?")
    assert len(relevant) >= 1
    assert any("SQLite" in item.content for item in relevant)

    db_mgr.close()
