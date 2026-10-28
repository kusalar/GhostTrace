"""Memory repository for CRUD operations and storage lifecycle."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.redaction import redact_sensitive_data
from ghosttrace.memory.schemas import MemoryCategory, MemoryItem, MemorySource

if TYPE_CHECKING:
    from ghosttrace.config.settings import Settings

logger = logging.getLogger("ghosttrace.memory.repository")


class MemoryRepository:
    """Manages CRUD persistence for developer memories."""

    def __init__(
        self,
        db: DatabaseManager,
        max_memories: int | Settings = 500,
        max_content_chars: int = 10000,
    ) -> None:
        self.db = db
        if hasattr(max_memories, "memory_max_items"):
            self.max_memories = max_memories.memory_max_items
            self.max_content_chars = getattr(max_memories, "memory_max_content_chars", 10000)
        else:
            self.max_memories = int(max_memories)
            self.max_content_chars = max_content_chars

    def create_memory(
        self,
        content: str = "",
        category: MemoryCategory | str = MemoryCategory.GENERAL,
        source: MemorySource | str = MemorySource.USER_EXPLICIT,
        importance: float = 1.0,
        **kwargs: object,
    ) -> MemoryItem:
        """Alias for save_memory."""
        if not content and "content" in kwargs:
            content = str(kwargs["content"])
        return self.save_memory(
            content=content,
            category=category,
            source=source,
            importance=importance,
        )

    def save_memory(
        self,
        content: str,
        category: MemoryCategory | str = MemoryCategory.GENERAL,
        source: MemorySource | str = MemorySource.USER_EXPLICIT,
        importance: float = 1.0,
    ) -> MemoryItem:
        """Create and persist a new developer memory record with redaction and bounding."""
        clean_content = content.strip()
        if not clean_content:
            msg = "Memory content cannot be empty."
            raise ValueError(msg)

        # Enforce max storage items
        current_count = self.count_memories()
        if current_count >= self.max_memories:
            msg = (
                f"Memory capacity reached ({current_count}/{self.max_memories}). "
                "Delete or clear older memories before adding new entries."
            )
            raise ValueError(msg)

        # Redact sensitive material
        redacted = redact_sensitive_data(clean_content)

        # Bounded length
        if len(redacted) > self.max_content_chars:
            redacted = redacted[: self.max_content_chars]

        # Standardize category
        if isinstance(category, str):
            try:
                cat_enum = MemoryCategory(category.upper())
            except ValueError:
                cat_enum = MemoryCategory.GENERAL
        else:
            cat_enum = category

        # Standardize source
        if isinstance(source, str):
            try:
                src_enum = MemorySource(source.upper())
            except ValueError:
                src_enum = MemorySource.USER_EXPLICIT
        else:
            src_enum = source

        clamped_importance = max(0.0, min(5.0, float(importance)))
        now = time.time()

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO memories (
                        category, content, source, importance, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (cat_enum.value, redacted, src_enum.value, clamped_importance, now, now),
                )
                memory_id = int(cur.lastrowid)
            finally:
                cur.close()

        return MemoryItem(
            id=memory_id,
            category=cat_enum,
            content=redacted,
            source=src_enum,
            importance=clamped_importance,
            created_at=now,
            updated_at=now,
        )

    def get_memory(self, memory_id: int) -> MemoryItem | None:
        """Retrieve a specific memory by its primary key ID."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT * FROM memories WHERE id = ?;", (memory_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_item(row)
            finally:
                cur.close()

    def get_memory_by_id(self, memory_id: int) -> MemoryItem | None:
        """Alias for get_memory."""
        return self.get_memory(memory_id)

    def get_memory_count(self, category: MemoryCategory | str | None = None) -> int:
        """Alias for count_memories."""
        return self.count_memories(category)

    def list_memories(
        self,
        category: MemoryCategory | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryItem]:
        """List stored memories sorted by recency."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                if category is not None:
                    cat_val = category.value if isinstance(category, MemoryCategory) else category
                    cur.execute(
                        """
                        SELECT * FROM memories
                        WHERE category = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?;
                        """,
                        (cat_val.upper(), limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM memories
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?;
                        """,
                        (limit, offset),
                    )

                rows = cur.fetchall()
                return [self._row_to_item(r) for r in rows]
            finally:
                cur.close()

    def update_memory(
        self,
        memory_id: int,
        content: str,
        category: MemoryCategory | str | None = None,
        importance: float | None = None,
    ) -> MemoryItem | None:
        """Update the content, category, or importance of an existing memory."""
        clean_content = content.strip()
        if not clean_content:
            msg = "Memory content cannot be empty."
            raise ValueError(msg)

        existing = self.get_memory(memory_id)
        if not existing:
            return None

        redacted = redact_sensitive_data(clean_content)
        if len(redacted) > self.max_content_chars:
            redacted = redacted[: self.max_content_chars]

        cat_val = (
            (category.value if isinstance(category, MemoryCategory) else category.upper())
            if category is not None
            else existing.category.value
        )
        imp_val = (
            max(0.0, min(5.0, float(importance))) if importance is not None else existing.importance
        )
        now = time.time()

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    UPDATE memories
                    SET content = ?, category = ?, importance = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (redacted, cat_val, imp_val, now, memory_id),
                )
            finally:
                cur.close()

        return MemoryItem(
            id=memory_id,
            category=MemoryCategory(cat_val),
            content=redacted,
            source=existing.source,
            importance=imp_val,
            created_at=existing.created_at,
            updated_at=now,
        )

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory item by ID."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM memories WHERE id = ?;", (memory_id,))
                return cur.rowcount > 0
            finally:
                cur.close()

    def clear_memories(self) -> int:
        """Remove all stored memories and return the count of deleted items."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM memories;")
                count = cur.rowcount
            finally:
                cur.close()
        return count

    def count_memories(self, category: MemoryCategory | str | None = None) -> int:
        """Return total number of saved memories."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                if category is not None:
                    cat_val = category.value if isinstance(category, MemoryCategory) else category
                    cur.execute(
                        "SELECT COUNT(*) FROM memories WHERE category = ?;",
                        (cat_val.upper(),),
                    )
                else:
                    cur.execute("SELECT COUNT(*) FROM memories;")
                row = cur.fetchone()
                return int(row[0]) if row else 0
            finally:
                cur.close()

    def get_stats(self) -> dict[str, int]:
        """Return counts broken down by category."""
        stats: dict[str, int] = {}
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT category, COUNT(*) FROM memories GROUP BY category;")
                for row in cur.fetchall():
                    stats[str(row[0])] = int(row[1])
            finally:
                cur.close()
        return stats

    def export_memories(self) -> list[dict[str, object]]:
        """Export all memory records as a serializable list of dictionaries."""
        items = self.list_memories(limit=self.max_memories)
        return [
            {
                "id": m.id,
                "category": m.category.value,
                "content": m.content,
                "source": m.source.value,
                "importance": m.importance,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in items
        ]

    def import_memories(self, items: list[dict[str, object]]) -> tuple[int, int]:
        """Import memories from serialized dictionary records.

        Returns:
            Tuple of (imported_count, skipped_count).
        """
        imported = 0
        skipped = 0

        for item in items:
            content = str(item.get("content", "")).strip()
            if not content:
                skipped += 1
                continue

            category = str(item.get("category", MemoryCategory.GENERAL.value))
            source = str(item.get("source", MemorySource.USER_EXPLICIT.value))
            importance_raw = item.get("importance", 1.0)
            try:
                importance = float(importance_raw)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                importance = 1.0

            try:
                self.save_memory(
                    content=content,
                    category=category,
                    source=source,
                    importance=importance,
                )
                imported += 1
            except ValueError:
                skipped += 1

        return imported, skipped

    @staticmethod
    def _row_to_item(row: object) -> MemoryItem:
        """Convert a database row mapping into a typed MemoryItem."""
        r = dict(row)  # type: ignore[call-overload]
        return MemoryItem(
            id=int(r["id"]),
            category=MemoryCategory(r["category"]),
            content=str(r["content"]),
            source=MemorySource(r["source"]),
            importance=float(r["importance"]),
            created_at=float(r["created_at"]),
            updated_at=float(r["updated_at"]),
        )
