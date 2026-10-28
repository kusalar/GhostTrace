"""Integration tests verifying interactive terminal behavior and safety invariants."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.schemas import AIStatus, ModelStatus
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.haunt.schemas import HauntMode, TriggerContext, TriggerType
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.widgets.conversation import ConversationLog


@pytest.fixture
def mock_ai_engine() -> MagicMock:
    """Return a mock AI engine that streams a predictable token sequence."""
    ai = MagicMock(spec=AIEngine)
    ai.get_status.return_value = AIStatus(
        runtime_available=True,
        runtime_version="0.3.7",
        model_status=ModelStatus.READY,
        model_path=Path("models/test.gguf"),
        model_exists=True,
        is_loaded=True,
        is_busy=False,
        history_count=0,
        context_size=2048,
        max_tokens=512,
        threads=2,
        gpu_layers=0,
    )
    ai.ask_stream.return_value = ["def ", "hello():\n", "    return 'world'"]
    return ai


@pytest.mark.asyncio
async def test_app_haunted_mode_session_start_and_ai_query(mock_ai_engine: MagicMock) -> None:
    """Verify app mount in HAUNTED mode generates atmospheric greeting and coding reaction."""
    settings = Settings(
        haunt_enabled=True,
        haunt_mode="haunted",
        haunt_cooldown_seconds=5.0,
    )
    ghost = GhostEngine(settings)
    haunt = HauntEngine(settings, ghost_engine=ghost)
    haunt.set_mode(HauntMode.HAUNTED)

    app = GhostTraceApp(
        settings=settings,
        ai_engine=mock_ai_engine,
        ghost_engine=ghost,
        haunt_engine=haunt,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.query_one("#conversation-log", ConversationLog) is not None
        # Mounting in HAUNTED mode fired SESSION_START
        assert haunt.history.count >= 1

        # Reset cooldown so subsequent coding trigger can fire
        haunt.scheduler.reset()

        # Submit natural language query
        cmd_input = app.query_one("#command-input")
        cmd_input.value = "write a hello function"
        await pilot.press("enter")
        await pilot.pause(0.2)

        # AI query completed, firing CODING_SUCCESS
        assert haunt.history.count >= 2


@pytest.mark.asyncio
async def test_app_mode_switching_preserves_state(mock_ai_engine: MagicMock) -> None:
    """Verify switching experience modes at runtime is instantaneous and preserves state."""
    settings = Settings(haunt_enabled=True, haunt_mode="normal")
    ghost = GhostEngine(settings)
    haunt = HauntEngine(settings, ghost_engine=ghost)

    app = GhostTraceApp(
        settings=settings,
        ai_engine=mock_ai_engine,
        ghost_engine=ghost,
        haunt_engine=haunt,
    )

    async with app.run_test() as pilot:
        await pilot.pause()

        # In NORMAL mode, session start was suppressed
        assert haunt.history.count == 0

        # Switch to HAUNTED via command
        app.registry.execute("haunt mode haunted", app.context)
        assert haunt.mode == HauntMode.HAUNTED

        # Preview event works immediately
        prev_res = haunt.preview_event()
        assert prev_res.fired is True

        # Switch to FOCUS mode
        app.registry.execute("haunt mode focus", app.context)
        assert haunt.mode == HauntMode.FOCUS


def test_atmospheric_events_never_saved_as_memories(tmp_path: Path) -> None:
    """Verify that haunt events are strictly session-only and never written to SQLite memories."""
    db_path = tmp_path / "test.db"
    db_mgr = DatabaseManager(db_path)
    apply_migrations(db_mgr)

    settings = Settings(
        haunt_enabled=True,
        haunt_mode="haunted",
        memory_database_path=str(db_path),
    )
    ghost = GhostEngine(settings)
    haunt = HauntEngine(settings, ghost_engine=ghost)
    mem_engine = MemoryEngine(settings)

    # Process atmospheric trigger
    haunt.process_trigger(TriggerContext(trigger_type=TriggerType.SESSION_START))
    assert haunt.history.count == 1

    # Check database tables
    memories = mem_engine.list_memories()
    assert len(memories) == 0  # Zero memories created by haunt events
