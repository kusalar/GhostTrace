"""Status panel widget for GhostTrace terminal UI."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ghosttrace.config.settings import Settings


class StatusPanel(Widget):
    """Sidebar status panel detailing environment, version, and subsystem states."""

    DEFAULT_CSS = """
    StatusPanel {
        width: 32;
        height: 100%;
        background: #050807;
        border-left: solid #00441b;
        padding: 1;
    }
    #status-title {
        color: #00ff66;
        text-style: bold;
        border-bottom: solid #003314;
        margin-bottom: 1;
    }
    #status-body {
        color: #99bb99;
    }
    """

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.settings = settings
        self._command_count = 0
        self._ai_status_text = "STANDBY"
        self._ghost_profile_text = "Forgotten Machine"
        self._ghost_mood_text = "DORMANT"
        self._ghost_enabled = True
        self._dev_enabled = True
        self._dev_static_analysis = True

    def compose(self) -> ComposeResult:
        yield Static("SYSTEM TELEMETRY", id="status-title")
        yield Static(self._build_content(), id="status-body")

    def update_command_count(self, count: int) -> None:
        """Update session command count and refresh widget display."""
        self._command_count = count
        try:
            body = self.query_one("#status-body", Static)
            body.update(self._build_content())
        except Exception:
            pass

    def update_ai_status(self, status_text: str) -> None:
        """Update AI subsystem state string in telemetry panel."""
        self._ai_status_text = status_text
        try:
            body = self.query_one("#status-body", Static)
            body.update(self._build_content())
        except Exception:
            pass

    def update_ghost_status(self, profile: str, mood: str, is_active: bool = True) -> None:
        """Update ghost persona and mood telemetry string."""
        self._ghost_profile_text = profile
        self._ghost_mood_text = mood
        self._ghost_enabled = is_active
        try:
            body = self.query_one("#status-body", Static)
            body.update(self._build_content())
        except Exception:
            pass

    def update_dev_status(self, is_active: bool = True, static_analysis: bool = True) -> None:
        """Update developer assistant subsystem telemetry."""
        self._dev_enabled = is_active
        self._dev_static_analysis = static_analysis
        try:
            body = self.query_one("#status-body", Static)
            body.update(self._build_content())
        except Exception:
            pass

    def _build_content(self) -> str:
        ai_color = "#33ff33" if self._ai_status_text in ("READY", "LOADED") else "#ffaa00"
        if self._ai_status_text in ("OFFLINE", "MISSING", "RUNTIME MISSING"):
            ai_color = "#ff5555"

        ghost_color = "#33ff33" if self._ghost_enabled else "#888888"
        ghost_text = (
            f"{self._ghost_profile_text} ({self._ghost_mood_text.upper()})"
            if self._ghost_enabled
            else "DISABLED"
        )

        dev_color = "#33ff33" if self._dev_enabled else "#888888"
        dev_text = (
            "ACTIVE (ANALYSIS ON)"
            if (self._dev_enabled and self._dev_static_analysis)
            else ("ACTIVE" if self._dev_enabled else "DISABLED")
        )

        return (
            f"[bold #33ff33]GhostTrace[/] [dim]v{self.settings.app_version}[/]\n\n"
            f"[dim #558855]Environment:[/] [bold]{self.settings.env}[/]\n"
            f"[dim #558855]Debug Mode:[/] {self.settings.debug}\n"
            f"[dim #558855]Interface:[/] [bold #33ff33]Textual TUI[/]\n"
            f"[dim #558855]Commands Run:[/] [bold #00ff66]{self._command_count}[/]\n\n"
            "[bold #00aa44]Subsystems:[/]\n"
            " • Foundation: [bold #33ff33]OK[/]\n"
            " • Interface : [bold #33ff33]ACTIVE[/]\n"
            f" • AI Engine : [bold {ai_color}]{self._ai_status_text}[/]\n"
            f" • Persona   : [bold {ghost_color}]{ghost_text}[/]\n"
            f" • Dev Intel : [bold {dev_color}]{dev_text}[/]\n"
            " • Guardian  : [dim #667766]STEP 06[/]\n"
            " • Memory    : [dim #667766]STEP 07[/]\n"
        )
