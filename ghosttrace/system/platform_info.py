"""Host platform and Python runtime metadata collection."""

from __future__ import annotations

import logging
import platform
import socket

from ghosttrace.system.schemas import PlatformInfo

logger = logging.getLogger(__name__)


def get_platform_info(include_hostname: bool = False) -> PlatformInfo:
    """Collect platform architecture, OS version, and Python runtime metadata."""
    os_name = platform.system() or "Unknown"
    os_release = platform.release() or "Unknown"
    os_version = platform.version() or "Unknown"
    architecture = platform.machine() or "Unknown"
    python_version = platform.python_version()
    python_compiler = platform.python_compiler()
    try:
        py_arch = platform.architecture()[0]
    except Exception:
        py_arch = "Unknown"

    hostname: str | None = None
    if include_hostname:
        try:
            hostname = socket.gethostname()
        except Exception as err:
            logger.debug("Failed to retrieve hostname: %s", err)
            hostname = "Unavailable"

    return PlatformInfo(
        os_name=os_name,
        os_release=os_release,
        os_version=os_version,
        architecture=architecture,
        python_version=python_version,
        python_compiler=python_compiler,
        python_executable_arch=py_arch,
        hostname=hostname,
    )
