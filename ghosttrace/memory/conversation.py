"""Persistent conversation history manager across GhostTrace sessions."""

from __future__ import annotations

import logging
import time

from ghosttrace.memory.database import DatabaseManager
from ghosttrace.memory.redaction import redact_sensitive_data
from ghosttrace.memory.schemas import ConversationRecord, MessageRecord

logger = logging.getLogger("ghosttrace.memory.conversation")


class ConversationPersistenceManager:
    """Stores and retrieves user and assistant messages across application restarts."""

    def __init__(
        self,
        db: DatabaseManager,
        max_messages_per_session: int | object = 100,
        max_message_chars: int = 8000,
    ) -> None:
        self.db = db
        if hasattr(max_messages_per_session, "memory_max_messages"):
            self.max_messages_per_session = max_messages_per_session.memory_max_messages
            self.max_message_chars = getattr(
                max_messages_per_session, "memory_max_content_chars", 8000
            )
        else:
            self.max_messages_per_session = int(max_messages_per_session)
            self.max_message_chars = max_message_chars

    def get_total_conversations(self) -> int:
        """Return total number of saved conversations."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM conversations;")
                return int(cur.fetchone()[0])
            finally:
                cur.close()

    def get_total_messages(self) -> int:
        """Return total number of saved messages."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM messages;")
                return int(cur.fetchone()[0])
            finally:
                cur.close()

    def get_conversation_messages(self, session_id: str, limit: int = 100) -> list[MessageRecord]:
        """Alias for get_messages."""
        return self.get_messages(session_id, limit=limit)

    def get_or_create_conversation(
        self,
        session_id: str,
        title: str | None = None,
    ) -> ConversationRecord:
        """Find or create a conversation record for the given session identifier."""
        clean_sid = session_id.strip() or "default"
        now = time.time()

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT id, session_id, title, created_at, updated_at "
                    "FROM conversations WHERE session_id = ?;",
                    (clean_sid,),
                )
                row = cur.fetchone()
                if row:
                    return ConversationRecord(
                        id=int(row["id"]),
                        session_id=str(row["session_id"]),
                        title=str(row["title"]),
                        created_at=float(row["created_at"]),
                        updated_at=float(row["updated_at"]),
                    )

                conv_title = title or f"Session {clean_sid[:8]}"
                cur.execute(
                    """
                    INSERT INTO conversations (session_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (clean_sid, conv_title, now, now),
                )
                conv_id = int(cur.lastrowid)
                return ConversationRecord(
                    id=conv_id,
                    session_id=clean_sid,
                    title=conv_title,
                    created_at=now,
                    updated_at=now,
                )
            finally:
                cur.close()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> MessageRecord | None:
        """Persist a conversation turn (user or assistant) with bounding and secret redaction."""
        clean_content = content.strip()
        if not clean_content:
            return None

        # Filter out approval tokens, transient internal telemetry, and raw execution commands
        if clean_content.startswith("guard approve ") or clean_content.startswith("guard cancel "):
            return None

        # Redact credentials before storage
        redacted = redact_sensitive_data(clean_content)
        if len(redacted) > self.max_message_chars:
            redacted = redacted[: self.max_message_chars]

        conv = self.get_or_create_conversation(session_id)
        now = time.time()

        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                # Deduplication check: Avoid inserting identical role+content immediately after
                cur.execute(
                    """
                    SELECT role, content FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC LIMIT 1;
                    """,
                    (conv.id,),
                )
                last_msg = cur.fetchone()
                if last_msg and last_msg["role"] == role and last_msg["content"] == redacted:
                    return None

                cur.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (conv.id, role, redacted, now),
                )
                msg_id = int(cur.lastrowid)

                # Update conversation updated_at
                cur.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?;",
                    (now, conv.id),
                )

                # Enforce per-conversation maximum message limit
                cur.execute(
                    """
                    DELETE FROM messages
                    WHERE conversation_id = ? AND id NOT IN (
                        SELECT id FROM messages
                        WHERE conversation_id = ?
                        ORDER BY id DESC LIMIT ?
                    );
                    """,
                    (conv.id, conv.id, self.max_messages_per_session),
                )

                return MessageRecord(
                    id=msg_id,
                    conversation_id=conv.id,
                    role=role,
                    content=redacted,
                    created_at=now,
                )
            finally:
                cur.close()

    def get_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[MessageRecord]:
        """Retrieve recent persisted messages for a session in chronological order."""
        conv = self.get_or_create_conversation(session_id)
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT id, conversation_id, role, content, created_at
                    FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id ASC
                    LIMIT ?;
                    """,
                    (conv.id, limit),
                )
                rows = cur.fetchall()
                return [
                    MessageRecord(
                        id=int(r["id"]),
                        conversation_id=int(r["conversation_id"]),
                        role=str(r["role"]),
                        content=str(r["content"]),
                        created_at=float(r["created_at"]),
                    )
                    for r in rows
                ]
            finally:
                cur.close()

    def list_conversations(self, limit: int = 50) -> list[ConversationRecord]:
        """List stored conversation threads."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT id, session_id, title, created_at, updated_at
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return [
                    ConversationRecord(
                        id=int(r["id"]),
                        session_id=str(r["session_id"]),
                        title=str(r["title"]),
                        created_at=float(r["created_at"]),
                        updated_at=float(r["updated_at"]),
                    )
                    for r in rows
                ]
            finally:
                cur.close()

    def clear_conversation(self, session_id: str) -> bool:
        """Delete all messages for a given session."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT id FROM conversations WHERE session_id = ?;", (session_id,))
                row = cur.fetchone()
                if not row:
                    return False
                conv_id = int(row["id"])
                cur.execute("DELETE FROM messages WHERE conversation_id = ?;", (conv_id,))
                return True
            finally:
                cur.close()

    def cleanup_old_conversations(self, retention_days: int) -> int:
        """Delete conversations and their messages older than the retention window."""
        cutoff = time.time() - (retention_days * 86400.0)
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM conversations WHERE updated_at < ?;", (cutoff,))
                return cur.rowcount
            finally:
                cur.close()
