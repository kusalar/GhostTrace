"""Tests for ProjectScanner bounded directory traversal, exclusions, and file limits."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.memory.project_scanner import ProjectScanner


def test_project_scanner_exclusions_and_limits(tmp_path: Path) -> None:
    """Ensure git folders, venvs, binary files, and secrets are excluded while code is scanned."""
    proj_root = tmp_path / "mock_project"
    proj_root.mkdir()

    # Regular files
    (proj_root / "main.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
    (proj_root / "README.md").write_text("# Mock Project\n", encoding="utf-8")

    # Excluded directories
    git_dir = proj_root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config content", encoding="utf-8")

    venv_dir = proj_root / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = ...", encoding="utf-8")

    # Excluded secret file
    (proj_root / ".env").write_text("SECRET_KEY=supersecret\n", encoding="utf-8")

    # Excluded binary file
    (proj_root / "model.gguf").write_bytes(b"\x00" * 100)

    settings = Settings(
        project_max_files=50,
        project_max_file_bytes=10000,
        project_max_total_bytes=50000,
        project_max_depth=4,
    )
    scanner = ProjectScanner(settings)
    scanned = scanner.scan_project(proj_root)

    scanned_paths = [s.relative_path for s in scanned]
    assert "main.py" in scanned_paths
    assert "README.md" in scanned_paths

    # Verify exclusions
    assert not any(".git" in p for p in scanned_paths)
    assert not any(".venv" in p for p in scanned_paths)
    assert not any(".env" in p for p in scanned_paths)
    assert not any("model.gguf" in p for p in scanned_paths)
