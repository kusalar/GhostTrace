"""Command input widget with session history navigation for GhostTrace."""

from textual import events
from textual.widgets import Input

from ghosttrace.terminal.history import SessionHistory


class CommandInput(Input):
    """Interactive command input field supporting Up/Down session history navigation."""

    DEFAULT_CSS = """
    CommandInput {
        background: #050807;
        color: #00ff66;
        border: heavy #00441b;
        padding: 0 1;
        height: 3;
    }
    CommandInput:focus {
        border: heavy #00aa44;
    }
    """

    def __init__(self, history: SessionHistory, **kwargs: object) -> None:
        super().__init__(
            placeholder="Enter command (e.g., 'help', 'status', 'about', 'ai', 'exit')...",
            **kwargs,
        )
        self.history = history

    def on_key(self, event: events.Key) -> None:
        """Handle Up and Down arrow keys to navigate command history."""
        if event.key == "up":
            prev_cmd = self.history.get_previous(self.value)
            if prev_cmd is not None:
                self.value = prev_cmd
                self.cursor_position = len(self.value)
                event.prevent_default()
                event.stop()

        elif event.key == "down":
            next_cmd = self.history.get_next()
            if next_cmd is not None:
                self.value = next_cmd
                self.cursor_position = len(self.value)
                event.prevent_default()
                event.stop()
