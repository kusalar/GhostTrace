"""Tests for conversation and message persistence."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.conversation import ConversationPersistenceManager
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations


def test_conversation_persistence(tmp_path: Path) -> None:
    """Ensure sessions, user and assistant messages are correctly persisted."""
    db_mgr = DatabaseManager(tmp_path / "conv.db")
    apply_migrations(db_mgr)
    settings = Settings(
        memory_persist_conversations=True,
        memory_max_messages=100,
    )
    conv_mgr = ConversationPersistenceManager(db_mgr, settings)

    session_id = "test_session_42"
    conv = conv_mgr.get_or_create_conversation(session_id, title="Test Session")
    assert conv.session_id == session_id

    # Add messages
    m1 = conv_mgr.add_message(session_id, role="user", content="How do I use pytest?")
    assert m1 is not None
    assert m1.role == "user"

    m2 = conv_mgr.add_message(
        session_id,
        role="assistant",
        content="Run pytest using 'pytest tests/'.",
    )
    assert m2 is not None
    assert m2.role == "assistant"

    messages = conv_mgr.get_conversation_messages(session_id)
    assert len(messages) == 2
    assert messages[0].content == "How do I use pytest?"
    assert messages[1].content == "Run pytest using 'pytest tests/'."

    assert conv_mgr.get_total_conversations() == 1
    assert conv_mgr.get_total_messages() == 2

    db_mgr.close()
