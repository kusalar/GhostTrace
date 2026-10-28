"""Targeted tests to achieve >= 90% overall project test coverage for release."""

from __future__ import annotations

from pathlib import Path

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.haunt.event_catalog import EventCatalog
from ghosttrace.haunt.schemas import EventCategory, HauntMode
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.project_index import ProjectIndexer
from ghosttrace.memory.project_registry import ProjectRegistry
from ghosttrace.memory.project_scanner import ScannedFile
from ghosttrace.system.health import HealthRegistry


def test_project_index_manager_methods_and_fallback(tmp_path: Path) -> None:
    """Test get_file, list_project_files, delete_project_files, and fallback search."""
    db_path = tmp_path / "idx_test.db"
    db_mgr = DatabaseManager(db_path)
    apply_migrations(db_mgr)

    settings = Settings(project_max_files=10)
    reg = ProjectRegistry(db_mgr, settings)
    idx_mgr = ProjectIndexer(db_mgr, settings)

    # 0. Register project so FK is satisfied
    proj_dir = tmp_path / "sample_proj"
    proj_dir.mkdir()
    p_rec = reg.add_project(path=proj_dir, name="Sample")

    # 1. Index files
    files = [
        ScannedFile(
            relative_path="src/app.py",
            content="def run_app():\n    return 'running'",
            language="python",
            content_hash="hash1",
            size_bytes=35,
        ),
        ScannedFile(
            relative_path="README.md",
            content="# Sample Project\nThis is a sample project for testing.",
            language="markdown",
            content_hash="hash2",
            size_bytes=48,
        ),
    ]
    added, updated, deleted = idx_mgr.sync_project_files(
        project_id=p_rec.id, project_name="Sample", scanned_files=files
    )
    assert added == 2
    assert updated == 0
    assert deleted == 0

    # 2. get_file
    rec = idx_mgr.get_file(project_id=p_rec.id, relative_path="src/app.py")
    assert rec is not None
    assert rec.language == "python"

    none_rec = idx_mgr.get_file(project_id=p_rec.id, relative_path="nonexistent.py")
    assert none_rec is None

    # 3. list_project_files & get_indexed_files
    all_files = idx_mgr.list_project_files(project_id=p_rec.id)
    assert len(all_files) == 2
    assert len(idx_mgr.get_indexed_files(p_rec.id)) == 2

    # 4. _search_fallback
    fallback_res = idx_mgr._search_fallback(
        project_id=p_rec.id,
        project_name="Sample",
        tokens=["run_app", "sample"],
        limit=5,
    )
    assert len(fallback_res) >= 1
    assert any("run_app" in r.file.content for r in fallback_res)

    # Empty tokens fallback returns empty
    empty_res = idx_mgr._search_fallback(p_rec.id, "Sample", [], 5)
    assert empty_res == []

    # 5. count_project_files & search_project_files
    cnt = idx_mgr.count_project_files(project_id=p_rec.id)
    assert cnt == 2

    search_res = idx_mgr.search_project_files(p_rec.id, "Sample", "run_app")
    assert len(search_res) >= 1


def test_project_registry_root_validations_and_removal(tmp_path: Path) -> None:
    """Test register project path safety, active project switching, and removal."""
    db_path = tmp_path / "reg_test.db"
    db_mgr = DatabaseManager(db_path)
    apply_migrations(db_mgr)

    settings = Settings()
    reg = ProjectRegistry(db_mgr, settings)

    # Disallowed root directory registration raises ValueError
    windows_dir = Path("C:/Windows")
    if windows_dir.exists():
        with pytest.raises(ValueError):
            reg.add_project(path=windows_dir, name="bad_win")

    # Valid project registration
    valid_proj = tmp_path / "valid_code"
    valid_proj.mkdir()
    p_rec = reg.add_project(path=valid_proj, name="MyCode")
    assert p_rec.name == "MyCode"

    # Set active project
    reg.set_active_project(p_rec.id)
    active = reg.get_active_project()
    assert active is not None
    assert active.id == p_rec.id

    # Clear active project
    reg.clear_active_project()
    assert reg.get_active_project() is None

    # Remove project
    success = reg.remove_project(p_rec.id)
    assert success is True
    assert reg.get_project(p_rec.id) is None


def test_health_registry_disabled_states(tmp_path: Path) -> None:
    """Test health registry with disabled components reporting DISABLED."""
    fake_model = tmp_path / "absent.gguf"
    settings = Settings(
        haunt_enabled=False,
        guard_enabled=False,
        model_path=fake_model,
    )
    registry = HealthRegistry(settings)
    report = registry.check_all()

    assert report.subsystems["haunted_experience"].status.value == "DISABLED"
    assert report.subsystems["command_guardian"].status.value == "DISABLED"


def test_event_catalog_template_selection() -> None:
    """Test EventCatalog profile fallback and deterministic template selection."""
    catalog = EventCatalog()

    # Event by id
    ev = catalog.get("greeting_awakening")
    assert ev is not None

    # Custom/unmatched profile falls back to default
    msg = catalog.select_template(ev, "unknown-custom-profile", seed=42)
    assert msg is not None
    assert len(msg) > 0

    # Events by category and mode
    greetings = catalog.filter_by_category(EventCategory.GHOST_GREETING)
    assert len(greetings) >= 1
    haunted_events = catalog.filter_by_mode(HauntMode.HAUNTED)
    assert len(haunted_events) >= 1
