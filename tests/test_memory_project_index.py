"""Tests for ProjectIndexer incremental hashing, search, and stale file cleanup."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.project_index import ProjectIndexer
from ghosttrace.memory.project_registry import ProjectRegistry
from ghosttrace.memory.project_scanner import ProjectScanner


def test_project_indexing_and_incremental_updates(tmp_path: Path) -> None:
    """Ensure project indexing creates records, detects updates, and cleans stale files."""
    db_mgr = DatabaseManager(tmp_path / "index.db")
    apply_migrations(db_mgr)
    settings = Settings()
    registry = ProjectRegistry(db_mgr, settings)
    scanner = ProjectScanner(settings)
    indexer = ProjectIndexer(db_mgr)

    proj_dir = tmp_path / "code_repo"
    proj_dir.mkdir()
    f1 = proj_dir / "app.py"
    f1.write_text("print('version 1')", encoding="utf-8")
    f2 = proj_dir / "helper.py"
    f2.write_text("def assist(): pass", encoding="utf-8")

    proj = registry.register_project(proj_dir, name="CodeRepo")

    # Initial scan
    scanned1 = scanner.scan_project(proj_dir)
    added, updated, deleted = indexer.sync_project_files(proj.id, proj.name, scanned1)
    assert added == 2
    assert updated == 0
    assert deleted == 0

    # Search indexed project files
    hits = indexer.search_project(proj.id, proj.name, "version")
    assert len(hits) >= 1
    assert "version 1" in hits[0].snippet

    # Modify file and re-scan
    f1.write_text("print('version 2 - updated')", encoding="utf-8")
    scanned2 = scanner.scan_project(proj_dir)
    added, updated, deleted = indexer.sync_project_files(proj.id, proj.name, scanned2)
    assert added == 0
    assert updated == 1
    assert deleted == 0

    # Delete a file and re-scan
    f2.unlink()
    scanned3 = scanner.scan_project(proj_dir)
    added, updated, deleted = indexer.sync_project_files(proj.id, proj.name, scanned3)
    assert deleted == 1

    files = indexer.get_indexed_files(proj.id)
    assert len(files) == 1
    assert files[0].relative_path == "app.py"

    db_mgr.close()
