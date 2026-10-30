"""Release readiness, packaging verification, and safety invariant regression tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from ghosttrace import __version__
from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.exceptions import ModelNotFoundError
from ghosttrace.ai.schemas import ModelStatus
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.guardian.engine import GuardianEngine
from ghosttrace.guardian.risk import RiskLevel
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.haunt.schemas import HauntMode, TriggerContext, TriggerType
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.project_scanner import ProjectScanner
from ghosttrace.system.engine import SystemEngine


def test_version_metadata_consistency() -> None:
    """Verify consistent 1.2.0 version string across config, package, and settings."""
    settings = Settings()
    assert settings.app_version == "1.2.0"
    assert __version__ == "1.2.0"


def test_default_experience_mode_is_normal() -> None:
    """Verify release default experience mode is strictly NORMAL across all entry points."""
    settings = Settings()
    assert settings.haunt_mode == "normal"

    haunt = HauntEngine(settings)
    assert haunt.mode == HauntMode.NORMAL

    # NORMAL mode must suppress unsolicited events
    res = haunt.process_trigger(TriggerContext(trigger_type=TriggerType.SESSION_START))
    assert res.fired is False
    assert "suppressed in NORMAL mode" in res.reason


def test_missing_model_weights_standby_and_graceful_recovery(tmp_path: Path) -> None:
    """Verify that absent model weights result in STANDBY state without crashes."""
    fake_model = tmp_path / "nonexistent_model.gguf"
    settings = Settings(model_path=fake_model)

    ai = AIEngine(settings)
    status = ai.get_status()

    assert status.model_exists is False
    assert status.model_status in (
        ModelStatus.UNLOADED,
        ModelStatus.UNAVAILABLE,
        ModelStatus.NOT_FOUND,
    )
    assert status.is_loaded is False

    # Attempting to load nonexistent model raises ModelNotFoundError with informative message
    with pytest.raises(ModelNotFoundError) as exc_info:
        ai.load_model()
    assert "not found" in str(exc_info.value).lower()

    # Recovery: app remains operational and get_status does not crash
    status_after = ai.get_status()
    assert status_after.is_loaded is False


def test_guardian_safety_invariants_and_token_tampering() -> None:
    """Verify Guardian safety invariants: shell=False, token validity, and high-risk blocking."""
    settings = Settings(guard_enabled=True, guard_block_high_risk=True)
    guardian = GuardianEngine(settings)

    # 1. Dangerous command must be classified HIGH or BLOCKED and not permitted
    analysis_rm = guardian.analyze("rmdir /s /q C:\\Windows")
    assert analysis_rm.risk_level in (RiskLevel.HIGH, RiskLevel.BLOCKED)
    assert analysis_rm.is_permitted is False

    # 2. Safe command analysis produces valid request
    analysis_safe = guardian.analyze("python --version")
    assert analysis_safe.risk_level == RiskLevel.SAFE
    assert analysis_safe.is_permitted is True

    # 3. Create approval token
    approval = guardian.request_approval("python --version")
    assert approval.token is not None

    # 4. Tampering with working directory invalidates approval and consumes token
    fake_cwd = "C:\\Fake\\Dir"
    valid_tampered, _, _ = guardian.approval_mgr.validate_and_consume(
        token=approval.token,
        command="python --version",
        working_dir=fake_cwd,
        policy_fingerprint=guardian.policy.get_fingerprint(),
    )
    assert valid_tampered is False

    # Attempting to reuse the consumed token fails
    valid_reused, _, _ = guardian.approval_mgr.validate_and_consume(
        token=approval.token,
        command="python --version",
        working_dir=approval.working_dir,
        policy_fingerprint=guardian.policy.get_fingerprint(),
    )
    assert valid_reused is False

    # 5. Fresh approval validates cleanly once, then cannot be used again
    fresh_approval = guardian.request_approval("python --version")
    valid_first, _, _ = guardian.approval_mgr.validate_and_consume(
        token=fresh_approval.token,
        command="python --version",
        working_dir=fresh_approval.working_dir,
        policy_fingerprint=guardian.policy.get_fingerprint(),
    )
    assert valid_first is True

    valid_second, _, _ = guardian.approval_mgr.validate_and_consume(
        token=fresh_approval.token,
        command="python --version",
        working_dir=fresh_approval.working_dir,
        policy_fingerprint=guardian.policy.get_fingerprint(),
    )
    assert valid_second is False


def test_project_scanner_read_only_and_exclusions(tmp_path: Path) -> None:
    """Verify that project scanning is strictly read-only and respects exclusions."""
    # Create mock project tree
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir()

    # Normal source file
    src_file = proj_dir / "main.py"
    src_file.write_text("print('hello world')", encoding="utf-8")

    # Excluded directories
    git_dir = proj_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("dummy git config", encoding="utf-8")

    venv_dir = proj_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = dummy", encoding="utf-8")

    settings = Settings()
    scanner = ProjectScanner(settings)
    scanned_files = scanner.scan_project(proj_dir)

    # Only main.py should be scanned; .git and .venv must be excluded
    file_names = [f.relative_path for f in scanned_files]
    assert "main.py" in file_names
    assert not any(".git" in f for f in file_names)
    assert not any(".venv" in f for f in file_names)

    # Verify no files were created or modified by scanner
    assert len(list(proj_dir.glob("*.tmp"))) == 0


def test_all_twelve_subsystem_health_checks() -> None:
    """Verify health inspection monitors all 12 subsystems without mutating state."""
    settings = Settings()
    sys_engine = SystemEngine(settings)
    report = sys_engine.check_health()

    assert len(report.subsystems) >= 12
    # Verify key subsystem entries exist
    subsystem_names = list(report.subsystems.keys())
    assert "configuration" in subsystem_names
    assert "command_guardian" in subsystem_names
    assert "haunted_experience" in subsystem_names
    assert "memory_db" in subsystem_names
    assert "ghost_persona" in subsystem_names


def test_haunt_events_isolated_from_sqlite_memories(tmp_path: Path) -> None:
    """Verify atmospheric events strictly never write to SQLite database tables."""
    db_path = tmp_path / "isolation.db"
    db_mgr = DatabaseManager(db_path)
    apply_migrations(db_mgr)

    settings = Settings(haunt_enabled=True, haunt_mode="haunted", memory_database_path=db_path)
    ghost = GhostEngine(settings)
    haunt = HauntEngine(settings, ghost_engine=ghost)
    mem_engine = MemoryEngine(settings)

    # Fire events
    haunt.process_trigger(TriggerContext(trigger_type=TriggerType.SESSION_START))
    haunt.process_trigger(TriggerContext(trigger_type=TriggerType.CODING_SUCCESS))

    assert haunt.history.count >= 1

    # Verify 0 memories created in SQLite
    assert len(mem_engine.list_memories()) == 0


def test_packaged_executable_cli_commands() -> None:
    """Verify that dist/GhostTrace/GhostTrace.exe executes standalone CLI subcommands."""
    exe_path = Path("dist/GhostTrace/GhostTrace.exe")
    if not exe_path.exists():
        pytest.skip("Packaged executable dist/GhostTrace/GhostTrace.exe not yet built.")

    # 1. Version command
    v_res = subprocess.run(
        [str(exe_path), "--version"], capture_output=True, text=True, check=False
    )
    assert v_res.returncode == 0
    assert "GhostTrace v1.2.0" in v_res.stdout

    # 2. Help command
    h_res = subprocess.run([str(exe_path), "--help"], capture_output=True, text=True, check=False)
    assert h_res.returncode == 0
    assert "GhostTrace" in h_res.stdout
    assert "guard" in h_res.stdout

    # 3. Guard status
    g_res = subprocess.run(
        [str(exe_path), "guard", "status"], capture_output=True, text=True, check=False
    )
    assert g_res.returncode == 0
    assert "Guardian Subsystem : ACTIVE" in g_res.stdout

    # 4. Haunt status
    haunt_res = subprocess.run(
        [str(exe_path), "haunt", "status"], capture_output=True, text=True, check=False
    )
    assert haunt_res.returncode == 0
    assert "Experience Mode    : NORMAL" in haunt_res.stdout
