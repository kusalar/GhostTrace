"""Custom Header widget for GhostTrace terminal UI."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from ghosttrace.config.settings import Settings


class GhostTraceHeader(Widget):
    """Header widget displaying branding, version, and honest subsystem connection states."""

    DEFAULT_CSS = """
    GhostTraceHeader {
        dock: top;
        height: 3;
        background: #060a08;
        border-bottom: heavy #00441b;
        padding: 0 1;
        content-align: center middle;
    }
    #header-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #branding {
        width: 1fr;
        color: #00ff66;
        text-style: bold;
    }
    #entity-status {
        width: auto;
        color: #33ff33;
        margin-right: 2;
    }
    #ai-status {
        width: auto;
        color: #ff5555;
        text-style: bold;
    }
    """

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-container"):
            yield Static(
                f"[bold #00ff66]GHOSTTRACE[/] [dim #33aa55]v{self.settings.app_version}[/]",
                id="branding",
            )
            yield Static(
                "[dim #338844]ENTITY:[/] [bold #33ff33]AWAKE[/]",
                id="entity-status",
            )
            yield Static(
                "[dim #883333]AI ENGINE:[/] [bold #ff5555]NOT CONNECTED[/]",
                id="ai-status",
            )
