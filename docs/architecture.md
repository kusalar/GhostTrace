# GhostTrace Architecture Specification

> **Status:** Step 10 / 10 — Testing, Optimization, Packaging & Release (Complete / Production Ready)  
> **Note:** All 10 roadmap steps are fully implemented, verified, hardened, and packaged for Windows 10/11 x64. Foundation, Configuration, Logging, Textual TUI, Typer CLI, Local AI Subsystem (Qwen2.5 GGUF + llama.cpp), Ghost Personality & Behaviour Engine, Developer Intelligence & Safe Code Analysis, Command Guardian & Execution Safety, Persistent Memory & Project Context, System Awareness & Diagnostics, Haunted Experience & Interactive Events, and PyInstaller Release Packaging are verified with 458 automated tests (100% passing, 89.08% project coverage).

---

## 1. Architectural Overview

**GhostTrace** ("The AI That Haunts Your Terminal") is an offline-first, local AI terminal companion built for developers. It unifies three distinct roles:
1. **Developer Assistant:** Code explanation, debugging, review, generation, refactoring, test generation, and safe local static analysis.
2. **Digital Ghost:** Context-aware terminal presence with evolving persona traits, haunting atmospheric effects, and responsive dialogue.
3. **Terminal Guardian:** Pre-execution command interception and safety analysis to prevent destructive shell operations.

