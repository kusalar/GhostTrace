"""Persistent memory and project context subsystem for GhostTrace."""

from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.memory.redaction import contains_sensitive_data, redact_sensitive_data
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
    ProjectRecord,
)

__all__ = [
    "ConversationRecord",
    "InjectedContext",
    "MemoryCategory",
    "MemoryEngine",
    "MemoryItem",
    "MemorySearchResult",
    "MemorySource",
    "MemoryStatus",
    "MessageRecord",
    "ProjectFileRecord",
    "ProjectFileSearchResult",
    "ProjectRecord",
    "contains_sensitive_data",
    "redact_sensitive_data",
]
