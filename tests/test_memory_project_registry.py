"""Tests for ProjectRegistry management, dangerous root checks, and active project state."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.project_registry import ProjectRegistry


def test_project_registration_and_active_state(tmp_path: Path) -> None:
    """Ensure project registration, lookup, switching and removing works."""
    db_mgr = DatabaseManager(tmp_path / "proj_reg.db")
    apply_migrations(db_mgr)
    settings = Settings()
    registry = ProjectRegistry(db_mgr, settings)

    proj_dir = tmp_path / "my_cool_project"
    proj_dir.mkdir()

    # Register project
    proj = registry.register_project(proj_dir, name="CoolProject")
    assert proj.id > 0
    assert proj.name == "CoolProject"
    assert proj.root_path == str(proj_dir.resolve())

    # List projects
    projs = registry.list_projects()
    assert len(projs) == 1
    assert projs[0].id == proj.id

    # Active project initially None
    assert registry.get_active_project() is None

    # Set active project
    active = registry.set_active_project("CoolProject")
    assert active.id == proj.id
    assert registry.get_active_project() is not None
    assert registry.get_active_project().id == proj.id

    # Clear active project
    registry.clear_active_project()
    assert registry.get_active_project() is None

    # Unregister project
    assert registry.unregister_project("CoolProject") is True
    assert len(registry.list_projects()) == 0

    db_mgr.close()


def test_reject_dangerous_project_roots(tmp_path: Path) -> None:
    """Ensure dangerous system roots like C:\\ and Windows directory are rejected."""
    db_mgr = DatabaseManager(tmp_path / "dang.db")
    settings = Settings()
    registry = ProjectRegistry(db_mgr, settings)

    # Drive root (e.g. C:\)
    drive_root = Path(os.path.splitdrive(os.path.abspath("."))[0] + "\\")
    with pytest.raises(ValueError, match="Cannot register drive root"):
        registry.register_project(drive_root)

    # Windows dir
    sys_root = os.environ.get("SYSTEMROOT")
    if sys_root and Path(sys_root).exists():
        with pytest.raises(ValueError, match="Cannot register Windows system directory"):
            registry.register_project(Path(sys_root))

    db_mgr.close()
