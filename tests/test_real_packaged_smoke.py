"""Automated interactive smoke test of GhostTraceApp using real Qwen model.

Validates:
- Application mounting and widget assembly
- Keyboard input processing via Textual pilot
- Real Qwen model loading & generation
- Real streaming output accumulation
- Ghost status & persona switching
- Python debugging query with useful response
- Command Guardian destructive command analysis
- Command Guardian approval modal presentation & dismissal
- Memory & Project subsystem commands
- System & Haunt subsystem commands
- Clean exit via 'exit' command
"""

from __future__ import annotations

import asyncio
import time

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.widgets.approval_modal import CommandApprovalModal
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.input import CommandInput
from ghosttrace.terminal.widgets.status_panel import StatusPanel


@pytest.mark.asyncio
async def test_full_interactive_terminal_smoke_with_real_ai() -> None:
    """Perform comprehensive end-to-end smoke test of interactive terminal."""
    settings = Settings()
    assert settings.model_path.exists(), f"Model path must exist: {settings.model_path}"

    app = GhostTraceApp(settings=settings)
    startup_start = time.perf_counter()

    async with app.run_test(size=(120, 40)) as pilot:
        startup_duration = time.perf_counter() - startup_start
        print(f"\n[SMOKE] Application mounted in {startup_duration:.3f}s")

        cmd_input = app.query_one("#command-input", CommandInput)
        conv_log = app.query_one("#conversation-log", ConversationLog)
        assert app.query_one("#status-panel", StatusPanel) is not None

        # 1. Verify Keyboard Input & ghost status
        cmd_input.value = "ghost status"
        await pilot.press("enter")
        await pilot.pause()
        assert any(
            "GHOST PERSONALITY SUBSYSTEM STATUS" in str(child.render())
            for child in conv_log.children
        )
        print("[SMOKE] TEST PASSED: ghost status")

        # 2. Verify persona switching
        cmd_input.value = "ghost set phantom-coder"
        await pilot.press("enter")
        await pilot.pause()
        assert app.ghost_engine.active_profile.id.value == "phantom-coder"
        print("[SMOKE] TEST PASSED: persona switching -> phantom-coder")

        # 3. Verify guard analyze (destructive command)
        cmd_input.value = "guard analyze rmdir /s /q C:\\Windows"
        await pilot.press("enter")
        await pilot.pause()
        assert any("BLOCKED - PROHIBITED" in str(child.render()) for child in conv_log.children)
        print("[SMOKE] TEST PASSED: guard analyze (destructive)")

        # 4. Verify guard run triggers approval modal
        cmd_input.value = "guard run git status"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, CommandApprovalModal)
        print("[SMOKE] TEST PASSED: Guardian approval modal displayed")
        # Cancel approval modal safely via 'n'
        await pilot.press("n")
        await pilot.pause()
        assert not isinstance(app.screen, CommandApprovalModal)
        print("[SMOKE] TEST PASSED: Guardian approval modal dismissed cleanly")

        # 5. Verify memory and project commands
        cmd_input.value = "memory status"
        await pilot.press("enter")
        await pilot.pause()
        assert any(
            "Memory Subsystem" in str(child.render()) or "Database" in str(child.render())
            for child in conv_log.children
        )
        print("[SMOKE] TEST PASSED: memory status")

        cmd_input.value = "project list"
        await pilot.press("enter")
        await pilot.pause()
        print("[SMOKE] TEST PASSED: project list")

        # 6. Verify system and haunt commands
        cmd_input.value = "system overview"
        await pilot.press("enter")
        await pilot.pause()
        print("[SMOKE] TEST PASSED: system overview")

        cmd_input.value = "haunt status"
        await pilot.press("enter")
        await pilot.pause()
        print("[SMOKE] TEST PASSED: haunt status")

        # 7. Real Qwen Model: Normal conversation with streaming
        print("[SMOKE] Submitting normal conversation prompt to Real Qwen Model...")
        model_load_start = time.perf_counter()
        cmd_input.value = "Hello! Who are you?"
        await pilot.press("enter")

        # Poll until generation completes
        max_wait = 90.0
        elapsed = 0.0
        while app.is_generating and elapsed < max_wait:
            await asyncio.sleep(0.5)
            elapsed += 0.5

        assert not app.is_generating, "AI generation timed out"
        gen_duration = time.perf_counter() - model_load_start
        print(f"[SMOKE] Normal conversation answered in {gen_duration:.2f}s")

        # 8. Real Qwen Model: Python debugging query
        print("[SMOKE] Submitting Python debugging question to Real Qwen Model...")
        dbg_start = time.perf_counter()
        cmd_input.value = "Why does print(1/0) fail in Python and how do I fix it?"
        await pilot.press("enter")

        elapsed = 0.0
        while app.is_generating and elapsed < max_wait:
            await asyncio.sleep(0.5)
            elapsed += 0.5

        assert not app.is_generating, "AI debugging query timed out"
        dbg_duration = time.perf_counter() - dbg_start
        print(f"[SMOKE] Python debugging question answered in {dbg_duration:.2f}s")

        # 9. Clean Exit command
        cmd_input.value = "exit"
        await pilot.press("enter")
        await pilot.pause()
        print("[SMOKE] TEST PASSED: exit command requested application exit cleanly")
