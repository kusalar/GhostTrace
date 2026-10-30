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
    CommandInput > .input--placeholder {
        color: #008833;
    }
    CommandInput > .input--suggestion {
        color: #008833;
    }
    CommandInput > .input--cursor {
        background: #00ff66;
        color: #050807;
        text-style: bold;
    }
    CommandInput:ansi {
        background: ansi_default;
        color: ansi_green;
    }
    CommandInput:ansi > .input--cursor {
        text-style: reverse;
    }
    CommandInput:ansi > .input--placeholder, CommandInput:ansi > .input--suggestion {
        color: ansi_green;
        text-style: dim;
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
        # Privacy: Notify app of aggregate typing activity WITHOUT passing key or character data
        try:
            app = self.app
            if hasattr(app, "on_keystroke_activity"):
                app.on_keystroke_activity()
        except Exception:
            pass

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
