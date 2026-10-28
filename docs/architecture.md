# GhostTrace Architecture Specification

> **Status:** Step 04 / 10 — Ghost Personality & Behaviour Engine  
> **Note:** Foundation, Configuration, Logging, Textual TUI, Typer CLI, Local AI Subsystem (Qwen2.5 GGUF + llama.cpp), and Ghost Personality & Behaviour Engine are implemented. Modules marked as *Planned* describe planned future architecture and are not yet implemented.

---

## 1. Architectural Overview

**GhostTrace** ("The AI That Haunts Your Terminal") is an offline-first, local AI terminal companion built for developers. It unifies three distinct roles:
1. **Developer Assistant:** Code generation, error triage, shell command synthesis, and interactive debugging.
2. **Digital Ghost:** Context-aware terminal presence with evolving persona traits, haunting atmospheric effects, and responsive dialogue.
3. **Terminal Guardian:** Pre-execution command interception and safety analysis to prevent destructive shell operations.

```text
┌─────────────────────────────────────────────────────────────────┐
│                    GhostTrace CLI (Typer)                       │
│           (ghosttrace, --version, --help, status)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ launches
┌───────────────────────────────▼─────────────────────────────────┐
│             Interactive Terminal Interface (Textual)            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ GhostTraceHeader (Branding, Live AI & Ghost States)       │  │
│  ├─────────────────────────────┬─────────────────────────────┤  │
│  │ ConversationLog (Streaming) │ StatusPanel (Telemetry)     │  │
│  ├─────────────────────────────┴─────────────────────────────┤  │
│  │ CommandInput (History Nav: Up/Down, Natural Language)     │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ Footer (Shortcuts: Enter, Ctrl+L, Ctrl+C, Escape)         │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ dispatches
┌───────────────────────────────▼─────────────────────────────────┐
│                    Command System & History                     │
│  ┌─────────────────────────────┐ ┌───────────────────────────┐  │
│  │ CommandRegistry (Routing)   │ │ SessionHistory (In-Memory)│  │
│  └─────────────────────────────┘ └───────────────────────────┘  │
└───────┬───────────────────────┬───────────────────────┬─────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  AI Engine   │◄───────┤ Ghost Persona│        │Safety Guard  │
│(Implemented) │        │(Implemented) │        │  (Planned)   │
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
- **Features:** Type-safe settings, environment variable overrides (`GHOSTTRACE_*`), Windows user path resolution (`%LOCALAPPDATA%\GhostTrace`), cached singleton retrieval.

### `ghosttrace.core` (Implemented in Step 01)
- **Status:** Implemented (Logging & Shared Foundation).
- **Responsibility:** Common runtime primitives, error types, and logging infrastructure.
- **Features:** Dual console and 10 MB rotating file logging, safe handler registration, strict privacy enforcement.

### `ghosttrace.terminal` (Implemented in Step 02)
- **Status:** Implemented (Interactive TUI & CLI Architecture).
- **Responsibility:** User interaction, presentation, command execution routing, and session history.
- **Components:**
  - `GhostTraceApp`: Textual application orchestrating the visual layout, background workers, and keyboard event lifecycle.
  - `GhostTraceHeader`: Displays branding, ghost entity badge, and live AI engine status.
  - `ConversationLog`: Scrollable log managing user command exchanges, incremental AI streaming, and formatted outputs.
  - `StatusPanel`: Live telemetry panel reflecting environment, version, command counts, and persona mood.
  - `CommandInput`: Specialized input widget supporting Up/Down arrow session history cycling.
  - `CommandRegistry`: Decoupled registry routing input to registered command handlers with alias resolution.
  - `SessionHistory`: Lightweight in-memory FIFO history excluding blank inputs and self-referential commands.
  - `interface`: High-level entry points for interactive TUI launch and non-interactive Rich CLI reporting.

### `ghosttrace.ai` (Implemented in Step 03)
- **Status:** Implemented (Local CPU Inference via llama.cpp + Qwen2.5 GGUF).
- **Responsibility:** Local open-weight LLM inference orchestration, lazy model loading, context management, and non-blocking streaming execution.
- **Components:**
  - `AIEngine`: Unified facade coordinating model lifecycle, prompt assembly, and inference execution.
  - `ModelManager`: Hardware-aware model discovery, validation, thread-safe lazy loading, and RAM release.
  - `InferenceEngine`: Low-level wrapper executing chat completions via `llama-cpp-python` with token streaming and concurrency locks.
  - `ConversationManager`: In-memory conversation context enforcing bounded limits and in-place system prompt updates.
  - `prompts`: Base developer assistant system prompt ensuring factual, humble, and developer-centric guidance.
  - `schemas`: Typed Pydantic models for status, model metadata, execution config, and token statistics.
  - `exceptions`: Domain-specific AI exception hierarchy.

### `ghosttrace.ghost` (Implemented in Step 04)
- **Status:** Implemented (Ghost Personality & Behaviour Engine).
- **Responsibility:** Persona state machine, contextual dialogue, configurable profiles, trait models, session mood transitions, and prompt composition.
- **Components:**
  - `GhostEngine`: Central facade managing active profile selection, mood transitions, prompt composition, and runtime switching.
  - `PersonalityProfile`: Declarative profile specifications for three distinct personas:
    1. **Forgotten Machine:** Dormant ancient intelligence, observant, calm, nostalgic, reflective.
    2. **Phantom Coder:** Playful digital hacker spirit, curious, witty, energetic, debug-focused.
    3. **Guardian Spirit:** Vigilant protector, composed, reassuring, defensive programming advocate.
  - `PersonalityTraits`: Normalized trait model (0.0 to 1.0) governing curiosity, composure, humor, mystery, technical helpfulness, emotional expressiveness, and safety awareness.
  - `SessionMoodTracker`: Lightweight, explainable session mood state machine with deterministic transitions (`DORMANT`, `CURIOUS`, `FOCUSED`, `AMUSED`, `CONCERNED`, `SATISFIED`).
  - `behaviour`: Context-aware classification engine detecting greetings, technical questions, debugging, errors, and dangerous commands.
  - `response_modifier`: Multi-layered system prompt composition pipeline injecting base identity, ghost persona, traits, and context guidance while strictly preserving truthfulness and developer safety.
  - `schemas`: Typed schemas and enums (`GhostProfileId`, `GhostMood`, `InteractionContext`, `PersonalityStatus`).

### `ghosttrace.safety` (Planned — Step 06)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Terminal guardian analyzing shell commands before execution with multi-tier risk classification (`SAFE`, `WARNING`, `DANGEROUS`, `BLOCKED`).

### `ghosttrace.memory` (Planned — Step 07)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Persistent local state, session history, and persona memory backed by SQLite in WAL mode.

### `ghosttrace.system` (Planned — Step 08)
- **Status:** Package initialized; implementation planned.
- **Responsibility:** Non-invasive local OS telemetry and hardware capability monitoring (CPU load, RAM pressure).

---

## 3. Agreed 10-Step Development Roadmap

1. **Step 01: Foundation, Environment & Configuration** *(Completed)*
2. **Step 02: Interactive Terminal Interface & CLI** *(Completed)*
3. **Step 03: Local AI Integration** *(Completed)*
4. **Step 04: Ghost Personality & Behaviour Engine** *(Completed)*
5. **Step 05: Developer Intelligence & Coding Assistance**
6. **Step 06: Command Guardian & Execution Safety**
7. **Step 07: Persistent Memory & Project Context**
8. **Step 08: System Awareness & Diagnostics**
9. **Step 09: Haunted Experience & Interactive Events**
10. **Step 10: Testing, Optimization, Packaging & Release**

---

## 4. Terminal Visual Design & Aesthetics

- **Palette:** Green phosphor CRT monitor aesthetic.
  - Primary Background: `#080c0a` (deep charcoal black)
  - Surface Background: `#050807` (dark container background)
  - Primary Accent: `#00ff66` / `#33ff33` (phosphor green)
  - Secondary Text: `#779977` / `#99bb99` (muted green-gray)
  - Warning/Alerts: `#ff5555` (muted crimson red)
  - Borders: `#00441b` / `#005522` (subtle dark green borders)
- **Zero Overhead:** No continuous animations, heavy background threads, or GPU dependencies; perfectly suited for Intel UHD Graphics and 12 GB RAM.
