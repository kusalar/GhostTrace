"""Conversation scrollable log widget for GhostTrace terminal UI."""

from __future__ import annotations

import uuid

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
    .response-thinking {
        margin-bottom: 1;
        color: #88bb88;
    }
    .response-error {
        margin-bottom: 1;
        color: #ff6666;
    }
    .haunt-event-line {
        margin-top: 1;
        margin-bottom: 1;
        padding: 0 1;
        border-left: wide #00ff66;
        background: #040806;
        color: #aaffbb;
    }
    """

    def compose(self) -> ComposeResult:
        # Initial Welcome Message
        welcome_text = (
            "[bold #00ff66]Something has awakened inside this terminal.[/]\n\n"
            "[dim #779977]GhostTrace is operating in Haunted Terminal mode (Step 09).\n"
            "Powered by Qwen2.5 GGUF via llama.cpp (offline & private).\n"
            "Type natural language queries to ask the local assistant, or\n"
            "type [bold #33ff33]'help'[/] for commands or "
            "[bold #33ff33]'haunt status'[/] for atmospheric experience controls.[/]"
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

    def add_pending_ai_query(self, query: str, widget_id: str | None = None) -> str:
        """Mount user query and initial thinking placeholder, returning widget id."""
        target_id = widget_id or f"ai-resp-{uuid.uuid4().hex[:8]}"

        cmd_widget = Static(
            f"[bold #00ff66]ghost>[/] [bold #ffffff]{query}[/]",
            classes="user-command-line",
        )
        self.mount(cmd_widget)

        thinking_widget = Static(
            "[bold #00ff66]GHOSTTRACE:[/] [dim #779977]Thinking...[/]",
            classes="response-thinking",
            id=target_id,
        )
        self.mount(thinking_widget)
        self.scroll_end(animate=False)
        return target_id

    def update_ai_stream(self, widget_id: str, current_text: str) -> None:
        """Update active streaming text in the target widget."""
        from ghosttrace.core.diagnostics import diag_log

        diag_log("CONV.UPDATE_STREAM.START", f"widget_id={widget_id}")
        try:
            widget = self.query_one(f"#{widget_id}", Static)
            diag_log("CONV.UPDATE_STREAM.WIDGET_FOUND")
            widget.update(f"[bold #00ff66]GHOSTTRACE:[/]\n{current_text}")
            diag_log("CONV.UPDATE_STREAM.WIDGET_UPDATED")
            self.scroll_end(animate=False)
            diag_log("CONV.UPDATE_STREAM.SCROLL_DONE")
        except Exception as exc:
            diag_log("CONV.UPDATE_STREAM.ERROR", str(exc))
            pass

    def update_ai_response(self, widget_id: str, final_text: str, success: bool) -> None:
        """Finalize the AI response widget with full text and appropriate styling."""
        try:
            widget = self.query_one(f"#{widget_id}", Static)
            if success:
                widget.remove_class("response-thinking")
                widget.add_class("response-line")
                widget.update(f"[bold #00ff66]GHOSTTRACE:[/]\n{final_text}")
            else:
                widget.remove_class("response-thinking")
                widget.add_class("response-error")
                widget.update(final_text)
            self.scroll_end(animate=False)
        except Exception:
            pass

    def add_busy_warning(self, query: str) -> None:
        """Display busy warning when user submits a query while inference is running."""
        cmd_widget = Static(
            f"[bold #00ff66]ghost>[/] [bold #ffffff]{query}[/]",
            classes="user-command-line",
        )
        self.mount(cmd_widget)

        busy_widget = Static(
            "[bold #ff6666]GhostTrace is currently generating a response. Please wait.[/]",
            classes="response-error",
        )
        self.mount(busy_widget)
        self.scroll_end(animate=False)

    def add_haunt_event(self, rendered_text: str) -> None:
        """Mount an atmospheric haunted event manifestation into the log."""
        event_widget = Static(rendered_text, classes="haunt-event-line")
        self.mount(event_widget)
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
