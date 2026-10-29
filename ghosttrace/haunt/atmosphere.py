"""Atmospheric terminal styling, ASCII art glyphs, and thematic formatting helpers."""

from __future__ import annotations

# Lightweight ASCII art glyphs for GhostTrace terminal presence
ASCII_GHOST_SMALL = """
  .-.
 (o o)
 | O |
 '~~~'
""".strip()

ASCII_GHOST_PHANTOM = """
 .--.
/ __ \\
| (o)(o)
|   >  |
'~~~~~~'
""".strip()

ASCII_GHOST_GUARDIAN = """
  /\\
 /  \\
| @@ |
 \\__//
  ||
""".strip()

ASCII_GLYPHS = {
    "forgotten-machine": ASCII_GHOST_SMALL,
    "phantom-coder": ASCII_GHOST_PHANTOM,
    "guardian-spirit": ASCII_GHOST_GUARDIAN,
    "default": ASCII_GHOST_SMALL,
}


def get_ascii_ghost(profile_id: str | None = None) -> str:
    """Return a lightweight ASCII ghost glyph appropriate for the active profile."""
    key = (profile_id or "default").lower().replace(" ", "-")
    return ASCII_GLYPHS.get(key, ASCII_GHOST_SMALL)


def format_atmospheric_whisper(text: str, profile_id: str | None = None) -> str:
    """Format an atmospheric whisper with subtle green-phosphor CRT accents."""
    profile_label = (profile_id or "digital-ghost").upper()
    return f"[dim #00aa44]~[ {profile_label} ]~[/] [italic #99eeaa]{text}[/]"


def format_haunt_banner(
    title: str, text: str, glyph: bool = False, profile_id: str | None = None
) -> str:
    """Format an interactive haunted event banner with optional ASCII glyph."""
    lines: list[str] = []
    lines.append(f"[bold #00ff66]* [HAUNTED RESONANCE] :: {title.upper()}[/]")
    if glyph:
        art = get_ascii_ghost(profile_id)
        for line in art.splitlines():
            lines.append(f"[dim #33cc66]  {line}[/]")
    lines.append(f"[italic #aaffbb]{text}[/]")
    return "\n".join(lines)


def format_mood_shift_banner(from_mood: str, to_mood: str, text: str) -> str:
    """Format a subtle mood transition manifestation."""
    return (
        f"[dim #00cc55]• [GHOST RESONANCE SHIFT][/] [bold #33ff33]{from_mood.upper()}[/] "
        f"[dim]->[/] [bold #00ff66]{to_mood.upper()}[/]\n"
        f"[italic #88dd99]{text}[/]"
    )
