"""Audio settings and experience mode control modal for GhostTrace terminal UI."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from ghosttrace.audio.adapter import AudioEventAdapter
    from ghosttrace.audio.manager import AudioManager


class AudioSettingsModal(ModalScreen[None]):
    """Modal screen displaying audio status, volume sliders, and experience controls."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss_modal", "Close", show=True),
        Binding("t", "test_sound", "Test Sound", show=True),
        Binding("m", "toggle_mute", "Toggle Mute", show=True),
        Binding("e", "toggle_enable", "Toggle Enable", show=True),
        Binding("k", "toggle_keystrokes", "Toggle Keystrokes", show=True),
        Binding("w", "toggle_whispers", "Toggle Whispers", show=True),
        Binding("+", "vol_up", "Vol +", show=False),
        Binding("-", "vol_down", "Vol -", show=False),
    ]

    DEFAULT_CSS = """
    AudioSettingsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.80);
    }
    #audio-dialog {
        width: 76;
        height: auto;
        border: heavy #00ff66;
        background: #080c0a;
        padding: 1 2;
    }
    #audio-title {
        color: #00ff66;
        text-style: bold;
        text-align: center;
        border-bottom: solid #00441b;
        margin-bottom: 1;
    }
    #audio-details {
        color: #bbddbb;
        margin-bottom: 1;
    }
    .action-row {
        width: 100%;
        height: 3;
        align: center middle;
        layout: horizontal;
        margin-top: 1;
    }
    .control-btn {
        background: #00441b;
        color: #00ff66;
        border: solid #00aa44;
        margin: 0 1;
        min-width: 12;
    }
    .control-btn:focus {
        background: #006622;
        color: #ffffff;
    }
    #btn-close {
        background: #222222;
        color: #aaaaaa;
        border: solid #444444;
        margin-top: 1;
    }
    #btn-close:focus {
        background: #444444;
        color: #ffffff;
    }
    """

    def __init__(
        self,
        audio_manager: AudioManager,
        audio_adapter: AudioEventAdapter | None = None,
        experience_mode: str = "normal",
    ) -> None:
        super().__init__()
        self.audio_manager = audio_manager
        self.audio_adapter = audio_adapter
        self.experience_mode = experience_mode

    def compose(self) -> ComposeResult:
        with Container(id="audio-dialog"):
            yield Static("GHOSTTRACE AUDIO CONTROLS", id="audio-title")
            yield Static(self._render_details(), id="audio-details")

            with Horizontal(classes="action-row"):
                yield Button(
                    "Disable" if self.audio_manager.settings.audio_enabled else "Enable",
                    id="btn-toggle-enable",
                    classes="control-btn",
                )
                yield Button(
                    "Unmute" if self.audio_manager._is_muted else "Mute",
                    id="btn-toggle-mute",
                    classes="control-btn",
                )
                yield Button(
                    "Keystrokes: ON"
                    if self.audio_manager.settings.audio_haunted_keystrokes_enabled
                    else "Keystrokes: OFF",
                    id="btn-toggle-keystrokes",
                    classes="control-btn",
                )
                yield Button(
                    "Whispers: ON"
                    if self.audio_manager.settings.audio_scheduled_whispers_enabled
                    else "Whispers: OFF",
                    id="btn-toggle-whispers",
                    classes="control-btn",
                )
                yield Button("Test Sound", id="btn-test-sound", classes="control-btn")

            with Horizontal(classes="action-row"):
                yield Static("[dim]Master Vol:[/] ", classes="vol-label")
                yield Button("-10%", id="btn-vol-down", classes="control-btn")
                yield Button("+10%", id="btn-vol-up", classes="control-btn")
                yield Button("50%", id="btn-vol-50", classes="control-btn")
                yield Button("100%", id="btn-vol-100", classes="control-btn")

            with Horizontal(classes="action-row"):
                yield Static("[dim]Ambient Vol:[/] ", classes="vol-label")
                yield Button("-10%", id="btn-amb-down", classes="control-btn")
                yield Button("+10%", id="btn-amb-up", classes="control-btn")
                yield Button("20%", id="btn-amb-20", classes="control-btn")
                yield Button("50%", id="btn-amb-50", classes="control-btn")

            with Horizontal(classes="action-row"):
                yield Button("Close (Esc)", id="btn-close", classes="control-btn")

    def _render_details(self) -> str:
        st = self.audio_manager.get_status()
        state_badge = (
            "[bold #00ff66]ENABLED[/]" if st.enabled else "[dim #ff5555]DISABLED (SILENT)[/]"
        )
        mute_badge = "[bold #ffaa00]MUTED[/]" if st.is_muted else "[bold #00ff66]ACTIVE[/]"
        device_badge = (
            "[bold #00ff66]AVAILABLE (READY)[/]"
            if st.backend_available
            else "[dim #ffaa00]NO DEVICE DETECTED[/]"
        )

        vol_bar = self._render_meter(st.volume)
        amb_bar = self._render_meter(st.ambient_volume)

        exp_mode = (
            self.audio_adapter.experience_mode
            if self.audio_adapter
            else self.experience_mode.upper()
        )
        policy_desc = {
            "normal": "Standard event sounds | Ambient loop inactive",
            "ambient": "Ambient loop active | Standard event sounds",
            "haunted": "Horror event sounds | Subtle ambient draft active",
            "focus": "Focus Mode: Non-essential audio suppressed | Guardian active",
        }.get(exp_mode.lower(), "Standard event sounds")

        keystrokes_badge = (
            "[bold #00ff66]ON[/]"
            if self.audio_manager.settings.audio_haunted_keystrokes_enabled
            else "[dim #ff5555]OFF[/]"
        )
        whispers_badge = (
            "[bold #00ff66]ON[/]"
            if self.audio_manager.settings.audio_scheduled_whispers_enabled
            else "[dim #ff5555]OFF[/]"
        )
        lines = [
            f"  Subsystem State    : {state_badge} (Mute: {mute_badge})",
            f"  Audio Backend      : [cyan]{st.backend_type.upper()}[/] ({device_badge})",
            f"  Master Volume      : {vol_bar} [bold]{int(st.volume * 100)}%[/]",
            f"  Ambient Volume     : {amb_bar} [bold]{int(st.ambient_volume * 100)}%[/]",
            f"  Haunted Keystrokes : {keystrokes_badge} (Typing effects)",
            f"  Scheduled Whispers : {whispers_badge} (Atmospheric cues)",
            f"  Experience Mode    : [bold #00ff66]{exp_mode.upper()}[/] — {policy_desc}",
        ]
        return "\n".join(lines)

    def _render_meter(self, val: float, width: int = 16) -> str:
        filled = round(val * width)
        empty = width - filled
        return f"[{'#' * filled}{'.' * empty}]"

    def _refresh_display(self) -> None:
        try:
            details_widget = self.query_one("#audio-details", Static)
            details_widget.update(self._render_details())

            enable_btn = self.query_one("#btn-toggle-enable", Button)
            enable_btn.label = "Disable" if self.audio_manager.settings.audio_enabled else "Enable"

            mute_btn = self.query_one("#btn-toggle-mute", Button)
            mute_btn.label = "Unmute" if self.audio_manager._is_muted else "Mute"

            keystrokes_btn = self.query_one("#btn-toggle-keystrokes", Button)
            keystrokes_btn.label = (
                "Keystrokes: ON"
                if self.audio_manager.settings.audio_haunted_keystrokes_enabled
                else "Keystrokes: OFF"
            )

            whispers_btn = self.query_one("#btn-toggle-whispers", Button)
            whispers_btn.label = (
                "Whispers: ON"
                if self.audio_manager.settings.audio_scheduled_whispers_enabled
                else "Whispers: OFF"
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-close":
            self.dismiss()
        elif btn_id == "btn-toggle-enable":
            self.action_toggle_enable()
        elif btn_id == "btn-toggle-mute":
            self.action_toggle_mute()
        elif btn_id == "btn-toggle-keystrokes":
            self.action_toggle_keystrokes()
        elif btn_id == "btn-toggle-whispers":
            self.action_toggle_whispers()
        elif btn_id == "btn-test-sound":
            self.action_test_sound()
        elif btn_id == "btn-vol-down":
            self.action_vol_down()
        elif btn_id == "btn-vol-up":
            self.action_vol_up()
        elif btn_id == "btn-vol-50":
            self.audio_manager.set_volume(0.50, persist=True)
            self._refresh_display()
        elif btn_id == "btn-vol-100":
            self.audio_manager.set_volume(1.00, persist=True)
            self._refresh_display()
        elif btn_id == "btn-amb-down":
            new_v = max(0.0, self.audio_manager._ambient_volume - 0.10)
            self.audio_manager.set_ambient_volume(round(new_v, 2), persist=True)
            self._refresh_display()
        elif btn_id == "btn-amb-up":
            new_v = min(1.0, self.audio_manager._ambient_volume + 0.10)
            self.audio_manager.set_ambient_volume(round(new_v, 2), persist=True)
            self._refresh_display()
        elif btn_id == "btn-amb-20":
            self.audio_manager.set_ambient_volume(0.20, persist=True)
            self._refresh_display()
        elif btn_id == "btn-amb-50":
            self.audio_manager.set_ambient_volume(0.50, persist=True)
            self._refresh_display()

    @work(thread=True)
    def action_toggle_enable(self) -> None:
        """Toggle audio enabled state in background thread to prevent UI freezing."""
        if self.audio_manager.settings.audio_enabled:
            self.audio_manager.disable(persist=True)
        else:
            self.audio_manager.enable(persist=True)
        self.app.call_from_thread(self._refresh_display)

    def action_toggle_mute(self) -> None:
        """Toggle mute state immediately."""
        if self.audio_manager._is_muted:
            self.audio_manager.unmute(persist=True)
        else:
            self.audio_manager.mute(persist=True)
        self._refresh_display()

    def action_vol_up(self) -> None:
        new_v = min(1.0, self.audio_manager._volume + 0.10)
        self.audio_manager.set_volume(round(new_v, 2), persist=True)
        self._refresh_display()

    def action_vol_down(self) -> None:
        new_v = max(0.0, self.audio_manager._volume - 0.10)
        self.audio_manager.set_volume(round(new_v, 2), persist=True)
        self._refresh_display()

    @work(thread=True)
    def action_test_sound(self) -> None:
        """Play short test sound effect in background thread."""
        self.audio_manager.play_test_sound()

    def action_toggle_keystrokes(self) -> None:
        """Toggle haunted keystrokes state immediately and persist preferences."""
        curr = self.audio_manager.settings.audio_haunted_keystrokes_enabled
        self.audio_manager.set_haunted_keystrokes(not curr, persist=True)
        self._refresh_display()

    def action_toggle_whispers(self) -> None:
        """Toggle scheduled whispers state immediately and persist preferences."""
        curr = self.audio_manager.settings.audio_scheduled_whispers_enabled
        self.audio_manager.set_scheduled_whispers(not curr, persist=True)
        self._refresh_display()

    def action_dismiss_modal(self) -> None:
        self.dismiss()
