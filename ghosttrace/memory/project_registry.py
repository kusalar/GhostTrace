"""Project registry for authorized development project directories."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.schemas import ProjectRecord

logger = logging.getLogger("ghosttrace.memory.project_registry")


class ProjectRegistry:
    """Manages registered project folders, activation state, and safety boundaries."""

    def __init__(
        self,
        db: DatabaseManager,
        app_data_dir: Path | str | object | None = None,
    ) -> None:
        self.db = db
        if hasattr(app_data_dir, "app_data_dir"):
            self.app_data_dir = Path(app_data_dir.app_data_dir).resolve()
        elif app_data_dir:
            self.app_data_dir = Path(app_data_dir).resolve()
        else:
            self.app_data_dir = Path.home() / ".ghosttrace"

    def register_project(self, path: Path | str, name: str | None = None) -> ProjectRecord:
        """Alias for add_project."""
        return self.add_project(path=path, name=name)

    def unregister_project(self, identifier: str | int | Path) -> bool:
        """Alias for remove_project."""
        return self.remove_project(identifier)

    def add_project(self, path: Path | str, name: str | None = None) -> ProjectRecord:
        """Register a user-specified project root directory.

        Raises:
            ValueError: If path is invalid, non-existent, dangerous, or already registered.
        """
        raw_path = Path(path)
        if not raw_path.exists():
            msg = f"Project path '{path}' does not exist."
            raise ValueError(msg)

        if not raw_path.is_dir():
            msg = f"Project path '{path}' must be a directory."
            raise ValueError(msg)

        resolved_path = raw_path.resolve()
        self._validate_safe_project_root(resolved_path)

        # Check for duplicates
        existing = self.get_project_by_path(resolved_path)
        if existing:
            msg = f"Project path '{resolved_path}' is already registered as '{existing.name}'."
            raise ValueError(msg)

        proj_name = (name or resolved_path.name).strip()
        if not proj_name:
            proj_name = "project"

        now = time.time()
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO projects (name, root_path, created_at, updated_at, enabled)
                    VALUES (?, ?, ?, ?, 1);
                    """,
                    (proj_name, str(resolved_path), now, now),
                )
                proj_id = int(cur.lastrowid)
            finally:
                cur.close()

        logger.info("Registered project '%s' at %s (id=%d)", proj_name, resolved_path, proj_id)
        return ProjectRecord(
            id=proj_id,
            name=proj_name,
            root_path=str(resolved_path),
            created_at=now,
            updated_at=now,
            last_indexed_at=None,
            enabled=True,
        )

    def _validate_safe_project_root(self, path: Path) -> None:
        """Ensure project path is not a dangerous system directory or drive root."""
        # 1. Reject drive roots (e.g. C:\ or D:\)
        if path.parent == path:
            msg = f"Cannot register drive root '{path}' as a project directory."
            raise ValueError(msg)

        path_str = str(path).lower()

        # 2. Reject Windows system directories
        system_root = os.environ.get("SYSTEMROOT", r"C:\Windows").lower()
        if path_str == system_root or path_str.startswith(system_root + "\\"):
            msg = f"Cannot register Windows system directory '{path}'."
            raise ValueError(msg)

        # 3. Reject Program Files
        prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files").lower()
        if path_str == prog_files or path_str.startswith(prog_files + "\\"):
            msg = f"Cannot register Program Files directory '{path}'."
            raise ValueError(msg)

        # 4. Reject bare User home directory (must be a project subfolder)
        user_home = str(Path.home().resolve()).lower()
        if path_str == user_home:
            msg = "Cannot register user root home directory as a project. Use a specific subfolder."
            raise ValueError(msg)

        # 5. Reject GhostTrace application-data directory
        app_data_str = str(self.app_data_dir).lower()
        if path_str == app_data_str or path_str.startswith(app_data_str + "\\"):
            msg = "Cannot register GhostTrace application data directory as a project."
            raise ValueError(msg)

    def get_project(self, project_id: int) -> ProjectRecord | None:
        """Retrieve a project by ID."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
                row = cur.fetchone()
                return self._row_to_record(row) if row else None
            finally:
                cur.close()

    def get_project_by_path(self, path: Path | str) -> ProjectRecord | None:
        """Retrieve a project by resolved canonical directory path."""
        resolved = str(Path(path).resolve())
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT * FROM projects WHERE root_path = ?;", (resolved,))
                row = cur.fetchone()
                return self._row_to_record(row) if row else None
            finally:
                cur.close()

    def get_project_by_name(self, name: str) -> ProjectRecord | None:
        """Retrieve a project by name (case-insensitive)."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT * FROM projects WHERE name = ? COLLATE NOCASE;",
                    (name.strip(),),
                )
                row = cur.fetchone()
                return self._row_to_record(row) if row else None
            finally:
                cur.close()

    def find_project(self, identifier: str | int | Path) -> ProjectRecord | None:
        """Locate a project by ID, name, or path."""
        if isinstance(identifier, int):
            return self.get_project(identifier)
        s = str(identifier).strip()
        if s.isdigit():
            p = self.get_project(int(s))
            if p:
                return p
        p = self.get_project_by_name(s)
        if p:
            return p
        return self.get_project_by_path(s)

    def list_projects(self) -> list[ProjectRecord]:
        """List all registered projects."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT * FROM projects ORDER BY updated_at DESC;")
                rows = cur.fetchall()
                return [self._row_to_record(r) for r in rows]
            finally:
                cur.close()

    def clear_active_project(self) -> None:
        """Deselect active project."""
        self.set_active_project(None)

    def set_active_project(self, identifier: str | int | Path | None) -> ProjectRecord | None:
        """Select the active project, or deactivate if identifier is None."""
        if identifier is None:
            with self.db.connection() as conn:
                conn.execute("DELETE FROM app_state WHERE key = 'active_project_id';")
            return None

        project = self.find_project(identifier)
        if not project:
            msg = f"Project '{identifier}' not found."
            raise ValueError(msg)

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO app_state (key, value) VALUES ('active_project_id', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (str(project.id),),
            )
        return project

    def get_active_project(self) -> ProjectRecord | None:
        """Retrieve the currently active project if set."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT value FROM app_state WHERE key = 'active_project_id';")
                row = cur.fetchone()
                if not row:
                    return None
                proj_id = int(row["value"])
            finally:
                cur.close()

        return self.get_project(proj_id)

    def remove_project(self, identifier: str | int | Path) -> bool:
        """Unregister a project and remove its indexed context."""
        project = self.find_project(identifier)
        if not project:
            return False

        active = self.get_active_project()
        if active and active.id == project.id:
            self.set_active_project(None)

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM project_files WHERE project_id = ?;", (project.id,))
                cur.execute("DELETE FROM projects WHERE id = ?;", (project.id,))
                return cur.rowcount > 0
            finally:
                cur.close()

    def clear_project_context(self, project_id: int) -> int:
        """Remove all indexed files for a project without unregistering it."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM project_files WHERE project_id = ?;", (project_id,))
                deleted = cur.rowcount
                cur.execute(
                    "UPDATE projects SET last_indexed_at = NULL WHERE id = ?;",
                    (project_id,),
                )
                return deleted
            finally:
                cur.close()

    def update_last_indexed(self, project_id: int, timestamp: float) -> None:
        """Update last_indexed_at timestamp for a project."""
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE projects SET last_indexed_at = ?, updated_at = ? WHERE id = ?;",
                (timestamp, timestamp, project_id),
            )

    @staticmethod
    def _row_to_record(row: object) -> ProjectRecord:
        """Convert a database row mapping into a typed ProjectRecord."""
        r = dict(row)  # type: ignore[call-overload]
        return ProjectRecord(
            id=int(r["id"]),
            name=str(r["name"]),
            root_path=str(r["root_path"]),
            created_at=float(r["created_at"]),
            updated_at=float(r["updated_at"]),
            last_indexed_at=float(r["last_indexed_at"]) if r.get("last_indexed_at") else None,
            enabled=bool(r.get("enabled", 1)),
        )
