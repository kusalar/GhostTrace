"""CPU metadata, core counts, model identification, and utilization collection."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import sys
import time

from ghosttrace.system.schemas import CpuInfo

logger = logging.getLogger(__name__)


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint), ("dwHighDateTime", ctypes.c_uint)]


def _filetime_to_int(ft: _FILETIME) -> int:
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


class CpuCollector:
    """Non-blocking, cached CPU metrics collector using Win32 API and standard library."""

    def __init__(self) -> None:
        self._last_idle: int | None = None
        self._last_kernel: int | None = None
        self._last_user: int | None = None
        self._last_sample_time: float = 0.0
        self._model_name: str | None = None

    def get_model_name(self) -> str:
        """Retrieve CPU model/brand string from Windows registry or platform fallback."""
        if self._model_name is not None:
            return self._model_name

        model = ""
        if sys.platform == "win32":
            try:
                import winreg

                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                )
                raw_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                if isinstance(raw_name, str):
                    model = " ".join(raw_name.split())
            except Exception as err:
                logger.debug("Failed reading CPU model from registry: %s", err)

        if not model:
            proc = platform.processor()
            model = proc.strip() if proc else "Unknown CPU"

        self._model_name = model
        return model

    def sample_cpu_percent(self, fallback_interval: float = 0.05) -> float | None:
        """Sample CPU usage percentage.

        If a previous sample exists and at least 50ms has elapsed, calculates the delta
        immediately without sleeping. Otherwise, takes a short sample using fallback_interval.
        """
        if sys.platform != "win32":
            return None

        try:
            kernel32 = ctypes.windll.kernel32
            idle = _FILETIME()
            kernel = _FILETIME()
            user = _FILETIME()

            if not kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                return None

            curr_idle = _filetime_to_int(idle)
            curr_kernel = _filetime_to_int(kernel)
            curr_user = _filetime_to_int(user)
            curr_time = time.time()

            # If we don't have a previous sample, sleep briefly once to establish a baseline
            if (
                self._last_idle is None
                or self._last_kernel is None
                or self._last_user is None
                or (curr_time - self._last_sample_time) < 0.05
            ):
                time.sleep(fallback_interval)
                idle2 = _FILETIME()
                kernel2 = _FILETIME()
                user2 = _FILETIME()
                if not kernel32.GetSystemTimes(
                    ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2)
                ):
                    return None
                prev_idle = curr_idle
                prev_kernel = curr_kernel
                prev_user = curr_user
                curr_idle = _filetime_to_int(idle2)
                curr_kernel = _filetime_to_int(kernel2)
                curr_user = _filetime_to_int(user2)
            else:
                prev_idle = self._last_idle
                prev_kernel = self._last_kernel
                prev_user = self._last_user

            self._last_idle = curr_idle
            self._last_kernel = curr_kernel
            self._last_user = curr_user
            self._last_sample_time = time.time()

            delta_idle = curr_idle - prev_idle
            delta_kernel = curr_kernel - prev_kernel
            delta_user = curr_user - prev_user
            delta_total = delta_kernel + delta_user

            if delta_total <= 0:
                return 0.0

            usage = (1.0 - (delta_idle / delta_total)) * 100.0
            return round(max(0.0, min(100.0, usage)), 1)
        except Exception as err:
            logger.debug("Failed measuring CPU utilization: %s", err)
            return None

    def get_cpu_info(self, sample_interval: float = 0.05) -> CpuInfo:
        """Collect all CPU attributes into a CpuInfo schema."""
        logical_cores = os.cpu_count()
        model_name = self.get_model_name()
        usage = self.sample_cpu_percent(fallback_interval=sample_interval)

        return CpuInfo(
            logical_cores=logical_cores,
            physical_cores=None,
            cpu_percent=usage,
            model_name=model_name,
            timestamp=time.time(),
        )


_DEFAULT_CPU_COLLECTOR: CpuCollector | None = None


def get_cpu_info(sample_interval: float = 0.05) -> CpuInfo:
    """Module-level entry point returning CPU metrics using a singleton collector."""
    global _DEFAULT_CPU_COLLECTOR
    if _DEFAULT_CPU_COLLECTOR is None:
        _DEFAULT_CPU_COLLECTOR = CpuCollector()
    return _DEFAULT_CPU_COLLECTOR.get_cpu_info(sample_interval=sample_interval)
