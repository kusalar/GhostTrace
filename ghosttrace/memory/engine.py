"""Unified facade coordinating persistent memory and project context operations."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.memory.conversation import ConversationPersistenceManager
from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.migrations import apply_migrations
from ghosttrace.memory.project_index import ProjectIndexer
from ghosttrace.memory.project_registry import ProjectRegistry
from ghosttrace.memory.project_scanner import ProjectScanner
from ghosttrace.memory.repository import MemoryRepository
from ghosttrace.memory.retrieval import MemoryRetriever
from ghosttrace.memory.schemas import (
    ConversationRecord,
    InjectedContext,
    MemoryCategory,
    MemoryItem,
    MemorySearchResult,
    MemorySource,
    MemoryStatus,
    MessageRecord,
    ProjectFileRecord,
    ProjectFileSearchResult,
    ProjectIndexResult,
    ProjectRecord,
)

logger = logging.getLogger("ghosttrace.memory.engine")


class MemoryEngine:
    """Facade orchestrating SQLite persistence, memory CRUD, project indexing, and retrieval."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

        # Database initialization
        db_path = (
            Path(self.settings.memory_database_path).resolve()
            if self.settings.memory_database_path
            else (self.settings.db_dir / "ghosttrace.db").resolve()
        )
        self.db = DatabaseManager(db_path=db_path)

        # Run migrations if enabled
        if self.settings.memory_enabled:
            apply_migrations(self.db)

        # Subsystem components
        self.repository = MemoryRepository(
            db=self.db,
            max_memories=self.settings.memory_max_items,
            max_content_chars=self.settings.memory_max_content_chars,
        )
        self.conversation = ConversationPersistenceManager(
            db=self.db,
            max_messages_per_session=self.settings.memory_max_messages,
            max_message_chars=self.settings.memory_max_content_chars,
        )
        self.retriever = MemoryRetriever(
            db=self.db,
            max_retrieved=self.settings.memory_max_retrieved,
            max_context_chars=self.settings.memory_max_context_chars,
        )
        self.registry = ProjectRegistry(
            db=self.db,
            app_data_dir=self.settings.app_data_dir,
        )
        self.scanner = ProjectScanner(
            max_files=self.settings.project_max_files,
            max_file_bytes=self.settings.project_max_file_bytes,
            max_total_bytes=self.settings.project_max_total_bytes,
            max_depth=self.settings.project_max_depth,
        )
        self.indexer = ProjectIndexer(db=self.db)
        from ghosttrace.memory.context_builder import ContextBuilder

        self.context_builder = ContextBuilder(
            retriever=self.retriever,
            registry=self.registry,
            indexer=self.indexer,
            max_memory_chars=self.settings.memory_max_context_chars,
            max_project_chars=self.settings.project_max_context_chars,
            max_total_chars=self.settings.context_max_total_chars,
        )

    @property
    def is_enabled(self) -> bool:
        """Return True if persistent memory subsystem is active."""
        return self.settings.memory_enabled

    # -------------------------------------------------------------
    # Memory Operations
    # -------------------------------------------------------------
    def save_memory(
        self,
        content: str,
        category: MemoryCategory | str = MemoryCategory.GENERAL,
        source: MemorySource | str = MemorySource.USER_EXPLICIT,
        importance: float = 1.0,
    ) -> MemoryItem:
        """Explicitly save a memory record."""
        if not self.is_enabled:
            msg = "Memory persistence is disabled in settings."
            raise RuntimeError(msg)
        return self.repository.save_memory(
            content=content,
            category=category,
            source=source,
            importance=importance,
        )

    def get_memory(self, memory_id: int) -> MemoryItem | None:
        """Inspect a specific memory by ID."""
        return self.repository.get_memory(memory_id)

    def list_memories(
        self,
        category: MemoryCategory | str | None = None,
        limit: int = 100,
    ) -> list[MemoryItem]:
        """List stored memories sorted by recency."""
        return self.repository.list_memories(category=category, limit=limit)

    def search_memories(
        self,
        query: str,
        category: MemoryCategory | str | None = None,
        limit: int = 5,
    ) -> list[MemorySearchResult]:
        """Search stored memories for a query string."""
        return self.retriever.retrieve(query=query, category=category, limit=limit)

    def update_memory(
        self,
        memory_id: int,
        content: str,
        category: MemoryCategory | str | None = None,
        importance: float | None = None,
    ) -> MemoryItem | None:
        """Edit an existing memory record."""
        if not self.is_enabled:
            msg = "Memory persistence is disabled in settings."
            raise RuntimeError(msg)
        return self.repository.update_memory(
            memory_id=memory_id,
            content=content,
            category=category,
            importance=importance,
        )

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory record by ID."""
        if not self.is_enabled:
            msg = "Memory persistence is disabled in settings."
            raise RuntimeError(msg)
        return self.repository.delete_memory(memory_id)

    def clear_memories(self) -> int:
        """Flush all memories from the database."""
        if not self.is_enabled:
            msg = "Memory persistence is disabled in settings."
            raise RuntimeError(msg)
        return self.repository.clear_memories()

    def clear_all_memories(self) -> int:
        """Flush all memories from the database (alias for clear_memories)."""
        return self.clear_memories()

    def get_memory_stats(self) -> dict[str, object]:
        """Return memory subsystem statistics and category breakdown."""
        status = self.get_status()
        by_cat = self.repository.get_stats()
        return {
            "total_memories": status.total_memories,
            "total_conversations": status.total_conversations,
            "total_messages": status.total_messages,
            "database_size_bytes": status.database_size_bytes,
            "by_category": by_cat,
        }

    def export_memories(self, export_path: Path | str) -> int:
        """Export stored memories to a human-readable JSON file.

        Returns:
            Count of exported records.
        """
        records = self.repository.export_memories()
        dest = Path(export_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump({"memories": records, "count": len(records)}, f, indent=2)
        return len(records)

    def import_memories(self, import_path: Path | str) -> tuple[int, int]:
        """Import memories from a validated JSON export file.

        Returns:
            Tuple of (imported_count, skipped_count).
        """
        if not self.is_enabled:
            msg = "Memory persistence is disabled in settings."
            raise RuntimeError(msg)

        src = Path(import_path).resolve()
        if not src.exists():
            msg = f"Import file '{import_path}' not found."
            raise FileNotFoundError(msg)

        # File size check (limit 10 MB)
        if src.stat().st_size > 10 * 1024 * 1024:
            msg = "Import file exceeds maximum allowed size (10 MB)."
            raise ValueError(msg)

        with open(src, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "memories" not in data:
            msg = "Invalid import file format; expected JSON object with 'memories' list."
            raise ValueError(msg)

        items = data["memories"]
        if not isinstance(items, list):
            msg = "Invalid 'memories' field; expected list."
            raise ValueError(msg)

        if len(items) > 1000:
            msg = "Import file contains too many records (maximum 1000 items per import)."
            raise ValueError(msg)

        return self.repository.import_memories(items)

    # -------------------------------------------------------------
    # Conversation Persistence
    # -------------------------------------------------------------
    def persist_user_message(self, session_id: str, content: str) -> None:
        """Persist a user conversation turn if conversation persistence is enabled."""
        if self.is_enabled and self.settings.memory_persist_conversations:
            self.conversation.add_message(session_id=session_id, role="user", content=content)

    def persist_assistant_message(self, session_id: str, content: str) -> None:
        """Persist an assistant response turn if conversation persistence is enabled."""
        if self.is_enabled and self.settings.memory_persist_conversations:
            self.conversation.add_message(session_id=session_id, role="assistant", content=content)

    def get_conversation_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[MessageRecord]:
        """Retrieve recent persisted messages for a session."""
        return self.conversation.get_messages(session_id=session_id, limit=limit)

    def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[MessageRecord]:
        """Alias for get_conversation_messages."""
        return self.get_conversation_messages(session_id, limit=limit)

    def list_conversations(self, limit: int = 50) -> list[ConversationRecord]:
        """List stored conversation threads."""
        return self.conversation.list_conversations(limit=limit)

    def clear_conversation(self, session_id: str) -> bool:
        """Delete persisted messages for a session."""
        return self.conversation.clear_conversation(session_id)

    # -------------------------------------------------------------
    # Project Operations
    # -------------------------------------------------------------
    def add_project(self, path: Path | str, name: str | None = None) -> ProjectRecord:
        """Register a new development project root."""
        return self.registry.add_project(path=path, name=name)

    def list_projects(self) -> list[ProjectRecord]:
        """List registered projects."""
        return self.registry.list_projects()

    def get_active_project(self) -> ProjectRecord | None:
        """Get the currently active project."""
        return self.registry.get_active_project()

    def set_active_project(self, identifier: str | int | Path | None) -> ProjectRecord | None:
        """Switch active project."""
        return self.registry.set_active_project(identifier)

    def clear_active_project(self) -> None:
        """Deselect active project."""
        self.registry.set_active_project(None)

    def remove_project(self, identifier: str | int | Path) -> bool:
        """Unregister a project and delete indexed files."""
        return self.registry.remove_project(identifier)

    def clear_project_context(self, project_id: int) -> int:
        """Remove indexed files for a project without unregistering it."""
        return self.registry.clear_project_context(project_id)

    def get_project_info(self, identifier: str | int | Path | None = None) -> dict[str, object]:
        """Compile detailed metrics and statistics for a registered project."""
        project: ProjectRecord | None = None
        if identifier is None:
            project = self.get_active_project()
        else:
            project = self.registry.find_project(identifier)

        if not project:
            msg = f"Project '{identifier}' not found."
            raise ValueError(msg)

        files = self.indexer.list_project_files(project.id)
        total_bytes = sum(len(f.content.encode("utf-8")) for f in files)
        languages: dict[str, int] = {}
        for f in files:
            languages[f.language] = languages.get(f.language, 0) + 1

        last_indexed_str = None
        if project.last_indexed_at:
            last_indexed_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(project.last_indexed_at)
            )

        created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(project.created_at))

        return {
            "id": project.id,
            "name": project.name,
            "root_path": project.root_path,
            "file_count": len(files),
            "total_bytes": total_bytes,
            "languages": languages,
            "last_indexed_at": last_indexed_str,
            "created_at": created_str,
        }

    def scan_project(self, identifier: str | int | Path | None = None) -> ProjectIndexResult:
        """Scan and index eligible source files in a registered project."""
        if not self.settings.project_enabled:
            msg = "Project indexing is disabled in settings."
            raise RuntimeError(msg)

        project: ProjectRecord | None = None
        if identifier is None:
            project = self.get_active_project()
        else:
            project = self.registry.find_project(identifier)

        if not project:
            msg = f"Project '{identifier}' not found."
            raise ValueError(msg)

        start_time = time.time()
        scanned = self.scanner.scan_project(project.root_path)
        added, updated, deleted = self.indexer.sync_project_files(
            project_id=project.id,
            project_name=project.name,
            scanned_files=scanned,
        )
        elapsed = time.time() - start_time
        total_bytes = sum(f.size_bytes for f in scanned)

        return ProjectIndexResult(
            project_id=project.id,
            project_name=project.name,
            scanned_files=len(scanned),
            indexed_files=added,
            updated_files=updated,
            stale_files_removed=deleted,
            total_bytes=total_bytes,
            elapsed_seconds=elapsed,
        )

    def refresh_active_project(self) -> ProjectIndexResult:
        """Re-scan and update active project index."""
        active = self.get_active_project()
        if not active:
            msg = "No active project selected."
            raise ValueError(msg)
        return self.scan_project(active.id)

    def search_project(self, query: str, limit: int = 10) -> list[ProjectFileSearchResult]:
        """Search indexed files of the active project."""
        active = self.get_active_project()
        if not active:
            return []
        return self.indexer.search_project(active.id, active.name, query, limit=limit)

    def scan_active_project(self) -> tuple[int, int, int]:
        """Scan and index eligible source files in the active project."""
        res = self.refresh_active_project()
        return (res.indexed_files, res.updated_files, res.stale_files_removed)

    def list_project_files(self, project_id: int, limit: int = 500) -> list[ProjectFileRecord]:
        """List indexed files for a project."""
        return self.indexer.list_project_files(project_id=project_id, limit=limit)

    # -------------------------------------------------------------
    # Context Construction
    # -------------------------------------------------------------
    def build_context(self, query: str) -> InjectedContext:
        """Search and format memory and project data relevant to the query."""
        if not self.is_enabled:
            return InjectedContext()
        return self.context_builder.build_context(query)

    # -------------------------------------------------------------
    # Telemetry and Status
    # -------------------------------------------------------------
    def get_status(self) -> MemoryStatus:
        """Compile a telemetry snapshot of the memory and project context subsystem."""
        active_proj = self.get_active_project()
        total_mems = self.repository.count_memories()
        conversations = self.conversation.list_conversations(limit=1000)
        projects = self.registry.list_projects()

        indexed_files = 0
        if active_proj:
            indexed_files = self.indexer.count_project_files(active_proj.id)

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM messages;")
                msg_count = int(cur.fetchone()[0])
            finally:
                cur.close()

        db_size = 0
        if self.db.db_path.exists():
            try:
                db_size = self.db.db_path.stat().st_size
            except Exception:
                db_size = 0

        return MemoryStatus(
            is_enabled=self.is_enabled,
            persist_conversations=self.settings.memory_persist_conversations,
            db_path=str(self.db.db_path),
            total_memories=total_mems,
            total_conversations=len(conversations),
            total_messages=msg_count,
            total_projects=len(projects),
            active_project_id=active_proj.id if active_proj else None,
            active_project_name=active_proj.name if active_proj else None,
            indexed_files_count=indexed_files,
            fts5_available=self.db.is_fts5_available(),
            max_memories=self.settings.memory_max_items,
            max_context_chars=self.settings.memory_max_context_chars,
            project_enabled=self.settings.project_enabled,
            database_size_bytes=db_size,
            wal_mode=True,
        )

    def close(self) -> None:
        """Close database connection."""
        self.db.close()
