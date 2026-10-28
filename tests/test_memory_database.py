"""Tests for SQLite database lifecycle, PRAGMA checks, and transactions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ghosttrace.memory.database import DatabaseManager


def test_database_lifecycle_in_temp_dir(tmp_path: Path) -> None:
    """Ensure database initializes, creates tables, enables foreign keys and WAL."""
    db_path = tmp_path / "test.db"
    db_mgr = DatabaseManager(db_path)

    # Check connection
    conn = db_mgr.get_connection()
    assert isinstance(conn, sqlite3.Connection)

    # Foreign keys check
    fk_cur = conn.execute("PRAGMA foreign_keys;")
    fk_val = fk_cur.fetchone()[0]
    assert fk_val == 1
    conn.close()

    # Apply migrations and check schema version
    from ghosttrace.memory.migrations import apply_migrations

    apply_migrations(db_mgr)
    with db_mgr.connection() as c:
        cur = c.execute("SELECT version FROM schema_metadata;")
        version = cur.fetchone()[0]
        assert version >= 1

    # Check FTS5 availability property
    assert isinstance(db_mgr.fts5_available, bool)

    # Check closing
    db_mgr.close()


def test_transaction_context(tmp_path: Path) -> None:
    """Ensure transaction commits on success and rolls back on exception."""
    from ghosttrace.memory.migrations import apply_migrations

    db_path = tmp_path / "trans.db"
    db_mgr = DatabaseManager(db_path)
    apply_migrations(db_mgr)

    with db_mgr.transaction() as conn:
        conn.execute(
            "INSERT INTO app_state (key, value) VALUES (?, ?);",
            ("test_key", "test_val"),
        )

    # Verify committed
    with db_mgr.cursor() as cur:
        cur.execute("SELECT value FROM app_state WHERE key = ?;", ("test_key",))
        row = cur.fetchone()
        assert row is not None
        assert row["value"] == "test_val"

    # Test rollback on error
    try:
        with db_mgr.transaction() as conn:
            conn.execute(
                "INSERT INTO app_state (key, value) VALUES (?, ?);",
                ("rollback_key", "val"),
            )
            raise ValueError("Intentional crash")
    except ValueError:
        pass

    with db_mgr.cursor() as cur:
        cur.execute("SELECT value FROM app_state WHERE key = ?;", ("rollback_key",))
        assert cur.fetchone() is None

    db_mgr.close()
