"""Disk space and drive volume metrics collection."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.system.schemas import DiskDrive, DiskInfo

logger = logging.getLogger(__name__)


def get_disk_info(
    paths: list[Path | str] | None = None, settings: Settings | None = None
) -> DiskInfo:
    """Collect disk capacity and utilization metrics for relevant application storage paths.

    Inspects the project installation drive and the application data directory drive by default.
    Handles missing paths, permission denials, and unmounted drives gracefully without crashing.
    """
    cfg = settings or get_settings()
    drives: list[DiskDrive] = []
    seen_anchors: set[str] = set()

    # Default targets: current working directory / repo root and application data directory
    targets: list[Path] = []
    if paths:
        targets.extend(Path(p) for p in paths)
    else:
        targets.append(Path.cwd())
        targets.append(cfg.app_data_dir)

    for target in targets:
        try:
            resolved = Path(target).resolve()
            anchor = resolved.anchor or str(resolved)
            if anchor in seen_anchors:
                continue
            seen_anchors.add(anchor)

            usage = shutil.disk_usage(resolved)
            total = usage.total
            used = usage.used
            free = usage.free
            percent = round((used / total) * 100.0, 1) if total > 0 else 0.0
            total_gb = round(total / (1024**3), 1)
            free_gb = round(free / (1024**3), 1)

            drives.append(
                DiskDrive(
                    path=anchor,
                    total_bytes=total,
                    used_bytes=used,
                    free_bytes=free,
                    percent_used=percent,
                    total_gb=total_gb,
                    free_gb=free_gb,
                )
            )
        except (OSError, PermissionError, ValueError) as err:
            logger.debug("Could not determine disk usage for target '%s': %s", target, err)

    return DiskInfo(drives=drives, timestamp=time.time())
