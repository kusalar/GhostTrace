"""Tests for MemoryEngine facade coordinating memory, projects, and context."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.memory.schemas import MemoryCategory


def test_memory_engine_facade(tmp_path: Path) -> None:
    """Ensure MemoryEngine provides seamless interface across all memory capabilities."""
    db_file = tmp_path / "facade.db"
    settings = Settings(memory_database_path=db_file)
    engine = MemoryEngine(settings)

    # Status check
    status = engine.get_status()
    assert status.is_enabled is True
    assert status.total_memories == 0

    # Save memory
    item = engine.save_memory(
        category=MemoryCategory.USER_PROFILE,
        content="Developer working on Windows 10.",
        importance=8,
    )
    assert item.id > 0

    # List memories
    items = engine.list_memories()
    assert len(items) == 1

    # Search memories
    hits = engine.search_memories("Windows")
    assert len(hits) == 1
    assert hits[0].memory.id == item.id

    # Update memory
    updated = engine.update_memory(item.id, content="Developer on Windows 11.")
    assert updated is not None
    assert updated.content == "Developer on Windows 11."

    # Project management
    proj_dir = tmp_path / "facade_proj"
    proj_dir.mkdir()
    (proj_dir / "index.html").write_text("<h1>Test</h1>", encoding="utf-8")

    proj = engine.add_project(proj_dir, name="FacadeProj")
    assert proj.name == "FacadeProj"

    active = engine.set_active_project(proj.name)
    assert active.id == proj.id

    scan_res = engine.scan_project(proj.name)
    assert scan_res.indexed_files == 1

    # Injected context
    injected = engine.build_context("test")
    assert injected.total_chars > 0

    # Conversation persistence
    engine.persist_user_message("sess_1", "Hello")
    engine.persist_assistant_message("sess_1", "Greetings")
    messages = engine.get_session_messages("sess_1")
    assert len(messages) == 2

    engine.close()
