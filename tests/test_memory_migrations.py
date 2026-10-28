"""Tests for database migrations and schema versioning."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import (
    CURRENT_SCHEMA_VERSION,
    apply_migrations,
    get_current_version,
)


def test_migration_version_tracking(tmp_path: Path) -> None:
    """Ensure migrations apply schema and record the version correctly."""
    db_file = tmp_path / "mig.db"
    db_mgr = DatabaseManager(db_file)

    # Initial version before migration is 0
    v0 = get_current_version(db_mgr)
    assert v0 == 0

    # Apply migration
    v1 = apply_migrations(db_mgr)
    assert v1 == CURRENT_SCHEMA_VERSION

    # Re-running migration is idempotent
    v2 = apply_migrations(db_mgr)
    assert v2 == CURRENT_SCHEMA_VERSION

    db_mgr.close()
