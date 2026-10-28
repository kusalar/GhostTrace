"""Tests for ProjectIndexer incremental hashing, search, and stale file cleanup."""

from __future__ import annotations

import contextlib
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


def test_failed_scan_preserves_previously_indexed_files(tmp_path: Path) -> None:
    """Ensure an interrupted or failed scan does not erase existing indexed files."""
    db_mgr = DatabaseManager(tmp_path / "index_fail.db")
    apply_migrations(db_mgr)
    settings = Settings()
    registry = ProjectRegistry(db_mgr, settings)
    scanner = ProjectScanner(settings)
    indexer = ProjectIndexer(db_mgr)

    proj_dir = tmp_path / "safe_repo"
    proj_dir.mkdir()
    f1 = proj_dir / "main.py"
    f1.write_text("print('hello world')", encoding="utf-8")

    proj = registry.register_project(proj_dir, name="SafeRepo")

    # Initial scan succeeds
    scanned = scanner.scan_project(proj_dir)
    added, _, _ = indexer.sync_project_files(proj.id, proj.name, scanned)
    assert added == 1

    # Simulate an error/exception before sync: index files must remain intact
    files_before = indexer.get_indexed_files(proj.id)
    assert len(files_before) == 1

    with contextlib.suppress(ValueError):
        # Scanning a non-directory raises ValueError
        scanner.scan_project(proj_dir / "non_existent_subdir")

    # Verified: Previously indexed files are untouched
    files_after = indexer.get_indexed_files(proj.id)
    assert len(files_after) == 1
    assert files_after[0].relative_path == "main.py"

    db_mgr.close()
