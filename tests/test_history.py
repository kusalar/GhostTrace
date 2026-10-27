"""Tests for the SessionHistory in-memory history manager."""

from ghosttrace.terminal.history import SessionHistory


def test_history_addition_and_ordering() -> None:
    """Verify non-empty commands are recorded in chronological order."""
    history = SessionHistory()
    assert history.count == 0

    assert history.add("help") is True
    assert history.add("about") is True
    assert history.add("status") is True

    assert history.count == 3
    assert len(history) == 3
    assert history.get_history() == ["help", "about", "status"]


def test_history_ignores_empty_and_whitespace() -> None:
    """Empty strings and whitespace-only strings must not be recorded."""
    history = SessionHistory()

    assert history.add("") is False
    assert history.add("   ") is False
    assert history.add("\t\n") is False
    assert history.count == 0
    assert history.get_history() == []


def test_history_excludes_history_command() -> None:
    """The 'history' command itself must not be recorded in session history."""
    history = SessionHistory()

    assert history.add("history") is False
    assert history.add("  HISTORY  ") is False
    assert history.add("History") is False
    assert history.count == 0


def test_history_up_down_navigation() -> None:
    """Verify Up and Down arrow key history cursor navigation."""
    history = SessionHistory()
    history.add("first")
    history.add("second")
    history.add("third")

    # Navigate up from end
    assert history.get_previous() == "third"
    assert history.get_previous() == "second"
    assert history.get_previous() == "first"
    # Should stay at first item if pressing up again
    assert history.get_previous() == "first"

    # Navigate down
    assert history.get_next() == "second"
    assert history.get_next() == "third"
    # Moving past the end returns empty string
    assert history.get_next() == ""

    # Clear navigation cursor
    history.reset_cursor()


def test_history_navigation_on_empty() -> None:
    """Navigation on an empty history returns None."""
    history = SessionHistory()
    assert history.get_previous() is None
    assert history.get_next() is None


def test_history_clear() -> None:
    """Clearing history wipes all recorded entries and resets the cursor."""
    history = SessionHistory()
    history.add("status")
    history.add("ai")
    assert history.count == 2

    history.clear()
    assert history.count == 0
    assert history.get_history() == []
