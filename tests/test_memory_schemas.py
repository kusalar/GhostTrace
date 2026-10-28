"""Tests for memory subsystem data schemas and models."""

from __future__ import annotations

from ghosttrace.memory.schemas import (
    ConversationRecord,
    InjectedContext,
    MemoryCategory,
    MemoryItem,
    MemorySearchResult,
    MemorySource,
    MemoryStatus,
    MessageRecord,
    ProjectFileRecord,
    ProjectFileSearchResult,
    ProjectRecord,
)


def test_memory_category_and_source_enums() -> None:
    """Verify that category and source enums contain expected members and str behavior."""
    assert MemoryCategory.USER_PREFERENCE.value == "USER_PREFERENCE"
    assert MemoryCategory.TECHNICAL_DECISION.value == "TECHNICAL_DECISION"
    assert MemoryCategory.GENERAL.value == "GENERAL"

    assert MemorySource.USER_EXPLICIT.value == "USER_EXPLICIT"
    assert MemorySource.SYSTEM_INFERRED.value == "SYSTEM_INFERRED"


def test_memory_item_creation() -> None:
    """Verify MemoryItem serialization and attributes."""
    item = MemoryItem(
        id=1,
        category=MemoryCategory.USER_PREFERENCE,
        content="Prefer pytest over unittest.",
        source=MemorySource.EXPLICIT_USER,
        importance=4.0,
        created_at=1730100000.0,
        updated_at=1730100000.0,
    )
    assert item.id == 1
    assert item.category == MemoryCategory.USER_PREFERENCE
    assert item.importance == 4.0
    data = item.to_dict()
    assert data["id"] == 1
    assert data["category"] == "USER_PREFERENCE"

    restored = MemoryItem.from_dict(data)
    assert restored.content == item.content
    assert restored.category == item.category


def test_conversation_and_message_records() -> None:
    """Verify ConversationRecord and MessageRecord models."""
    conv = ConversationRecord(
        id=42,
        session_id="sess_123",
        title="Debug Session",
        created_at=1730100000.0,
        updated_at=1730101800.0,
    )
    assert conv.id == 42
    assert conv.session_id == "sess_123"

    msg = MessageRecord(
        id=101,
        conversation_id=42,
        role="user",
        content="Hello GhostTrace",
        created_at=1730100060.0,
    )
    assert msg.role == "user"
    assert msg.conversation_id == 42


def test_project_and_project_file_records() -> None:
    """Verify ProjectRecord and ProjectFileRecord models."""
    proj = ProjectRecord(
        id=5,
        name="GhostTrace",
        root_path="D:/GhostTrace",
        created_at=1730100000.0,
        updated_at=1730100000.0,
        last_indexed_at=None,
        enabled=True,
    )
    assert proj.name == "GhostTrace"
    assert proj.enabled is True

    pfile = ProjectFileRecord(
        id=1,
        project_id=5,
        relative_path="src/main.py",
        content_hash="abc123hash",
        language="Python",
        content="print('hello')",
        indexed_at=1730100300.0,
    )
    assert pfile.language == "Python"
    assert pfile.content_hash == "abc123hash"


def test_search_results_and_status() -> None:
    """Verify search result wrappers and MemoryStatus model."""
    item = MemoryItem(
        id=1,
        category=MemoryCategory.LEARNING,
        content="Use WAL mode for sqlite concurrency.",
        source=MemorySource.EXPLICIT_USER,
        importance=5.0,
        created_at=1730100000.0,
        updated_at=1730100000.0,
    )
    res = MemorySearchResult(memory=item, score=0.95, snippet="...WAL mode...")
    assert res.score == 0.95
    assert res.snippet == "...WAL mode..."

    pf = ProjectFileRecord(
        id=1,
        project_id=1,
        relative_path="db.py",
        content_hash="hash1",
        language="Python",
        content="pragma journal_mode=WAL",
        indexed_at=1730100000.0,
    )
    pf_res = ProjectFileSearchResult(file=pf, score=0.88, snippet="...WAL...")
    assert pf_res.score == 0.88
    assert pf_res.file_record.id == 1

    ctx = InjectedContext(
        formatted_memory_context="[Memory: WAL mode]",
        formatted_project_context="[Project: db.py]",
        total_chars=40,
    )
    assert ctx.total_chars == 40

    status = MemoryStatus(
        is_enabled=True,
        database_path="mem.db",
        database_size_bytes=4096,
        wal_mode=True,
        fts5_available=True,
        total_memories=10,
        total_conversations=2,
        total_messages=15,
        total_projects=1,
        total_project_files=5,
        active_project=None,
        max_items=500,
        max_context_chars=1500,
    )
    assert status.total_memories == 10
    assert status.wal_mode is True
