"""Conversation scrollable log widget for GhostTrace terminal UI."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from ghosttrace.terminal.command_registry import CommandResult


class ConversationLog(VerticalScroll):
    """Scrollable conversation area displaying submitted commands and system responses."""

    DEFAULT_CSS = """
    ConversationLog {
        width: 1fr;
        height: 1fr;
        background: #080c0a;
        padding: 1 2;
        overflow-y: auto;
    }
    .welcome-box {
        margin-bottom: 1;
        padding: 1 2;
        border: heavy #00441b;
        background: #050807;
        color: #99cc99;
    }
    .user-command-line {
        margin-top: 1;
        color: #00ff66;
        text-style: bold;
    }
    .response-line {
        margin-bottom: 1;
        color: #bbddbb;
    }
    .response-error {
        margin-bottom: 1;
        color: #ff6666;
    }
    """

    def compose(self) -> ComposeResult:
        # Initial Welcome Message
        welcome_text = (
            "[bold #00ff66]Something has awakened inside this terminal.[/]\n\n"
            "[dim #779977]GhostTrace is operating in Step 02 Interactive Terminal mode.\n"
            "AI model inference and ghost persona are currently offline.\n"
            "Type [bold #33ff33]'help'[/] for available commands or "
            "[bold #33ff33]'status'[/] for diagnostics.[/]"
        )
        yield Static(welcome_text, classes="welcome-box", id="welcome-message")

    def add_exchange(self, command: str, result: CommandResult) -> None:
        """Render a user command and the corresponding command output."""
        # 1. User command entry
        cmd_widget = Static(
            f"[bold #00ff66]ghost>[/] [bold #ffffff]{command}[/]",
            classes="user-command-line",
        )
        self.mount(cmd_widget)

        # 2. Response entry
        if result.output != "":
            css_class = "response-line" if result.success else "response-error"
            resp_widget = Static(result.output, classes=css_class)
            self.mount(resp_widget)

        # Scroll to bottom
        self.scroll_end(animate=False)

    def clear_log(self) -> None:
        """Remove all conversational exchanges and display clear confirmation."""
        self.remove_children()
        cleared_note = Static(
            "[dim #558855]--- Conversation buffer cleared ---[/]",
            classes="welcome-box",
        )
        self.mount(cleared_note)
        self.scroll_end(animate=False)
