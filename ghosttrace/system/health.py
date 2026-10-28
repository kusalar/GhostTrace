"""Internal GhostTrace subsystem diagnostic health registry and validation."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.system.schemas import HealthStatus, SubsystemHealth, SystemHealthReport

logger = logging.getLogger(__name__)


class HealthRegistry:
    """Non-destructive diagnostic health registry inspecting GhostTrace subsystems.

    Guarantees:
    - Never triggers model loading or inference.
    - Never executes commands.
    - Never modifies Guardian policies.
    - Never writes to registered project directories.
    - Reports disabled features as DISABLED, not ERROR.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def check_configuration(self) -> SubsystemHealth:
        """Validate application configuration integrity."""
        try:
            env = self.settings.env
            debug = self.settings.debug
            return SubsystemHealth(
                name="configuration",
                status=HealthStatus.HEALTHY,
                details=f"Environment: {env}, Debug: {debug}",
                checked_at=time.time(),
            )
        except Exception as err:
            return SubsystemHealth(
                name="configuration",
                status=HealthStatus.ERROR,
                details=f"Config validation error: {err}",
                checked_at=time.time(),
            )

    def check_ai_runtime(self) -> SubsystemHealth:
        """Check whether llama-cpp-python is installed and importable without loading models."""
        try:
            import llama_cpp  # noqa: F401

            return SubsystemHealth(
                name="ai_runtime",
                status=HealthStatus.HEALTHY,
                details="llama-cpp-python runtime is installed and importable",
                checked_at=time.time(),
            )
        except ImportError:
            return SubsystemHealth(
                name="ai_runtime",
                status=HealthStatus.DEGRADED,
                details="llama-cpp-python is not installed (mock inference fallback active)",
                checked_at=time.time(),
            )
        except Exception as err:
            return SubsystemHealth(
                name="ai_runtime",
                status=HealthStatus.ERROR,
                details=f"Runtime error checking llama-cpp-python: {err}",
                checked_at=time.time(),
            )

    def check_ai_engine(self, ai_engine: object | None = None) -> SubsystemHealth:
        """Inspect AI engine initialized status."""
        if not self.settings.ai_enabled:
            return SubsystemHealth(
                name="ai_engine",
                status=HealthStatus.DISABLED,
                details="AI engine disabled in settings (GHOSTTRACE_AI_ENABLED=false)",
                checked_at=time.time(),
            )

        if ai_engine is None:
            return SubsystemHealth(
                name="ai_engine",
                status=HealthStatus.HEALTHY,
                details="Configured and enabled (standby)",
                checked_at=time.time(),
            )

        try:
            # Check status without loading model
            get_status = getattr(ai_engine, "get_status", None)
            if callable(get_status):
                status_obj = get_status()
                runtime = getattr(status_obj, "runtime_available", False)
                loaded = getattr(status_obj, "is_loaded", False)
                state_str = "loaded" if loaded else "standby"
                runtime_str = "available" if runtime else "missing"
                return SubsystemHealth(
                    name="ai_engine",
                    status=HealthStatus.HEALTHY if runtime else HealthStatus.DEGRADED,
                    details=f"AI engine {state_str} (runtime: {runtime_str})",
                    checked_at=time.time(),
                )
            return SubsystemHealth(
                name="ai_engine",
                status=HealthStatus.HEALTHY,
                details="AI engine active",
                checked_at=time.time(),
            )
        except Exception as err:
            return SubsystemHealth(
                name="ai_engine",
                status=HealthStatus.ERROR,
                details=f"Failed inspecting AI engine: {err}",
                checked_at=time.time(),
            )

    def check_model_file(self) -> SubsystemHealth:
        """Verify configured model file existence on disk (strictly read-only stat check)."""
        model_path = Path(self.settings.model_path)
        if model_path.is_file():
            try:
                size_mb = round(model_path.stat().st_size / (1024 * 1024), 1)
                return SubsystemHealth(
                    name="model_file",
                    status=HealthStatus.HEALTHY,
                    details=f"Present ({size_mb} MB) at {model_path.name}",
                    checked_at=time.time(),
                )
            except OSError:
                return SubsystemHealth(
                    name="model_file",
                    status=HealthStatus.HEALTHY,
                    details=f"File present at {model_path.name}",
                    checked_at=time.time(),
                )
        return SubsystemHealth(
            name="model_file",
            status=HealthStatus.DEGRADED,
            details=f"GGUF model file not found at {model_path.name} (fallback inference active)",
            checked_at=time.time(),
        )

    def check_model_loaded(self, ai_engine: object | None = None) -> SubsystemHealth:
        """Inspect whether model weights are currently resident in RAM.

        Strict invariant: Does NOT trigger load_model() or allocate weights.
        """
        if ai_engine is None:
            return SubsystemHealth(
                name="model_loaded",
                status=HealthStatus.HEALTHY,
                details="Unloaded (on-demand loading enabled)",
                checked_at=time.time(),
            )

        mgr = getattr(ai_engine, "model_manager", None)
        if mgr and hasattr(mgr, "is_loaded"):
            loaded = mgr.is_loaded()
            return SubsystemHealth(
                name="model_loaded",
                status=HealthStatus.HEALTHY,
                details="Loaded in memory" if loaded else "Unloaded (on-demand loading enabled)",
                checked_at=time.time(),
            )
        return SubsystemHealth(
            name="model_loaded",
            status=HealthStatus.HEALTHY,
            details="Unloaded",
            checked_at=time.time(),
        )

    def check_memory_database(self, memory_engine: object | None = None) -> SubsystemHealth:
        """Inspect persistent SQLite database connectivity and schema readiness."""
        if not self.settings.memory_enabled:
            return SubsystemHealth(
                name="memory_db",
                status=HealthStatus.DISABLED,
                details="Persistent memory disabled in settings",
                checked_at=time.time(),
            )

        db_path = self.settings.memory_database_path
        if db_path is None or not Path(db_path).exists():
            return SubsystemHealth(
                name="memory_db",
                status=HealthStatus.HEALTHY,
                details="Database uninitialized (will initialize automatically on first write)",
                checked_at=time.time(),
            )

        try:
            import sqlite3

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1.0)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
            tbl_count = cur.fetchone()[0]
            conn.close()
            return SubsystemHealth(
                name="memory_db",
                status=HealthStatus.HEALTHY,
                details=f"SQLite connected ({tbl_count} tables)",
                checked_at=time.time(),
            )
        except Exception as err:
            return SubsystemHealth(
                name="memory_db",
                status=HealthStatus.ERROR,
                details=f"Database connectivity check failed: {err}",
                checked_at=time.time(),
            )

    def check_memory_wal(self) -> SubsystemHealth:
        """Inspect whether SQLite database is operating in WAL journal mode."""
        if not self.settings.memory_enabled:
            return SubsystemHealth(
                name="memory_wal",
                status=HealthStatus.DISABLED,
                details="Memory disabled",
                checked_at=time.time(),
            )

        db_path = self.settings.memory_database_path
        if db_path is None or not Path(db_path).exists():
            return SubsystemHealth(
                name="memory_wal",
                status=HealthStatus.HEALTHY,
                details="WAL mode will activate on database creation",
                checked_at=time.time(),
            )

        try:
            import sqlite3

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1.0)
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            mode = cur.fetchone()[0]
            conn.close()
            is_wal = str(mode).lower() == "wal"
            return SubsystemHealth(
                name="memory_wal",
                status=HealthStatus.HEALTHY if is_wal else HealthStatus.DEGRADED,
                details=f"Journal mode: {mode.upper()}",
                checked_at=time.time(),
            )
        except Exception as err:
            return SubsystemHealth(
                name="memory_wal",
                status=HealthStatus.DEGRADED,
                details=f"Could not read journal mode: {err}",
                checked_at=time.time(),
            )

    def check_project_context(self, memory_engine: object | None = None) -> SubsystemHealth:
        """Inspect project registration and indexing subsystem state."""
        if not self.settings.project_enabled:
            return SubsystemHealth(
                name="project_context",
                status=HealthStatus.DISABLED,
                details="Project indexing disabled in settings",
                checked_at=time.time(),
            )

        if memory_engine is not None and hasattr(memory_engine, "get_active_project"):
            active = memory_engine.get_active_project()
            if active:
                return SubsystemHealth(
                    name="project_context",
                    status=HealthStatus.HEALTHY,
                    details=f"Active project: '{active.name}' ({active.root_path})",
                    checked_at=time.time(),
                )
            return SubsystemHealth(
                name="project_context",
                status=HealthStatus.HEALTHY,
                details="No active project selected (standby)",
                checked_at=time.time(),
            )

        return SubsystemHealth(
            name="project_context",
            status=HealthStatus.HEALTHY,
            details="Project subsystem ready (standby)",
            checked_at=time.time(),
        )

    def check_ghost_persona(self, ghost_engine: object | None = None) -> SubsystemHealth:
        """Inspect Ghost personality engine status."""
        if not self.settings.ghost_enabled:
            return SubsystemHealth(
                name="ghost_persona",
                status=HealthStatus.DISABLED,
                details="Ghost personality engine disabled in settings",
                checked_at=time.time(),
            )

        profile = getattr(self.settings, "ghost_profile", "unknown")
        mood_enabled = getattr(self.settings, "ghost_mood_enabled", True)
        mood_str = "enabled" if mood_enabled else "disabled"
        return SubsystemHealth(
            name="ghost_persona",
            status=HealthStatus.HEALTHY,
            details=f"Profile: '{profile}', Mood tracking: {mood_str}",
            checked_at=time.time(),
        )

    def check_developer_assistant(self, dev_engine: object | None = None) -> SubsystemHealth:
        """Inspect Developer coding assistance subsystem status."""
        if not self.settings.dev_enabled:
            return SubsystemHealth(
                name="developer_assistant",
                status=HealthStatus.DISABLED,
                details="Developer assistance disabled in settings",
                checked_at=time.time(),
            )

        static_analysis = getattr(self.settings, "dev_static_analysis", True)
        analysis_str = "enabled" if static_analysis else "disabled"
        return SubsystemHealth(
            name="developer_assistant",
            status=HealthStatus.HEALTHY,
            details=f"Code intelligence active (static analysis: {analysis_str})",
            checked_at=time.time(),
        )

    def check_command_guardian(self, guardian_engine: object | None = None) -> SubsystemHealth:
        """Inspect Command Guardian safety subsystem and approval policy."""
        if not self.settings.guard_enabled:
            return SubsystemHealth(
                name="command_guardian",
                status=HealthStatus.DISABLED,
                details="Command Guardian disabled in settings",
                checked_at=time.time(),
            )

        require_appr = getattr(self.settings, "guard_require_approval", True)
        exec_enabled = getattr(self.settings, "guard_execution_enabled", True)
        timeout = getattr(self.settings, "guard_timeout_seconds", 30)

        details = (
            f"Execution: {'enabled' if exec_enabled else 'analysis-only'}, "
            f"Approval required: {'yes' if require_appr else 'no'}, "
            f"Timeout: {timeout}s"
        )
        return SubsystemHealth(
            name="command_guardian",
            status=HealthStatus.HEALTHY,
            details=details,
            checked_at=time.time(),
        )

    def check_haunted_experience(self, haunt_engine: object | None = None) -> SubsystemHealth:
        """Inspect Haunted Experience & Atmospheric Events subsystem status."""
        if not getattr(self.settings, "haunt_enabled", True):
            return SubsystemHealth(
                name="haunted_experience",
                status=HealthStatus.DISABLED,
                details="Haunted experience disabled in settings",
                checked_at=time.time(),
            )

        mode = getattr(self.settings, "haunt_mode", "normal")
        intensity = getattr(self.settings, "haunt_intensity", "medium")
        idle = getattr(self.settings, "haunt_idle_events", False)

        details = (
            f"Mode: '{mode}', Intensity: '{intensity}', "
            f"Idle events: {'enabled' if idle else 'disabled'}"
        )
        return SubsystemHealth(
            name="haunted_experience",
            status=HealthStatus.HEALTHY,
            details=details,
            checked_at=time.time(),
        )

    def check_all(
        self,
        ai_engine: object | None = None,
        ghost_engine: object | None = None,
        dev_engine: object | None = None,
        guardian_engine: object | None = None,
        memory_engine: object | None = None,
        haunt_engine: object | None = None,
    ) -> SystemHealthReport:
        """Execute all non-destructive subsystem health checks and compute overall state."""
        subsystems: dict[str, SubsystemHealth] = {}

        subsystems["configuration"] = self.check_configuration()
        subsystems["ai_runtime"] = self.check_ai_runtime()
        subsystems["ai_engine"] = self.check_ai_engine(ai_engine)
        subsystems["model_file"] = self.check_model_file()
        subsystems["model_loaded"] = self.check_model_loaded(ai_engine)
        subsystems["memory_db"] = self.check_memory_database(memory_engine)
        subsystems["memory_wal"] = self.check_memory_wal()
        subsystems["project_context"] = self.check_project_context(memory_engine)
        subsystems["ghost_persona"] = self.check_ghost_persona(ghost_engine)
        subsystems["developer_assistant"] = self.check_developer_assistant(dev_engine)
        subsystems["command_guardian"] = self.check_command_guardian(guardian_engine)
        subsystems["haunted_experience"] = self.check_haunted_experience(haunt_engine)

        # Derive overall health status
        statuses = [s.status for s in subsystems.values()]
        if any(st == HealthStatus.ERROR for st in statuses):
            overall = HealthStatus.ERROR
            summary = "One or more critical subsystems encountered an error."
        elif any(st == HealthStatus.UNAVAILABLE for st in statuses):
            overall = HealthStatus.DEGRADED
            summary = "One or more subsystems are unavailable."
        elif any(st == HealthStatus.DEGRADED for st in statuses):
            overall = HealthStatus.DEGRADED
            summary = "Operating in degraded mode (fallback active for optional components)."
        elif all(st == HealthStatus.DISABLED for st in statuses):
            overall = HealthStatus.DISABLED
            summary = "All subsystems disabled."
        else:
            overall = HealthStatus.HEALTHY
            summary = "All subsystems operational and healthy."

        return SystemHealthReport(
            overall_status=overall,
            subsystems=subsystems,
            summary=summary,
            timestamp=time.time(),
        )
