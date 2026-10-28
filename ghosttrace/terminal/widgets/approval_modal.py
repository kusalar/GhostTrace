"""Command execution approval modal dialog for GhostTrace terminal UI."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ghosttrace.guardian.explanations import get_risk_badge
from ghosttrace.guardian.schemas import ApprovalRequest


class CommandApprovalModal(ModalScreen[bool]):
    """Modal dialog displaying command preview and requesting explicit user approval."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("y", "confirm", "Confirm Execution", show=True),
        Binding("enter", "confirm", "Confirm Execution", show=False),
        Binding("n", "cancel", "Cancel", show=True),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    CommandApprovalModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #modal-dialog {
        width: 74;
        height: auto;
        border: heavy #00ff66;
        background: #080c0a;
        padding: 1 2;
    }
    #modal-title {
        color: #00ff66;
        text-style: bold;
        text-align: center;
        border-bottom: solid #00441b;
        margin-bottom: 1;
    }
    #modal-details {
        color: #bbddbb;
        margin-bottom: 1;
    }
    #modal-actions {
        width: 100%;
        height: 3;
        align: center middle;
        layout: horizontal;
        margin-top: 1;
    }
    #btn-confirm {
        background: #00441b;
        color: #00ff66;
        border: solid #00aa44;
        margin-right: 2;
    }
    #btn-confirm:focus {
        background: #006622;
        color: #ffffff;
    }
    #btn-cancel {
        background: #331111;
        color: #ff6666;
        border: solid #882222;
    }
    #btn-cancel:focus {
        background: #551111;
        color: #ffffff;
    }
    """

    def __init__(
        self,
        request: ApprovalRequest,
        timeout_seconds: int = 30,
        max_output_chars: int = 12000,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.request = request
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def compose(self) -> ComposeResult:
        with Container(id="modal-dialog"):
            yield Static("COMMAND EXECUTION APPROVAL REQUIRED", id="modal-title")

            badge = get_risk_badge(self.request.analysis.risk_level)
            args_str = " ".join(self.request.analysis.args)
            reasons = "\n".join(f" • {r}" for r in self.request.analysis.risk_reasons)
            side_effects = (
                "\n".join(f" • {s}" for s in self.request.analysis.side_effects) or " • None noted"
            )

            body_text = (
                "[bold #ffffff]Command:[/] "
                f"[bold #00ff66]{self.request.analysis.original_command}[/]\n"
                f"[bold #ffffff]Executable:[/] {self.request.analysis.executable or 'NONE'} "
                f"[dim]({self.request.analysis.resolved_executable_path or 'not found'})[/]\n"
                f"[bold #ffffff]Arguments:[/] {args_str or '(none)'}\n"
                f"[bold #ffffff]Working Dir:[/] [dim]{self.request.working_dir}[/]\n"
                f"[bold #ffffff]Risk Level:[/] {badge}\n"
                f"[bold #ffffff]Timeout Limit:[/] {self.timeout_seconds}s  "
                f"[bold #ffffff]Output Limit:[/] {self.max_output_chars} chars\n\n"
                f"[bold #00aa44]Risk Assessment:[/]\n{reasons}\n\n"
                f"[bold #00aa44]Expected Side Effects:[/]\n{side_effects}\n"
            )

            yield Static(body_text, id="modal-details")

            with Horizontal(id="modal-actions"):
                yield Button("Confirm [Y]", id="btn-confirm")
                yield Button("Cancel [N]", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.action_confirm()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
