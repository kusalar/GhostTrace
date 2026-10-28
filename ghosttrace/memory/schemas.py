"""Typed models and schemas for the GhostTrace persistent memory and project context subsystem."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryCategory(StrEnum):
    """Structured categories for persistent developer memory."""

    USER_PREFERENCE = "USER_PREFERENCE"
    USER_PROFILE = "USER_PROFILE"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    TECHNICAL_DECISION = "TECHNICAL_DECISION"
    WORKFLOW = "WORKFLOW"
    LEARNING = "LEARNING"
    GENERAL = "GENERAL"


class MemorySource(StrEnum):
    """Origin of a recorded memory item."""

    USER_EXPLICIT = "USER_EXPLICIT"
    EXPLICIT_USER = "USER_EXPLICIT"
    CONVERSATION_EXTRACTED = "CONVERSATION_EXTRACTED"
    PROJECT_METADATA = "PROJECT_METADATA"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"


class MemoryItem(BaseModel):
    """An individual persistent memory record."""

    model_config = ConfigDict(frozen=True)

    id: int
    category: MemoryCategory
    content: str
    source: MemorySource = MemorySource.USER_EXPLICIT
    importance: float = Field(default=1.0, ge=0.0, le=5.0)
    created_at: float
    updated_at: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory item to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        """Construct memory item from dictionary."""
        return cls.model_validate(data)


class ConversationRecord(BaseModel):
    """Persistent session conversation thread."""

    model_config = ConfigDict(frozen=True)

    id: int
    session_id: str
    title: str
    created_at: float
    updated_at: float


class MessageRecord(BaseModel):
    """Individual stored conversation message."""

    model_config = ConfigDict(frozen=True)

    id: int
    conversation_id: int
    role: str
    content: str
    created_at: float


class ProjectRecord(BaseModel):
    """Registered development project metadata."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    root_path: str
    created_at: float
    updated_at: float
    last_indexed_at: float | None = None
    enabled: bool = True


class ProjectFileRecord(BaseModel):
    """Indexed project file containing redacted source content and metadata."""

    model_config = ConfigDict(frozen=True)

    id: int
    project_id: int
    relative_path: str
    content_hash: str
    language: str
    content: str
    indexed_at: float


class MemorySearchResult(BaseModel):
    """Ranked memory search result."""

    model_config = ConfigDict(frozen=True)

    memory: MemoryItem
    score: float
    match_source: str = "fts5"
    snippet: str = ""


class ProjectFileSearchResult(BaseModel):
    """Ranked project file search result."""

    model_config = ConfigDict(frozen=True)

    file: ProjectFileRecord
    project_name: str = ""
    score: float = 1.0
    snippet: str = ""

    @property
    def file_record(self) -> ProjectFileRecord:
        return self.file


class InjectedContext(BaseModel):
    """Bounded prompt context constructed for LLM consumption."""

    model_config = ConfigDict(frozen=True)

    memories: list[MemoryItem] = Field(default_factory=list)
    project_files: list[ProjectFileSearchResult] = Field(default_factory=list)
    active_project: ProjectRecord | None = None
    formatted_memory_context: str = ""
    formatted_project_context: str = ""
    total_chars: int = 0


class MemoryStatus(BaseModel):
    """Comprehensive telemetry and status snapshot of the memory subsystem."""

    model_config = ConfigDict(frozen=True)

    is_enabled: bool
    persist_conversations: bool = True
    db_path: str = ""
    total_memories: int = 0
    total_conversations: int = 0
    total_messages: int = 0
    total_projects: int = 0
    active_project_id: int | None = None
    active_project_name: str | None = None
    indexed_files_count: int = 0
    fts5_available: bool = True
    max_memories: int = 500
    max_context_chars: int = 4000
    project_enabled: bool = True
    database_size_bytes: int = 0
    wal_mode: bool = True

    @property
    def database_path(self) -> str:
        return self.db_path

    @property
    def max_items(self) -> int:
        return self.max_memories

    @property
    def total_project_files(self) -> int:
        return self.indexed_files_count


class ProjectIndexResult(BaseModel):
    """Outcome of scanning and indexing project source files."""

    model_config = ConfigDict(frozen=True)

    project_id: int
    project_name: str
    scanned_files: int = 0
    indexed_files: int = 0
    updated_files: int = 0
    stale_files_removed: int = 0
    total_bytes: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
