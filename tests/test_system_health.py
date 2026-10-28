"""Tests for internal subsystem health diagnostics and safety invariants."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from ghosttrace.config.settings import Settings
from ghosttrace.system.health import HealthRegistry
from ghosttrace.system.schemas import HealthStatus, SubsystemHealth


def test_health_checks_do_not_load_model() -> None:
    """Invariant: Health checks must NEVER load model weights into RAM."""
    settings = Settings()
    registry = HealthRegistry(settings)

    mock_ai = MagicMock()
    mock_ai.model_manager.is_loaded.return_value = False
    mock_ai.get_status.return_value = MagicMock(runtime_available=True, is_loaded=False)

    report = registry.check_all(ai_engine=mock_ai)
    # Ensure load_model was NOT called
    mock_ai.model_manager.load_model.assert_not_called()
    assert "model_loaded" in report.subsystems
    assert report.subsystems["model_loaded"].status == HealthStatus.HEALTHY


def test_health_checks_disabled_subsystems() -> None:
    """Disabled subsystems must report as DISABLED, not ERROR."""
    settings = Settings(
        ai_enabled=False,
        ghost_enabled=False,
        dev_enabled=False,
        guard_enabled=False,
        memory_enabled=False,
        project_enabled=False,
        haunt_enabled=False,
    )
    registry = HealthRegistry(settings)
    report = registry.check_all()

    assert report.subsystems["ai_engine"].status == HealthStatus.DISABLED
    assert report.subsystems["ghost_persona"].status == HealthStatus.DISABLED
    assert report.subsystems["developer_assistant"].status == HealthStatus.DISABLED
    assert report.subsystems["command_guardian"].status == HealthStatus.DISABLED
    assert report.subsystems["memory_db"].status == HealthStatus.DISABLED
    assert report.subsystems["project_context"].status == HealthStatus.DISABLED
    assert report.subsystems["haunted_experience"].status == HealthStatus.DISABLED


def test_health_checks_error_propagation() -> None:
    """Errors in critical subsystems correctly elevate overall status to ERROR."""
    settings = Settings()
    registry = HealthRegistry(settings)

    with patch.object(
        registry,
        "check_configuration",
        return_value=SubsystemHealth(
            name="configuration", status=HealthStatus.ERROR, details="Corrupt config"
        ),
    ):
        report = registry.check_all()
        assert report.overall_status == HealthStatus.ERROR
        assert "critical" in report.summary.lower() or "error" in report.summary.lower()


def test_health_checks_memory_db_and_wal(tmp_path: Path) -> None:
    """Verify live SQLite database connectivity and WAL mode inspection."""
    db_file = tmp_path / "test_health.db"
    settings = Settings(memory_database_path=db_file)
    registry = HealthRegistry(settings)

    # Initial state: uninitialized
    h1 = registry.check_memory_database()
    assert h1.status == HealthStatus.HEALTHY
    assert "uninitialized" in h1.details.lower()

    # Create SQLite table in WAL mode
    import sqlite3

    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE test (id INT);")
    conn.commit()
    conn.close()

    h2 = registry.check_memory_database()
    assert h2.status == HealthStatus.HEALTHY
    assert "tables" in h2.details

    h_wal = registry.check_memory_wal()
    assert h_wal.status == HealthStatus.HEALTHY
    assert "WAL" in h_wal.details
