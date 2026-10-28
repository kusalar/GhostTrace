"""SQLite database connection and lifecycle manager for GhostTrace memory."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("ghosttrace.memory.database")


class DatabaseManager:
    """Manages SQLite connections, pragmas, WAL mode, and transactions."""

    def __init__(
        self,
        db_path: Path | str,
        busy_timeout_ms: int = 5000,
        enable_wal: bool = True,
    ) -> None:
        self.db_path = Path(db_path).resolve()
        self.busy_timeout_ms = busy_timeout_ms
        self.enable_wal = enable_wal
        self._fts5_supported: bool | None = None

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply required performance and integrity PRAGMAs to an active connection."""
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        try:
            # Enforce relational integrity
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms};")
            cursor.execute("PRAGMA synchronous = NORMAL;")

            if self.enable_wal and self.db_path.name != ":memory:":
                try:
                    cursor.execute("PRAGMA journal_mode = WAL;")
                    result = cursor.fetchone()
                    mode = result[0] if result else "unknown"
                    logger.debug("SQLite journal_mode set to %s for %s", mode, self.db_path)
                except sqlite3.OperationalError as exc:
                    logger.warning("Could not enable WAL mode (%s); falling back", exc)
        finally:
            cursor.close()

    def get_raw_connection(self) -> sqlite3.Connection:
        """Open a single unmanaged SQLite connection with standard configuration."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.busy_timeout_ms / 1000.0,
            check_same_thread=False,
        )
        self._configure_connection(conn)
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager providing an active connection with transaction lifecycle."""
        conn = self.get_raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        """Context manager providing a cursor with commit/rollback management."""
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    def is_fts5_available(self) -> bool:
        """Detect whether SQLite FTS5 extension is compiled and available."""
        if self._fts5_supported is not None:
            return self._fts5_supported

        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_test USING fts5(col);")
                cur.execute("DROP TABLE IF EXISTS _fts5_test;")
                self._fts5_supported = True
            except sqlite3.OperationalError:
                self._fts5_supported = False
            finally:
                cur.close()

        return self._fts5_supported

    @property
    def fts5_available(self) -> bool:
        """Property alias for is_fts5_available()."""
        return self.is_fts5_available()

    def get_connection(self) -> sqlite3.Connection:
        """Alias for get_raw_connection()."""
        return self.get_raw_connection()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Alias for connection() with transaction semantics."""
        with self.connection() as conn:
            yield conn

    def close(self) -> None:
        """Explicit close hook for clean shutdown."""
        pass

    def execute_script(self, sql_script: str) -> None:
        """Execute a multi-statement DDL/DML script within a transaction."""
        with self.connection() as conn:
            conn.executescript(sql_script)

    def vacuum(self) -> None:
        """Reclaim unused database space."""
        conn = self.get_raw_connection()
        try:
            conn.execute("VACUUM;")
        finally:
            conn.close()
