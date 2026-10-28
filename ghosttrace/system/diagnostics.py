"""Structured diagnostic report compilation and safe sanitised export."""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from ghosttrace import __version__
from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.system.collector import SystemCollector
from ghosttrace.system.health import HealthRegistry
from ghosttrace.system.schemas import DiagnosticReport

logger = logging.getLogger(__name__)


class DiagnosticsGenerator:
    """Generates structured diagnostic reports and handles safe sanitised JSON export."""

    def __init__(
        self,
        settings: Settings | None = None,
        collector: SystemCollector | None = None,
        health_registry: HealthRegistry | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.collector = collector or SystemCollector(self.settings)
        self.health_registry = health_registry or HealthRegistry(self.settings)

    def generate_report(
        self,
        ai_engine: object | None = None,
        ghost_engine: object | None = None,
        dev_engine: object | None = None,
        guardian_engine: object | None = None,
        memory_engine: object | None = None,
        force_refresh: bool = False,
    ) -> DiagnosticReport:
        """Compile a complete point-in-time diagnostic report."""
        snapshot = self.collector.get_snapshot(force_refresh=force_refresh)
        health = self.health_registry.check_all(
            ai_engine=ai_engine,
            ghost_engine=ghost_engine,
            dev_engine=dev_engine,
            guardian_engine=guardian_engine,
            memory_engine=memory_engine,
        )
        snapshot.health = health

        warnings: list[str] = []
        unavailable: list[str] = []

        if snapshot.cpu.cpu_percent is None:
            unavailable.append("CPU utilization measurement unavailable on this host")
        if snapshot.processes.total_processes is None:
            unavailable.append("Process count enumeration unavailable on this host")
        if snapshot.uptime.system_uptime_seconds is None:
            unavailable.append("Operating system uptime measurement unavailable")

        # Health warnings
        for sub_name, sub in health.subsystems.items():
            if sub.status.value in ("ERROR", "DEGRADED", "UNAVAILABLE"):
                warnings.append(f"[{sub.status.value}] Subsystem '{sub_name}': {sub.details}")

        # Resource warnings
        if snapshot.memory.percent_used >= 90.0:
            warnings.append(
                f"High physical RAM load: {snapshot.memory.percent_used}% used "
                f"({snapshot.memory.available_gb} GB available)"
            )
        for drive in snapshot.disk.drives:
            if drive.percent_used >= 95.0:
                warnings.append(
                    f"Critically low disk space on drive '{drive.path}': "
                    f"{drive.free_gb} GB free ({drive.percent_used}% used)"
                )

        return DiagnosticReport(
            app_name=self.settings.app_name,
            app_version=__version__,
            python_version=sys.version.split()[0],
            snapshot=snapshot,
            warnings=warnings,
            unavailable_metrics=unavailable,
            generated_at=time.time(),
        )

    def export_report_json(
        self,
        report: DiagnosticReport,
        target_path: Path | str,
        overwrite: bool = False,
    ) -> Path:
        """Safely export sanitised diagnostic report to a JSON file.

        Guarantees:
        - Never includes secrets, passwords, environment variables, or tokens.
        - Never includes conversation text or persistent memories.
        - Rejects overwriting existing files unless overwrite=True.
        """
        dest = Path(target_path).resolve()
        if dest.exists() and not overwrite:
            msg = f"Target file already exists: {dest}. Specify overwrite to replace."
            raise FileExistsError(msg)

        dest.parent.mkdir(parents=True, exist_ok=True)
        data = report.model_dump(mode="json")

        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Exported diagnostic report to %s", dest)
        return dest
