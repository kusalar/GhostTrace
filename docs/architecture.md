# GhostTrace Architecture Specification

> **Status:** Step 01 / 10 — Foundation & Configuration  
> **Note:** Only the foundation, configuration, logging, and package structure are currently implemented. Modules marked as *Planned* describe planned future architecture and are not yet implemented in Step 01.

---

## 1. Architectural Overview

**GhostTrace** ("The AI That Haunts Your Terminal") is an offline-first, local AI terminal companion built for developers. It unifies three distinct roles:
1. **Developer Assistant:** Code generation, error triage, shell command synthesis, and interactive debugging.
2. **Digital Ghost:** Context-aware terminal presence with evolving persona traits, haunting atmospheric effects, and responsive dialogue.
3. **Terminal Guardian:** Pre-execution command interception and safety analysis to prevent destructive shell operations.

```text
┌─────────────────────────────────────────────────────────────────┐
│                       GhostTrace Terminal                       │
│             (Planned: Rich Console + Textual TUI)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  AI Engine   │        │ Ghost Persona│        │Safety Guard  │
│  (Planned)   │        │  (Planned)   │        │  (Planned)   │
└───────┬──────┘        └───────┬──────┘        └───────┬──────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│Memory System │        │System Monitor│        │  Core Config │
│  (Planned)   │        │  (Planned)   │        │ (Implemented)│
└──────────────┘        └──────────────┘        └──────────────┘
```

---

## 2. Package Breakdown & Responsibilities

### `ghosttrace.config` (Implemented in Step 01)
- **Status:** Implemented.
- **Responsibility:** Centralized configuration management using Pydantic Settings (`BaseSettings`).
- **Features:**
  - Type-safe validation of environment, debug mode, log levels, and directory paths.
  - Environment variable overrides with the `GHOSTTRACE_` prefix.
  - Cross-platform Windows path resolution (`pathlib.Path`).
  - Safe default data directories outside repository roots (`%LOCALAPPDATA%\GhostTrace`).
  - Cached singleton retrieval (`get_settings()`) with unit-test isolation capabilities.

### `ghosttrace.core` (Implemented in Step 01)
- **Status:** Implemented (Logging & Foundation).
- **Responsibility:** Common runtime primitives, error types, and logging infrastructure.
- **Features:**
  - Rotating file logging (10 MB per file, 5 backups) and console stream output.
  - Automatic directory provisioning.
  - Safe initialization preventing duplicate handlers.
  - Strict privacy enforcement: forbids logging secrets, passwords, or raw proprietary code.

### `ghosttrace.ai` (Planned — Steps 03, 04)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Local open-weight LLM inference orchestration.
- **Planned Design:**
  - Runtime: `llama-cpp-python` binding to `llama.cpp` using Qwen2.5 Instruct GGUF.
  - Quantization: 4-bit / 5-bit (Q4_K_M) optimized for CPU execution on 12 GB RAM (Intel i3-1115G4).
  - Context budgeting: Strict sliding window tokens with KV cache quantization to respect hardware limits.
  - Zero external network dependencies.

### `ghosttrace.ghost` (Planned — Step 06)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Persona state machine, contextual dialogue, and atmospheric terminal haunting.
- **Planned Design:**
  - Dynamic mood and haunting intensity based on developer activity, compilation failures, and time of day.
  - Atmospheric ASCII art, glitch text, and subtle terminal easter eggs.

### `ghosttrace.terminal` (Planned — Step 05)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Terminal UI rendering, REPL loop, and syntax-highlighted command output.
- **Planned Design:**
  - Built with `Rich` and `Textual`.
  - Non-blocking asynchronous event loop allowing background AI token streaming while maintaining a responsive CLI.

### `ghosttrace.safety` (Planned — Step 07)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Terminal guardian analyzing commands before execution.
- **Planned Design:**
  - Multi-tier danger classification: `SAFE`, `WARNING`, `DANGEROUS`, `BLOCKED`.
  - Heuristic AST and regex matching for destructive operations (e.g., recursive deletion, disk formatting, sensitive environment dumping).
  - Optional local AI safety verification for ambiguous shell commands.

### `ghosttrace.memory` (Planned — Step 08)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Persistent local state, session history, and persona memory.
- **Planned Design:**
  - SQLite backend residing in `%LOCALAPPDATA%\GhostTrace\db\ghosttrace.db`.
  - WAL mode (Write-Ahead Logging) for atomic, crash-resilient operations.
  - Clean retention policies allowing the user to prune or wipe history at any time.

### `ghosttrace.system` (Planned — Step 09)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Local OS telemetry and hardware capability inspection.
- **Planned Design:**
  - Non-invasive resource monitoring (CPU load, RAM pressure).
  - Dynamically throttles AI inference when system memory is constrained.

---

## 3. Data Privacy & Security Principles

1. **Strict Offline Execution:** GhostTrace operates strictly locally. No prompt, shell command, code snippet, or diagnostic ever leaves the host machine.
2. **No Secret Logging:** Tokens, keys, passwords, and sensitive environment variables are filtered from all application log files.
3. **User-Owned Data:** All configuration and persistent databases reside within standard user application data paths (`%LOCALAPPDATA%\GhostTrace`), fully inspectable and deletable by the user.
4. **Non-Destructive Defaults:** By default, command suggestions require explicit user confirmation before shell execution.

---

## 4. Hardware Optimization Strategy (Intel i3-1115G4 / 12 GB RAM)

- **Target Architecture:** Dual-core / 4-thread CPU with AVX2 instruction support.
- **Inference Budget:** Thread count capped at 3 or 4 threads to prevent UI lockup.
- **Memory Footprint:** Peak process memory ceiling bounded at ≤ 4.5 GB for LLM weights and context buffer, preserving the remaining RAM for the operating system and developer tools.
