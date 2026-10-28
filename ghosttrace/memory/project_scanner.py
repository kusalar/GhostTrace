"""Bounded, read-only scanner for authorized development project directories."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ghosttrace.developer.languages import detect_language
from ghosttrace.memory.redaction import redact_sensitive_data

logger = logging.getLogger("ghosttrace.memory.project_scanner")

# Directory names that are strictly excluded from scanning
EXCLUDED_DIRECTORIES: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "coverage",
    ".tox",
    ".idea",
    ".vscode",
    ".gemini",
    "models",
    "bin",
    "obj",
    ".vs",
    ".cache",
}

# Recognized file extensions for indexing
ALLOWED_EXTENSIONS: set[str] = {
    # Programming languages
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".html",
    ".css",
    ".sql",
    ".sh",
    ".bash",
    ".ps1",
    # Documentation and configs
    ".md",
    ".markdown",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".rst",
}

# Explicitly excluded file patterns (credentials, secrets, model weights, binaries)
EXCLUDED_FILE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    "id_rsa",
    "id_ed25519",
    "credentials",
    ".gguf",
    ".bin",
    ".safetensors",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".pyc",
    ".class",
    ".iso",
)


@dataclass(frozen=True)
class ScannedFile:
    """Represents an eligible, read-only scanned project source file."""

    relative_path: str
    content: str
    language: str
    content_hash: str
    size_bytes: int


class ProjectScanner:
    """Safely traverses an authorized project root enforcing strict boundaries and limits."""

    def __init__(
        self,
        max_files: int | object = 500,
        max_file_bytes: int = 262144,
        max_total_bytes: int = 5242880,
        max_depth: int = 12,
    ) -> None:
        if hasattr(max_files, "project_max_files"):
            self.max_files = max_files.project_max_files
            self.max_file_bytes = getattr(max_files, "project_max_file_bytes", 262144)
            self.max_total_bytes = getattr(max_files, "project_max_total_bytes", 5242880)
            self.max_depth = getattr(max_files, "project_max_depth", 12)
        else:
            self.max_files = int(max_files)
            self.max_file_bytes = max_file_bytes
            self.max_total_bytes = max_total_bytes
            self.max_depth = max_depth

    def is_file_eligible(self, relative_path: str, filename: str) -> bool:
        """Check whether a file matches allowed extensions and passes exclusion rules."""
        lower_name = filename.lower()
        lower_path = relative_path.lower()

        # Check secret / excluded file prefixes and extensions
        for pattern in EXCLUDED_FILE_PATTERNS:
            if lower_name.startswith(pattern) or lower_name.endswith(pattern):
                return False
            if f"/{pattern}" in lower_path or f"\\{pattern}" in lower_path:
                return False

        ext = Path(filename).suffix.lower()
        return ext in ALLOWED_EXTENSIONS

    def scan_project(self, root_path: Path | str) -> list[ScannedFile]:
        """Inspect and read all eligible text files within the project root.

        Enforces:
        - Authorized directory containment (no symlink escape)
        - Depth limits
        - File count limits
        - File size limits
        - Total text size ceiling
        - Secret redaction before returning
        """
        resolved_root = Path(root_path).resolve()
        if not resolved_root.is_dir():
            msg = f"Project root '{root_path}' is not a valid directory."
            raise ValueError(msg)

        scanned_files: list[ScannedFile] = []
        total_bytes = 0

        for current_dir, dirnames, filenames in os.walk(str(resolved_root), followlinks=False):
            # Compute nesting depth relative to project root
            try:
                rel_dir = Path(current_dir).relative_to(resolved_root)
                depth = len(rel_dir.parts)
            except ValueError:
                continue

            if depth > self.max_depth:
                dirnames.clear()
                continue

            # Filter out excluded directory branches in-place
            dirnames[:] = [
                d
                for d in dirnames
                if d.lower() not in EXCLUDED_DIRECTORIES and not d.startswith(".")
            ]

            for filename in filenames:
                if len(scanned_files) >= self.max_files:
                    logger.info("Project scan reached max file limit (%d)", self.max_files)
                    return scanned_files

                file_path = Path(current_dir) / filename

                # Security check: Validate canonical path does not escape project root via junction
                try:
                    real_file = file_path.resolve()
                    if not real_file.is_relative_to(resolved_root):
                        logger.warning("Skipping symlink escape: %s", file_path)
                        continue
                except (ValueError, RuntimeError):
                    continue

                rel_path = str(file_path.relative_to(resolved_root)).replace("\\", "/")

                if not self.is_file_eligible(rel_path, filename):
                    continue

                # Check individual file size
                try:
                    file_size = file_path.stat().st_size
                except OSError:
                    continue

                if file_size > self.max_file_bytes or file_size == 0:
                    continue

                if total_bytes + file_size > self.max_total_bytes:
                    logger.info("Project scan reached total bytes limit (%d)", self.max_total_bytes)
                    return scanned_files

                # Read and validate text content
                content = self._safe_read_text(file_path)
                if content is None:
                    continue

                # Redact secrets before caching
                redacted = redact_sensitive_data(content)
                content_hash = hashlib.sha256(redacted.encode("utf-8", "replace")).hexdigest()
                detected_lang = detect_language(code=redacted, hint=file_path.suffix or filename)

                scanned_files.append(
                    ScannedFile(
                        relative_path=rel_path,
                        content=redacted,
                        language=detected_lang.name if detected_lang else "Plain Text",
                        content_hash=content_hash,
                        size_bytes=len(redacted.encode("utf-8", "replace")),
                    )
                )
                total_bytes += file_size

        return scanned_files

    @staticmethod
    def _safe_read_text(path: Path) -> str | None:
        """Safely read text with encoding fallback and null-byte binary check."""
        try:
            with open(path, "rb") as f:
                raw = f.read(1024)
                if b"\x00" in raw:
                    # Binary file detected
                    return None

            with open(path, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(path, encoding="utf-8-sig") as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(path, encoding="latin-1") as f:
                        return f.read()
                except Exception:
                    return None
        except Exception as exc:
            logger.debug("Failed to read file %s: %s", path, exc)
            return None
