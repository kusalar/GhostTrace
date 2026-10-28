"""Tests for terminal memory and project commands."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.terminal.command_registry import CommandContext, CommandRegistry
from ghosttrace.terminal.commands import handle_memory, handle_project
from ghosttrace.terminal.history import SessionHistory


def test_terminal_memory_commands(tmp_path: Path) -> None:
    """Test memory subcommands: status, help, save, list, show, edit, search, stats, clear."""
    db_file = tmp_path / "term_mem.db"
    settings = Settings(memory_database_path=db_file)
    engine = MemoryEngine(settings)
    ctx = CommandContext(
        settings=settings,
        history=SessionHistory(),
        memory_engine=engine,
    )

    # memory help
    res_help = handle_memory(["help"], ctx)
    assert res_help.success is True
    assert "MEMORY SUBSYSTEM COMMANDS" in str(res_help.output)

    # memory status
    res_status = handle_memory(["status"], ctx)
    assert res_status.success is True
    assert "PERSISTENT MEMORY STATUS" in str(res_status.output)

    # memory save
    res_save = handle_memory(
        ["save", "USER_PREFERENCE", "I prefer using dark mode in terminal."],
        ctx,
    )
    assert res_save.success is True
    assert "saved in category" in str(res_save.output)

    # memory list
    res_list = handle_memory(["list"], ctx)
    assert res_list.success is True

    # memory search
    res_search = handle_memory(["search", "dark mode"], ctx)
    assert res_search.success is True

    # memory show
    res_show = handle_memory(["show", "1"], ctx)
    assert res_show.success is True
    assert "MEMORY ITEM #1" in str(res_show.output)

    # memory edit
    res_edit = handle_memory(["edit", "1", "I prefer using high contrast dark mode."], ctx)
    assert res_edit.success is True

    # memory stats
    res_stats = handle_memory(["stats"], ctx)
    assert res_stats.success is True
    assert "MEMORY SUBSYSTEM STATISTICS" in str(res_stats.output)

    # memory export & import
    exp_file = tmp_path / "export.json"
    res_exp = handle_memory(["export", str(exp_file)], ctx)
    assert res_exp.success is True

    # memory clear without force
    res_clear_noforce = handle_memory(["clear"], ctx)
    assert res_clear_noforce.success is False

    # memory clear with force
    res_clear = handle_memory(["clear", "--force"], ctx)
    assert res_clear.success is True

    # memory import
    res_imp = handle_memory(["import", str(exp_file)], ctx)
    assert res_imp.success is True

    # memory delete
    mems = engine.list_memories()
    assert len(mems) == 1
    res_del = handle_memory(["delete", str(mems[0].id)], ctx)
    assert res_del.success is True

    engine.close()


def test_terminal_project_commands(tmp_path: Path) -> None:
    """Test project subcommands: help, status, add, list, use, info, scan, refresh, clear."""
    db_file = tmp_path / "term_proj.db"
    settings = Settings(memory_database_path=db_file)
    engine = MemoryEngine(settings)
    ctx = CommandContext(
        settings=settings,
        history=SessionHistory(),
        memory_engine=engine,
    )

    proj_dir = tmp_path / "app_repo"
    proj_dir.mkdir()
    (proj_dir / "app.py").write_text("print('hello')", encoding="utf-8")

    # project help
    res_help = handle_project(["help"], ctx)
    assert res_help.success is True
    assert "PROJECT CONTEXT COMMANDS" in str(res_help.output)

    # project add
    res_add = handle_project(["add", str(proj_dir), "AppRepo"], ctx)
    assert res_add.success is True
    assert "Registered project 'AppRepo'" in str(res_add.output)

    # project list
    res_list = handle_project(["list"], ctx)
    assert res_list.success is True

    # project use
    res_use = handle_project(["use", "AppRepo"], ctx)
    assert res_use.success is True
    assert "Switched active project" in str(res_use.output)

    # project status
    res_status = handle_project(["status"], ctx)
    assert res_status.success is True
    assert "ACTIVE PROJECT: AppRepo" in str(res_status.output)

    # project scan
    res_scan = handle_project(["scan", "AppRepo"], ctx)
    assert res_scan.success is True
    assert "INDEXING COMPLETE: AppRepo" in str(res_scan.output)

    # project refresh
    res_refresh = handle_project(["refresh"], ctx)
    assert res_refresh.success is True
    assert "ACTIVE PROJECT REFRESHED: AppRepo" in str(res_refresh.output)

    # project info
    res_info = handle_project(["info"], ctx)
    assert res_info.success is True
    assert "PROJECT INFORMATION: AppRepo" in str(res_info.output)

    # project clear
    res_clear = handle_project(["clear"], ctx)
    assert res_clear.success is True
    assert "Cleared active project" in str(res_clear.output)

    # project remove
    res_rm = handle_project(["remove", "AppRepo"], ctx)
    assert res_rm.success is True

    engine.close()


def test_command_registry_includes_memory_and_project() -> None:
    """Ensure default CommandRegistry registers memory and project commands."""
    from ghosttrace.terminal.commands import create_default_registry

    reg = create_default_registry()
    assert isinstance(reg, CommandRegistry)

    mem_cmd = reg.get("memory")
    assert mem_cmd is not None
    assert "mem" in mem_cmd.aliases

    proj_cmd = reg.get("project")
    assert proj_cmd is not None
    assert "proj" in proj_cmd.aliases
