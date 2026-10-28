"""Schema versioning and migrations for GhostTrace persistent SQLite database."""

from __future__ import annotations

import logging
import time

from ghosttrace.memory.database import DatabaseManager

logger = logging.getLogger("ghosttrace.memory.migrations")

CURRENT_SCHEMA_VERSION = 1


def get_current_version(db: DatabaseManager) -> int:
    """Retrieve the highest applied schema version from the database."""
    with db.connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_metadata';"
            )
            if not cur.fetchone():
                return 0

            cur.execute("SELECT MAX(version) FROM schema_metadata;")
            row = cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
            return 0
        finally:
            cur.close()


def apply_migrations(db: DatabaseManager) -> int:
    """Apply all unapplied schema migrations in sequence within explicit transactions.

    Returns:
        The final schema version after migration.
    """
    current_version = get_current_version(db)
    fts5_available = db.is_fts5_available()

    if current_version < 1:
        _apply_migration_v1(db, fts5_available=fts5_available)
        current_version = 1

    logger.info("Database schema at version %d (FTS5: %s)", current_version, fts5_available)
    return current_version


def _apply_migration_v1(db: DatabaseManager, fts5_available: bool) -> None:
    """Apply Initial Migration (v1): Core tables, indexes, triggers, and FTS5 search."""
    logger.info("Applying database migration v1...")

    base_ddl = """
    -- Schema metadata table
    CREATE TABLE IF NOT EXISTS schema_metadata (
        version INTEGER PRIMARY KEY,
        applied_at REAL NOT NULL,
        description TEXT NOT NULL
    );

    -- Key-value persistent application state (active project, etc.)
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    -- Conversations and Sessions
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);

    -- Conversation Messages
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conversation_id);

    -- Developer Memories
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT NOT NULL,
        importance REAL NOT NULL DEFAULT 1.0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);

    -- Registered Projects
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        root_path TEXT NOT NULL UNIQUE,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        last_indexed_at REAL,
        enabled INTEGER NOT NULL DEFAULT 1
    );

    -- Indexed Project Files
    CREATE TABLE IF NOT EXISTS project_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        relative_path TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        language TEXT NOT NULL,
        content TEXT NOT NULL,
        indexed_at REAL NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE(project_id, relative_path)
    );
    CREATE INDEX IF NOT EXISTS idx_project_files_proj ON project_files(project_id);
    """

    fts5_ddl = """
    -- Full-Text Search Virtual Table for Memories
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        content,
        category UNINDEXED,
        content='memories',
        content_rowid='id'
    );

    -- Automated synchronization triggers for memories_fts
    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
        INSERT INTO memories_fts(rowid, content, category)
        VALUES (new.id, new.content, new.category);
    END;

    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, content, category)
        VALUES ('delete', old.id, old.content, old.category);
    END;

    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, content, category)
        VALUES ('delete', old.id, old.content, old.category);
        INSERT INTO memories_fts(rowid, content, category)
        VALUES (new.id, new.content, new.category);
    END;

    -- Full-Text Search Virtual Table for Project Files
    CREATE VIRTUAL TABLE IF NOT EXISTS project_files_fts USING fts5(
        relative_path,
        content,
        content='project_files',
        content_rowid='id'
    );

    -- Automated synchronization triggers for project_files_fts
    CREATE TRIGGER IF NOT EXISTS project_files_ai AFTER INSERT ON project_files BEGIN
        INSERT INTO project_files_fts(rowid, relative_path, content)
        VALUES (new.id, new.relative_path, new.content);
    END;

    CREATE TRIGGER IF NOT EXISTS project_files_ad AFTER DELETE ON project_files BEGIN
        INSERT INTO project_files_fts(project_files_fts, rowid, relative_path, content)
        VALUES ('delete', old.id, old.relative_path, old.content);
    END;

    CREATE TRIGGER IF NOT EXISTS project_files_au AFTER UPDATE ON project_files BEGIN
        INSERT INTO project_files_fts(project_files_fts, rowid, relative_path, content)
        VALUES ('delete', old.id, old.relative_path, old.content);
        INSERT INTO project_files_fts(rowid, relative_path, content)
        VALUES (new.id, new.relative_path, new.content);
    END;
    """

    with db.connection() as conn:
        conn.executescript(base_ddl)
        if fts5_available:
            try:
                conn.executescript(fts5_ddl)
            except Exception as exc:
                logger.warning("FTS5 table creation failed (%s); continuing without FTS5", exc)

        conn.execute(
            "INSERT INTO schema_metadata (version, applied_at, description) VALUES (?, ?, ?);",
            (1, time.time(), "Initial schema: conversations, messages, memories, projects"),
        )
