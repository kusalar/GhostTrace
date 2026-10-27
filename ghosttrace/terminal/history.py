"""Lightweight in-memory session command history for GhostTrace."""

from __future__ import annotations


class SessionHistory:
    """Manages ordered, in-memory command history for the active session.

    Resets automatically on application shutdown and does not persist to disk.
    """

    def __init__(self) -> None:
        self._history: list[str] = []
        self._cursor: int = 0

    def add(self, command: str) -> bool:
        """Add a non-empty command to history.

        Excludes empty/whitespace commands and the 'history' command itself.
        Returns True if added, False otherwise.
        """
        cleaned = command.strip()
        if not cleaned:
            return False

        # Exclude 'history' command from being recorded into history
        if cleaned.lower() == "history":
            return False

        self._history.append(cleaned)
        self.reset_cursor()
        return True

    def get_history(self) -> list[str]:
        """Return a copy of the recorded history in chronological order."""
        return list(self._history)

    def get_previous(self, current_input: str = "") -> str | None:
        """Navigate backwards in history (Up arrow)."""
        if not self._history:
            return None

        if self._cursor > 0:
            self._cursor -= 1
            return self._history[self._cursor]

        # If already at first item, return it
        return self._history[0]

    def get_next(self) -> str | None:
        """Navigate forwards in history (Down arrow)."""
        if not self._history:
            return None

        if self._cursor < len(self._history) - 1:
            self._cursor += 1
            return self._history[self._cursor]

        # Moving past the latest command returns empty string
        self._cursor = len(self._history)
        return ""

    def reset_cursor(self) -> None:
        """Reset the navigation cursor to the end of history."""
        self._cursor = len(self._history)

    def clear(self) -> None:
        """Clear all session history."""
        self._history.clear()
        self._cursor = 0

    @property
    def count(self) -> int:
        """Return the number of commands in history."""
        return len(self._history)

    def __len__(self) -> int:
        return len(self._history)
