"""High-resolution thread and timing diagnostics for GhostTrace TUI forensic investigation.

Writes timing, thread identity, and execution trace to a file without writing to stdout/stderr.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

_DIAG_FILE_PATH: Path | None = None
_DIAG_LOCK = threading.Lock()
_START_TIME = time.perf_counter()


def get_diag_log_path() -> Path:
    """Return the absolute path of the diagnostic log file."""
    global _DIAG_FILE_PATH
    if _DIAG_FILE_PATH is None:
        local_app = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        diag_dir = local_app / "GhostTrace" / "logs"
        diag_dir.mkdir(parents=True, exist_ok=True)
        _DIAG_FILE_PATH = diag_dir / "tui_diagnostics.log"
    return _DIAG_FILE_PATH


def diag_log(tag: str, detail: str = "") -> None:
    """Write timestamped, thread-identified diagnostic trace entry to log file."""
    now = time.perf_counter() - _START_TIME
    tid = threading.get_ident()
    tname = threading.current_thread().name
    line = f"{now:10.4f} [TID:{tid:<6} {tname:<16}] [{tag:<24}] {detail}\n"

    try:
        log_path = get_diag_log_path()
        with _DIAG_LOCK, open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
    except Exception:
        pass


def clear_diag_log() -> None:
    """Clear diagnostic log file for a fresh trace run."""
    try:
        log_path = get_diag_log_path()
        with _DIAG_LOCK, open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== GHOSTTRACE FORENSIC DIAGNOSTIC TRACE STARTED AT {time.ctime()} ===\n")
    except Exception:
        pass
