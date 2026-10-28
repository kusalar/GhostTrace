"""Tests for MemoryRepository CRUD, limits, and export/import."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.repository import MemoryRepository
from ghosttrace.memory.schemas import MemoryCategory, MemorySource


def test_memory_repository_crud(tmp_path: Path) -> None:
    """Test creating, reading, updating, deleting memories."""
    db_mgr = DatabaseManager(tmp_path / "repo.db")
    apply_migrations(db_mgr)
    settings = Settings(memory_max_items=50, memory_max_content_chars=500)
    repo = MemoryRepository(db_mgr, settings)

    # Create memory
    item = repo.create_memory(
        category=MemoryCategory.USER_PREFERENCE,
        content="Prefer dark green terminal theme.",
        source=MemorySource.EXPLICIT_USER,
        importance=4.5,
    )
    assert item.id > 0
    assert item.category == MemoryCategory.USER_PREFERENCE
    assert item.importance == 4.5

    # Retrieve memory
    fetched = repo.get_memory_by_id(item.id)
    assert fetched is not None
    assert fetched.content == "Prefer dark green terminal theme."

    # Update memory
    updated = repo.update_memory(
        item.id,
        content="Prefer high-contrast dark green terminal theme.",
        importance=5.0,
    )
    assert updated is not None
    assert updated.content == "Prefer high-contrast dark green terminal theme."
    assert updated.importance == 5.0

    # List memories
    items = repo.list_memories()
    assert len(items) == 1
    assert items[0].id == item.id

    # Filter by category
    assert len(repo.list_memories(category=MemoryCategory.USER_PREFERENCE)) == 1
    assert len(repo.list_memories(category=MemoryCategory.LEARNING)) == 0

    # Delete memory
    assert repo.delete_memory(item.id) is True
    assert repo.get_memory_by_id(item.id) is None
    assert repo.delete_memory(item.id) is False

    db_mgr.close()


def test_memory_auto_redaction_and_bounding(tmp_path: Path) -> None:
    """Ensure sensitive data is redacted and long contents are bounded."""
    db_mgr = DatabaseManager(tmp_path / "bound.db")
    apply_migrations(db_mgr)
    repo = MemoryRepository(db_mgr, max_memories=50, max_content_chars=50)

    # Content with secret
    secret_text = "My secret token is ghp_1234567890abcdef1234567890abcdef123456."
    item = repo.create_memory(
        category=MemoryCategory.USER_PROFILE,
        content=secret_text,
    )
    assert "ghp_" not in item.content
    assert "[REDACTED:GITHUB_TOKEN]" in item.content

    # Content exceeding max_content_chars
    long_text = "A" * 200
    item2 = repo.create_memory(
        category=MemoryCategory.GENERAL,
        content=long_text,
    )
    assert len(item2.content) <= 50

    db_mgr.close()


def test_memory_export_import(tmp_path: Path) -> None:
    """Ensure memories can be exported to and imported from dict lists."""
    db_mgr = DatabaseManager(tmp_path / "exp_imp.db")
    apply_migrations(db_mgr)
    settings = Settings(memory_max_items=50)
    repo = MemoryRepository(db_mgr, settings)

    repo.create_memory(category=MemoryCategory.WORKFLOW, content="Step 1: run tests")
    repo.create_memory(category=MemoryCategory.WORKFLOW, content="Step 2: build package")

    records = repo.export_memories()
    assert len(records) == 2

    # Clear memories
    cleared = repo.clear_memories()
    assert cleared == 2
    assert repo.get_memory_count() == 0

    # Import back
    imported, skipped = repo.import_memories(records)
    assert imported == 2
    assert skipped == 0
    assert repo.get_memory_count() == 2

    db_mgr.close()
