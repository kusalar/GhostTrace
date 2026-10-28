"""Project context indexer managing incremental file updates and text search."""

from __future__ import annotations

import logging
import re
import time

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.project_scanner import ScannedFile
from ghosttrace.memory.schemas import ProjectFileRecord, ProjectFileSearchResult

logger = logging.getLogger("ghosttrace.memory.project_index")


class ProjectIndexer:
    """Synchronizes scanned project files into SQLite and executes search queries."""

    def __init__(self, db: DatabaseManager, *args: object, **kwargs: object) -> None:
        self.db = db

    def get_indexed_files(self, project_id: int) -> list[ProjectFileRecord]:
        """Alias for list_project_files."""
        return self.list_project_files(project_id)

    def search_project(
        self,
        project_id: int,
        project_name: str,
        query: str,
        limit: int = 5,
    ) -> list[ProjectFileSearchResult]:
        """Alias for search_project_files."""
        return self.search_project_files(project_id, project_name, query, limit=limit)

    def sync_project_files(
        self,
        project_id: int,
        project_name: str,
        scanned_files: list[ScannedFile],
    ) -> tuple[int, int, int]:
        """Incrementally update indexed files for a project and purge deleted files.

        Returns:
            Tuple of (added_count, updated_count, deleted_count).
        """
        now = time.time()
        added = 0
        updated = 0
        scanned_paths: set[str] = set()

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                # Fetch existing indexed file hashes
                cur.execute(
                    "SELECT relative_path, content_hash FROM project_files WHERE project_id = ?;",
                    (project_id,),
                )
                existing_map = {row["relative_path"]: row["content_hash"] for row in cur.fetchall()}

                for file in scanned_files:
                    scanned_paths.add(file.relative_path)
                    existing_hash = existing_map.get(file.relative_path)

                    if existing_hash is None:
                        # New file
                        cur.execute(
                            """
                            INSERT INTO project_files (
                                project_id, relative_path, content_hash,
                                language, content, indexed_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?);
                            """,
                            (
                                project_id,
                                file.relative_path,
                                file.content_hash,
                                file.language,
                                file.content,
                                now,
                            ),
                        )
                        added += 1
                    elif existing_hash != file.content_hash:
                        # File modified
                        cur.execute(
                            """
                            UPDATE project_files
                            SET content_hash = ?, language = ?, content = ?, indexed_at = ?
                            WHERE project_id = ? AND relative_path = ?;
                            """,
                            (
                                file.content_hash,
                                file.language,
                                file.content,
                                now,
                                project_id,
                                file.relative_path,
                            ),
                        )
                        updated += 1

                # Clean up deleted files
                deleted_paths = set(existing_map.keys()) - scanned_paths
                deleted = len(deleted_paths)
                for del_path in deleted_paths:
                    cur.execute(
                        "DELETE FROM project_files WHERE project_id = ? AND relative_path = ?;",
                        (project_id, del_path),
                    )

                # Update project last_indexed_at timestamp
                cur.execute(
                    "UPDATE projects SET last_indexed_at = ?, updated_at = ? WHERE id = ?;",
                    (now, now, project_id),
                )
            finally:
                cur.close()

        logger.info(
            "Project '%s' synced: %d added, %d updated, %d removed (%d total)",
            project_name,
            added,
            updated,
            deleted,
            len(scanned_files),
        )
        return added, updated, deleted

    def get_file(self, project_id: int, relative_path: str) -> ProjectFileRecord | None:
        """Retrieve an indexed file by relative path."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT id, project_id, relative_path, content_hash,
                           language, content, indexed_at
                    FROM project_files
                    WHERE project_id = ? AND relative_path = ?;
                    """,
                    (project_id, relative_path),
                )
                row = cur.fetchone()
                return self._row_to_record(row) if row else None
            finally:
                cur.close()

    def list_project_files(self, project_id: int, limit: int = 500) -> list[ProjectFileRecord]:
        """List all indexed files for a project."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT id, project_id, relative_path, content_hash,
                           language, content, indexed_at
                    FROM project_files
                    WHERE project_id = ?
                    ORDER BY relative_path ASC
                    LIMIT ?;
                    """,
                    (project_id, limit),
                )
                rows = cur.fetchall()
                return [self._row_to_record(r) for r in rows]
            finally:
                cur.close()

    def count_project_files(self, project_id: int) -> int:
        """Return count of indexed files for a project."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM project_files WHERE project_id = ?;",
                    (project_id,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
            finally:
                cur.close()

    def search_project_files(
        self,
        project_id: int,
        project_name: str,
        query: str,
        limit: int = 5,
    ) -> list[ProjectFileSearchResult]:
        """Search indexed project files using FTS5 with SQL fallback."""
        clean_query = query.strip()
        if not clean_query:
            return []

        tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", clean_query.lower())
        if not tokens:
            return []

        # Attempt FTS5 search
        results: list[ProjectFileSearchResult] = []
        if self.db.is_fts5_available():
            try:
                results = self._search_fts5(project_id, project_name, tokens, limit)
            except Exception as exc:
                logger.warning("FTS5 project search failed (%s); using fallback search", exc)
                results = []

        if not results:
            results = self._search_fallback(project_id, project_name, tokens, limit)

        return results[:limit]

    def _search_fts5(
        self,
        project_id: int,
        project_name: str,
        tokens: list[str],
        limit: int,
    ) -> list[ProjectFileSearchResult]:
        """Query project_files_fts table."""
        fts_query = " OR ".join(f'"{t}"*' for t in tokens[:6])

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT p.id, p.project_id, p.relative_path, p.content_hash, p.language,
                           p.content, p.indexed_at, bm25(project_files_fts) AS bm25_score
                    FROM project_files_fts f
                    JOIN project_files p ON f.rowid = p.id
                    WHERE project_files_fts MATCH ? AND p.project_id = ?
                    ORDER BY bm25_score ASC
                    LIMIT ?;
                    """,
                    (fts_query, project_id, limit),
                )
                rows = cur.fetchall()
                results: list[ProjectFileSearchResult] = []
                for r in rows:
                    rec = self._row_to_record(r)
                    raw_score = float(r["bm25_score"])
                    norm_score = max(0.1, 10.0 / (abs(raw_score) + 1.0))
                    snippet = self._extract_snippet(rec.content, tokens)
                    results.append(
                        ProjectFileSearchResult(
                            file=rec,
                            project_name=project_name,
                            score=norm_score,
                            snippet=snippet,
                        )
                    )
                return results
            finally:
                cur.close()

    def _search_fallback(
        self,
        project_id: int,
        project_name: str,
        tokens: list[str],
        limit: int,
    ) -> list[ProjectFileSearchResult]:
        """Fallback LIKE search over paths and content."""
        conditions: list[str] = []
        params: list[object] = [project_id]

        for t in tokens[:4]:
            conditions.append("(relative_path LIKE ? OR content LIKE ?)")
            params.extend([f"%{t}%", f"%{t}%"])

        if not conditions:
            return []

        where_clause = " OR ".join(conditions)
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                sql = f"""
                    SELECT id, project_id, relative_path, content_hash,
                           language, content, indexed_at
                    FROM project_files
                    WHERE project_id = ? AND ({where_clause})
                    LIMIT ?;
                """
                params.append(limit)
                cur.execute(sql, params)
                rows = cur.fetchall()
                results: list[ProjectFileSearchResult] = []
                for r in rows:
                    rec = self._row_to_record(r)
                    snippet = self._extract_snippet(rec.content, tokens)
                    results.append(
                        ProjectFileSearchResult(
                            file=rec,
                            project_name=project_name,
                            score=1.0,
                            snippet=snippet,
                        )
                    )
                return results
            finally:
                cur.close()

    @staticmethod
    def _extract_snippet(content: str, tokens: list[str], max_len: int = 300) -> str:
        """Extract a representative text snippet containing search tokens."""
        content_lower = content.lower()
        first_pos = -1

        for token in tokens:
            pos = content_lower.find(token.lower())
            if pos != -1 and (first_pos == -1 or pos < first_pos):
                first_pos = pos

        if first_pos == -1:
            return content[:max_len].strip() + ("..." if len(content) > max_len else "")

        start = max(0, first_pos - 80)
        end = min(len(content), first_pos + max_len)
        snippet = content[start:end].strip()

        prefix = "... " if start > 0 else ""
        suffix = " ..." if end < len(content) else ""
        return f"{prefix}{snippet}{suffix}"

    @staticmethod
    def _row_to_record(row: object) -> ProjectFileRecord:
        """Convert a database row mapping into a typed ProjectFileRecord."""
        r = dict(row)  # type: ignore[call-overload]
        return ProjectFileRecord(
            id=int(r["id"]),
            project_id=int(r["project_id"]),
            relative_path=str(r["relative_path"]),
            content_hash=str(r["content_hash"]),
            language=str(r["language"]),
            content=str(r["content"]),
            indexed_at=float(r["indexed_at"]),
        )
