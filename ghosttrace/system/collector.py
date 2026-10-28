"""Central read-only system telemetry collector with configurable caching."""

from __future__ import annotations

import logging
import time

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.system.cpu import CpuCollector
from ghosttrace.system.disk import get_disk_info
from ghosttrace.system.memory import get_memory_info
from ghosttrace.system.platform_info import get_platform_info
from ghosttrace.system.processes import get_process_info
from ghosttrace.system.schemas import (
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    PlatformInfo,
    ProcessInfo,
    SystemSnapshot,
    UptimeInfo,
)
from ghosttrace.system.uptime import get_uptime_info

logger = logging.getLogger(__name__)


class SystemCollector:
    """Coordinates on-demand resource metric collection with TTL-based caching."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.cpu_collector = CpuCollector()
        self._cached_snapshot: SystemSnapshot | None = None
        self._cache_expires_at: float = 0.0

    @property
    def cache_ttl(self) -> float:
        """Cache duration in seconds."""
        return float(getattr(self.settings, "system_cache_seconds", 3.0))

    def get_platform(self) -> PlatformInfo:
        """Collect platform and runtime metadata."""
        include_host = bool(getattr(self.settings, "system_include_hostname", False))
        return get_platform_info(include_hostname=include_host)

    def get_cpu(self) -> CpuInfo:
        """Sample processor metrics."""
        return self.cpu_collector.get_cpu_info()

    def get_memory(self) -> MemoryInfo:
        """Sample physical RAM and page-file metrics."""
        return get_memory_info()

    def get_disk(self) -> DiskInfo:
        """Sample disk usage on application storage drives."""
        return get_disk_info(settings=self.settings)

    def get_processes(self) -> ProcessInfo:
        """Collect aggregate process count and GhostTrace footprint."""
        return get_process_info()

    def get_uptime(self) -> UptimeInfo:
        """Calculate system and application uptime."""
        return get_uptime_info()

    def get_snapshot(self, force_refresh: bool = False) -> SystemSnapshot:
        """Collect a unified system snapshot, returning cached results if within TTL."""
        now = time.time()
        if not force_refresh and self._cached_snapshot is not None and now < self._cache_expires_at:
            return self._cached_snapshot

        platform = self.get_platform()
        cpu = self.get_cpu()
        memory = self.get_memory()
        disk = self.get_disk()
        processes = self.get_processes()
        uptime = self.get_uptime()

        snapshot = SystemSnapshot(
            platform=platform,
            cpu=cpu,
            memory=memory,
            disk=disk,
            processes=processes,
            uptime=uptime,
            collected_at=now,
        )

        self._cached_snapshot = snapshot
        self._cache_expires_at = now + self.cache_ttl
        return snapshot