```text
┌─────────────────────────────────────────────────────────────────┐
│                    GhostTrace CLI (Typer)                       │
│        (ghosttrace, --version, --help, status, guard)           │
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
│(Implemented) │        │(Implemented) │        │(Implemented) │
└───────┬──────┘        └───────┬──────┘        └───────┬──────┘
        │                       │                       │
        │       ┌───────────────┴──────────────┐        │
        │       │    Developer Intelligence    │        │
        └──────►│        (Implemented)         │        │
                └───────────────┬──────────────┘        │
                                │                       │
        ┌───────────────────────┼───────────────────────┘
        ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│Memory System │        │System Monitor│        │  Core Config │
│(Implemented) │        │(Implemented) │        │ (Implemented)│
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

### `ghosttrace.developer` (Implemented in Step 05)
- **Status:** Implemented (Developer Intelligence & Safe Code Analysis).
- **Responsibility:** High-level programming assistant capabilities, intent classification, bounded code context construction, safe AST static analysis, polyglot language detection, and task-specific prompt composition.
- **Components:**
  - `DeveloperEngine`: High-level facade coordinating intent detection, context assembly, static analysis, and prompt generation.
  - `intents`: Rule-based developer intent classifier supporting 9 discrete intents (`EXPLAIN_CODE`, `DEBUG_CODE`, `REVIEW_CODE`, `GENERATE_CODE`, `REFACTOR_CODE`, `GENERATE_TESTS`, `OPTIMIZE_CODE`, `GENERAL_PROGRAMMING`, `UNKNOWN`) with CLI keyword exclusion.
  - `languages`: Polyglot language registry and detector supporting 15+ languages (Python, JS, TS, Java, C, C++, C#, Go, Rust, PHP, HTML, CSS, SQL, Bash, PowerShell) via fences, file extensions, and syntax regex.
  - `code_analysis`: Safe static analyzer using Python's standard library `ast.parse` for syntax trees, function/class discovery, import mapping, bare except identification, and polyglot delimiter validation. Strictly zero code execution.
  - `context`: Context builder extracting markdown code blocks, compiler tracebacks, and applying safety truncation limits (`GHOSTTRACE_DEV_MAX_CODE_CHARS`, `GHOSTTRACE_DEV_MAX_CONTEXT_CHARS`).
  - `prompts`: Task-specific prompt builders injecting structured instructions (findings severity, testing checklists, edge cases) and static analysis ground truth into the AI prompt pipeline.
  - `responses`: Presentation formatters rendering formatted terminal banners, static analysis reports, and task-oriented summaries.
  - `schemas`: Typed Pydantic models and Enums (`DeveloperIntent`, `ReviewSeverity`, `ReviewFinding`, `CodeAnalysisResult`, `DeveloperContext`, `DeveloperTaskRequest`, `DeveloperTaskResult`).

### `ghosttrace.guardian` / `ghosttrace.safety` (Implemented in Step 06)
- **Status:** Implemented (Command Guardian & Execution Safety).
- **Responsibility:** Pre-execution static command analysis, risk classification, approval integrity lifecycle, and restricted subprocess execution.
- **Components:**
  - `GuardianEngine`: Subsystem facade coordinating static analysis, explanation generation, cryptographic approval tokens, and controlled execution.
  - `CommandAnalyzer`: Windows-aware argument parsing preserving backslash path delimiters, resolving executable paths via `shutil.which`, and detecting unquoted shell operators (`&&`, `||`, `;`, `|`, `>`, `<`).
  - `RiskClassifier`: Multi-dimensional classification evaluating command combinations, arguments, rules, and default medium risk for unknown binaries.
  - `PatternRules`: Conservative regex heuristics detecting destructive filesystem operations, system modification, registry tampering, suspicious obfuscated PowerShell, remote payload downloads, destructive VCS actions, and package manager risks.
  - `ExecutionPolicy`: Enforces execution boundaries; strict `shell=False` only; no subshell wrappers (`cmd.exe /c`, `powershell.exe`); HIGH and BLOCKED commands never executed.
  - `ApprovalManager`: HMAC-SHA256 cryptographically signed tokens tying approval to the exact command text, parsed arguments, working directory, and risk classification. Single-use and short-lived (default 60s TTL).
  - `ControlledExecutor`: Process execution using `subprocess.Popen` with argument lists, timeout enforcement with hard kill (`proc.kill()`), bounded stdout/stderr capture (default 4,000 chars), and safe Windows console encoding fallback.
  - `GuardianHistory`: In-memory bounded FIFO session history with credential redaction.
  - `CommandApprovalModal`: Textual modal screen providing explicit visual confirmation previews before running permitted commands.
  - `schemas`: Typed Pydantic models (`RiskLevel`: `SAFE`, `LOW`, `MEDIUM`, `HIGH`, `BLOCKED`; `ApprovalStatus`, `ExecutionStatus`, `CommandAnalysis`, `ApprovalRequest`, `ExecutionResult`, `HistoryEntry`, `GuardianStatus`).

### `ghosttrace.memory` (Implemented in Step 07)
- **Status:** Implemented (Persistent Memory & Project Context).
- **Responsibility:** Persistent local conversation history, user-controlled memory creation, and read-only project indexing backed by Python's standard-library `sqlite3`. Strictly zero vector DBs, embeddings models, or cloud sync.
- **Components:**
  - `DatabaseManager`: Standard library `sqlite3` connection manager with WAL journal mode, strict foreign key enforcement (`PRAGMA foreign_keys = ON`), 5000ms busy timeout, automatic FTS5 detection, and transaction safety.
  - `Migrations`: Versioned database migration runner (`schema_metadata`) managing schema lifecycle, relational tables (`conversations`, `messages`, `memories`, `projects`, `project_files`, `app_state`), and conditional FTS5 virtual tables (`memories_fts`, `project_files_fts`) with automatic synchronization triggers.
  - `Redaction`: Sensitive secret detection and sanitization engine covering API tokens, bearer keys, private key blocks, connection strings, and credential patterns before persistent storage.
  - `MemoryRepository`: CRUD operations for structured memories across 7 categories (`USER_PREFERENCE`, `USER_PROFILE`, `PROJECT_CONTEXT`, `TECHNICAL_DECISION`, `WORKFLOW`, `LEARNING`, `GENERAL`) with configurable bounding, recency sorting, and export/import capabilities.
  - `ConversationPersistenceManager`: Bounded conversation session management persisting user and assistant messages, maintaining session context and ordering.
  - `MemoryRetriever`: Relevance-based search using FTS5 full-text queries with graceful fallback to parameterized SQL `LIKE`, weighted by importance and recency with deduplication.
  - `ProjectRegistry`: Safe project registration validating paths against dangerous root directories (`C:\`, `C:\Windows`, Program Files, User home root, GhostTrace app data) and maintaining active project pointers.
  - `ProjectScanner`: Read-only, bounded directory crawler enforcing directory exclusions (`.git`, `.venv`, `node_modules`, `__pycache__`, build artifacts, binaries, model weights), depth limits, file count caps, per-file byte thresholds (default 256 KB), total byte quotas (default 5 MB), symlink escape rejection, and UTF-8 fallback decoding.
  - `ProjectIndexer`: Incremental file indexing via SHA-256 content hashing, language detection, stale file removal, and full-text code search with snippet extraction.
  - `ContextBuilder`: Prompt injection-defended context formatter framing retrieved memories and project files as untrusted, passive reference material with strict boundary delimiters.
  - `MemoryEngine`: Subsystem facade coordinating the database, repository, retrieval, registry, scanner, indexer, and context builder.
  - `schemas`: Typed Pydantic models and Enums (`MemoryCategory`, `MemorySource`, `MemoryItem`, `ConversationRecord`, `MessageRecord`, `ProjectRecord`, `ProjectFileRecord`, `MemorySearchResult`, `ProjectFileSearchResult`, `InjectedContext`, `MemoryStatus`, `ProjectIndexResult`).

### `ghosttrace.system` (Implemented in Step 08)
- **Status:** Implemented (System Awareness & Diagnostics).
- **Responsibility:** Non-invasive, read-only host OS telemetry, hardware resource monitoring, operational health checks, diagnostic reports, and passive AI context injection. Strictly zero external telemetry, zero background polling threads, and zero heavy dependencies (standard library and Win32 `ctypes` only).
- **Components:**
  - `SystemCollector`: Central metric orchestrator maintaining TTL-cached system snapshots to prevent CPU/IO spikes.
  - `CpuCollector`: CPU model discovery via `winreg` (`HARDWARE\DESCRIPTION\System\CentralProcessor\0`), logical core counts, and delta sampling via Win32 `GetSystemTimes` without shell invocation.
  - `MemoryCollector`: Physical RAM telemetry via Win32 `GlobalMemoryStatusEx`, tracking total, available, used bytes and percent load while cleanly isolating page-file swap.
  - `DiskCollector`: Storage capacity and free space measurement for application data and repository drives via standard library `shutil.disk_usage`.
  - `ProcessCollector`: Lightweight process awareness via Win32 `EnumProcesses` for system task counts, alongside self-process resident RAM (`WorkingSetSize`) and PID tracking via Win32 `GetProcessMemoryInfo`.
  - `UptimeCollector`: Windows system uptime via `GetTickCount64()` and application session duration tracking.
  - `HealthRegistry`: Read-only health inspection across all 11 GhostTrace subsystems (`configuration`, `logging`, `platform`, `ai_engine`, `ghost_persona`, `developer_assistant`, `command_guardian`, `memory_database`, `project_context`, `system_monitor`, `storage`) without executing commands or mutating state.
  - `DiagnosticsGenerator`: Comprehensive diagnostic report generator with threshold-based operational warnings and safe JSON export.
  - `SystemEngine`: Subsystem facade coordinating collector, health registry, diagnostics, and relevance-filtered AI system context injection (`SYSTEM_INTENT_PATTERN`).
  - `schemas`: Typed Pydantic models and Enums (`HealthStatus`, `PlatformInfo`, `CpuInfo`, `MemoryInfo`, `DiskDrive`, `DiskInfo`, `ProcessInfo`, `UptimeInfo`, `SubsystemHealth`, `SystemHealthReport`, `SystemSnapshot`, `DiagnosticReport`).

### `ghosttrace.haunt` (Implemented in Step 09)
- **Status:** Implemented (Haunted Experience & Interactive Events).
- **Responsibility:** Atmospheric terminal manifestations, context-aware ghost reactions, supernatural-themed events, dynamic mode filtering, frequency budgeting, and strictly non-persistent in-memory event tracking. Standard library, Rich, and Textual only; strictly zero speech synthesis, audio, external telemetry, or SQLite persistence.
- **Components:**
  - `HauntEngine`: Central subsystem facade orchestrating event generation, live trigger evaluation, profile reaction generation, mode transitions, and status reporting.
  - `EventCatalog`: Declarative catalog spanning 9 supernatural event categories (`GHOST_GREETING`, `IDLE_WHISPER`, `CODING_REACTION`, `ERROR_REACTION`, `GUARDIAN_REACTION`, `MOOD_SHIFT`, `SESSION_EVENT`, `DISCOVERY_EVENT`, `SPECIAL_EVENT`) with profile-coherent message templates (`forgotten-machine`, `phantom-coder`, `guardian-spirit`, `default`) and deterministic seeding.
  - `HauntScheduler`: Event frequency manager enforcing global and per-event cooldowns, intensity multipliers (`LOW` 1.5x, `MEDIUM` 1.0x, `HIGH` 0.6x), session event quotas (`GHOSTTRACE_HAUNT_MAX_EVENTS_PER_SESSION`), recent duplicate suppression, and idle eligibility without background threads.
  - `TriggerEvaluator`: Trigger-to-event dispatch mapping 8 application triggers (`SESSION_START`, `IDLE_TICK`, `CODING_SUCCESS`, `APP_ERROR`, `GUARDIAN_WARNING`, `MOOD_TRANSITION`, `COMMAND_DISCOVERY`, `MANUAL_PREVIEW`) to eligible event categories with strict mode filtering (`NORMAL` and `FOCUS` suppress all unsolicited events).
  - `GhostReactionBuilder`: Contextual reactive text generator tying atmospheric manifestations directly to genuine operational milestones: coding solutions, application/runtime errors, Guardian risk warnings, and persona mood shifts.
  - `HauntRenderer`: Visual presentation engine rendering ASCII ghost glyphs (`ascii_ghost`, `ascii_spirit`, `ascii_glyph`, `ascii_whisper`), stylized Rich panels, reduced-motion accessibility formatting, and formatted session history tables.
  - `HauntHistoryManager`: Bounded in-memory FIFO queue (max 100 entries) tracking triggered events for session inspection with zero SQLite writes.
  - `schemas`: Typed Pydantic models and Enums (`HauntMode`: `NORMAL`, `AMBIENT`, `HAUNTED`, `FOCUS`; `HauntIntensity`: `LOW`, `MEDIUM`, `HIGH`; `EventCategory`, `TriggerType`, `HauntEvent`, `TriggerContext`, `TriggerResult`, `HauntHistoryEntry`, `HauntStatus`).

### Windows Packaging & Release Distribution (Implemented in Step 10)
- **Status:** Implemented (Hardened Windows Distribution).
- **Responsibility:** Standalone executable build, dependency bundling, startup latency optimization, and production release artifact staging.
- **Components:**
  - `PyInstaller` Spec (`GhostTrace.spec`): Collects `textual`, `llama_cpp` native AVX2 runtime binaries, metadata, and dependencies into an optimized onedir distribution.
  - `GhostTrace.exe`: Standalone Windows executable runner (10.8 MB) verified for headless CLI subcommands (`status`, `guard`, `system`, `haunt`, `--version`, `--help`) and interactive TUI.
  - `dist/release/`: Self-contained release staging directory with binary bundle, `SHA256SUMS.txt`, `QUICKSTART.md`, `INSTALL.md`, `MODEL_SETUP.md`, `CONFIG.md`, `THIRD_PARTY_NOTICES.md`, and `RELEASE_NOTES_v1.0.0.md`.

---

## 3. Agreed 10-Step Development Roadmap

1. **Step 01: Foundation, Environment & Configuration** *(Completed)*
2. **Step 02: Interactive Terminal Interface & CLI** *(Completed)*
3. **Step 03: Local AI Integration** *(Completed)*
4. **Step 04: Ghost Personality & Behaviour Engine** *(Completed)*
5. **Step 05: Developer Intelligence & Coding Assistance** *(Completed)*
6. **Step 06: Command Guardian & Execution Safety** *(Completed)*
7. **Step 07: Persistent Memory & Project Context** *(Completed)*
8. **Step 08: System Awareness & Diagnostics** *(Completed)*
9. **Step 09: Haunted Experience & Interactive Events** *(Completed)*
10. **Step 10: Testing, Optimization, Packaging & Release** *(Completed)*

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
