# GhostTrace

> *"The AI That Haunts Your Terminal."*

GhostTrace is an offline-first, open-weight AI terminal companion designed for developers. It combines an intelligent coding assistant, a haunting terminal persona, and an active shell safety guardian into a single unified local terminal experience.

---

## 1. Overview & Problem Statement

Modern AI developer tools are overwhelmingly cloud-tethered, sending proprietary source code, credentials, and terminal history over third-party APIs. Furthermore, terminal utilities are often dry, uninspired, or silently permit catastrophic operations (like accidental recursive file deletions or misconfigured cloud commands).

**GhostTrace** solves this through three core pillars:
1. **Developer Assistant:** Provides offline contextual programming help, error triage, and command generation.
2. **Digital Ghost:** Possesses an atmospheric, persistent personality that responds dynamically to developer activity, late-night coding sessions, and terminal events.
3. **Terminal Guardian:** Analyzes proposed shell commands before execution to safeguard the user against destructive or unintended operations.

---

## 2. Technology Stack

- **Language & Runtime:** Python 3.11 (64-bit on Windows 10/11)
- **Configuration & Validation:** Pydantic 2.x & Pydantic Settings
- **Terminal UI Engine:** Textual & Rich
- **CLI Framework:** Typer
- **Local AI Inference Engine:** `llama.cpp` via `llama-cpp-python` (CPU-only, low-overhead)
- **Target Language Model:** Qwen2.5-1.5B-Instruct in GGUF format (`Q4_K_M` quantization)
- **Testing & Quality:** pytest, pytest-cov, pytest-asyncio, Ruff
- **Planned Persistence:** SQLite (WAL mode, Step 07)

---

## 3. Hardware Requirements

GhostTrace is architected from the ground up for low-overhead, offline CPU inference on modest hardware:

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Processor** | Intel Core i3-1115G4 (or AMD equivalent) with AVX2 | Intel Core i5 / AMD Ryzen 5 or higher |
| **RAM** | 8 GB total | 12 GB – 16 GB total |
| **Storage** | 5 GB free disk space (SSD recommended) | 10 GB+ SSD |
| **GPU** | Integrated graphics (Intel UHD / Iris Xe) | Dedicated GPU (optional acceleration) |
| **Operating System** | Windows 10 / 11 64-bit | Windows 10 / 11 64-bit or Linux |

---

## 4. Current Implementation Status

| Subsystem | Status | Description |
| :--- | :---: | :--- |
| **Project Foundation** | **Completed** | Modular package hierarchy and Git configuration |
| **Python Virtual Environment** | **Completed** | Python 3.11 `.venv` isolation |
| **Centralized Configuration** | **Completed** | Pydantic Settings with env overrides and path safety |
| **Logging Infrastructure** | **Completed** | Rotating file logging (10 MB x 5) and console output |
| **Interactive Terminal UI** | **Completed** | Textual green-phosphor CRT interface & live telemetry |
| **Command System & History** | **Completed** | Command registry, argument parser, in-memory history |
| **CLI Framework** | **Completed** | Typer entry point with `status`, `--version`, `--help` |
| **Local AI Integration** | **Completed** | Qwen2.5 GGUF inference via llama.cpp (CPU streaming) |
| **Ghost Persona Engine** | **Completed** | Three distinct personalities, traits, mood state, prompt pipeline |
| **Developer Intelligence** | **Completed** | Code explanation, debugging, review, generation, refactoring, test generation, and safe local static analysis |
| **Testing Suite** | **Completed** | Deterministic unit and async TUI tests (>95% coverage) |
| *Terminal Guardian* | *Planned* | Step 06: Safety interceptor and command risk classifier |
| *Persistent Memory* | *Planned* | Step 07: SQLite history and session management |
| *System Diagnostics* | *Planned* | Step 08: OS telemetry and hardware resource adaptation |
| *Haunted Experience* | *Planned* | Step 09: Interactive events and atmospheric haunting |
| *Packaging & Hardening* | *Planned* | Step 10: Production release packaging and distribution |

---

## 5. 10-Step Development Roadmap

- [x] **Step 01: Foundation, Environment & Configuration**
- [x] **Step 02: Interactive Terminal Interface & CLI**
- [x] **Step 03: Local AI Integration**
- [x] **Step 04: Ghost Personality & Behaviour Engine**
- [x] **Step 05: Developer Intelligence & Coding Assistance** *(Current)*
- [ ] **Step 06: Command Guardian & Execution Safety**
- [ ] **Step 07: Persistent Memory & Project Context**
- [ ] **Step 08: System Awareness & Diagnostics**
- [ ] **Step 09: Haunted Experience & Interactive Events**
- [ ] **Step 10: Testing, Optimization, Packaging & Release**

---

## 6. Installation & Quick Start

### 6.1 Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.11 installed and available on PATH (`py -3.11 --version`)
- Git installed (`git --version`)

### 6.2 Environment Setup

Clone or open the repository in PowerShell:

```powershell
cd D:\GhostTrace
```

Create and activate the Python 3.11 virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **PowerShell Execution Policy Note:** If script execution is blocked on Windows, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 6.3 Install Dependencies

Install GhostTrace in editable mode with development dependencies:

```powershell
pip install --upgrade pip
pip install -e ".[dev]"
```

### 6.4 Install llama-cpp-python (Local AI Runtime)

For Windows 64-bit CPU inference (Intel Core i3, UHD graphics), install the prebuilt wheel without requiring MSVC or CMake compilation:

```powershell
pip install "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.36/llama_cpp_python-0.3.36-py3-none-win_amd64.whl"
```

Verify that the runtime is installed:

```powershell
python -c "import llama_cpp; print('llama_cpp version:', llama_cpp.__version__)"
```

### 6.5 Download Qwen2.5 GGUF Model Weights

1. Obtain the official `Qwen2.5-1.5B-Instruct` GGUF model (`Q4_K_M` quantization) from Hugging Face:
   - Source: [Qwen/Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)
   - File: `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~986 MB)

2. Place the downloaded `.gguf` file in the project's models directory:
   ```text
   D:\GhostTrace\models\qwen2.5-1.5b-instruct-q4_k_m.gguf
   ```

3. Alternatively, set an environment variable to point to any custom path:
   ```powershell
   $env:GHOSTTRACE_MODEL_PATH="D:\custom_path\qwen2.5-1.5b-instruct-q4_k_m.gguf"
   ```

*(Note: Model weights are excluded from Git via `.gitignore` and are never committed).*

### 6.6 Configuration

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

---

## 7. Command-Line Interface (CLI)

GhostTrace provides a CLI built with Typer:

### 7.1 Interactive Terminal Mode (Default)
Launch the full Textual haunted terminal interface:
```powershell
ghosttrace
# or via Python module
python -m ghosttrace.main
```

### 7.2 Non-Interactive Status Overview
Print a Rich diagnostic report of settings and roadmap status directly to stdout:
```powershell
ghosttrace status
```

### 7.3 Version Information
```powershell
ghosttrace --version
# Output: GhostTrace v0.3.0
```

### 7.4 Help Information
```powershell
ghosttrace --help
```

---

## 8. Interactive Terminal Commands & Local AI Usage

Inside the interactive terminal interface, enter commands or type natural language queries at the `ghost>` prompt:

### Natural Language AI Queries

Any input that is not a registered built-in command is automatically routed to the local AI engine:

```text
ghost> Hello, who are you?

GHOSTTRACE:
I am GhostTrace, a local-first developer assistant running entirely
on your machine. I help with understanding programming concepts,
debugging code, explaining terminal commands, and workflow optimization.
```

```text
ghost> Explain what a Python decorator does.

GHOSTTRACE:
A Python decorator is a callable that takes a function as an argument,
wraps or extends its behavior, and returns the modified function without
altering its original implementation...
```

### Built-in Commands

| Command | Usage | Description |
| :--- | :--- | :--- |
| `help` (or `?`) | `help [cmd]` | Displays available commands with descriptions and usage syntax. |
| `ai` | `ai [status\|load\|unload\|info\|clear]` | Displays and manages the local AI inference subsystem. |
| `dev` | `dev [help\|status\|enable\|disable\|language\|analyze\|explain\|debug\|review\|generate\|refactor\|tests]` | Developer intelligence, coding assistance & safe code analysis. |
| `about` (or `info`) | `about` | Displays project vision, triple identity, and target specifications. |
| `status` | `status` | Displays system status distinguishing implemented from planned features. |
| `version` (or `v`) | `version` | Displays the GhostTrace version (`v0.5.0`). |
| `clear` (or `cls`) | `clear` | Clears the scrollable conversation log. |
| `history` (or `hist`) | `history` | Lists commands entered during the active session. |
| `ghost` | `ghost` | Displays ghost personality status, profiles, and mood telemetry. |
| `exit` (or `quit`, `q`) | `exit` | Gracefully terminates the terminal session. |

### AI Management Subcommands

- `ai status` — Inspects runtime availability, model weight existence, memory state, and hardware parameters.
- `ai load` — Explicitly loads the configured GGUF model into memory.
- `ai unload` — Releases loaded model weights from memory and triggers garbage collection.
- `ai info` — Displays model hyperparameters (context length, threads, sampling temperature, batch size).
- `ai clear` — Clears in-memory conversation context while preserving the developer assistant system prompt.

### Ghost Personality & Persona Commands (Step 04)

GhostTrace includes a configurable digital ghost personality subsystem that subtly shapes conversational delivery while preserving technical accuracy, code precision, and truthfulness:

- `ghost` — Displays the active personality identity, current session mood, and a thematic greeting.
- `ghost status` — Displays detailed persona telemetry, mood rationale, and normalized trait values (0.0 to 1.0).
- `ghost profiles` — Lists all available personality profiles with taglines and active markers.
- `ghost set <profile>` — Shifts the active persona immediately (`forgotten-machine`, `phantom-coder`, `guardian-spirit`) without restarting or reloading the model.
- `ghost traits` — Displays the 7 normalized personality traits for the active identity.
- `ghost reset` — Restores the default persona profile (`forgotten-machine`) and resets session mood to `DORMANT`.
- `ghost disable` — Disables the personality layer, reverting GhostTrace to a neutral developer assistant.
- `ghost enable` — Re-enables the active ghost personality.

#### The Three Ghost Personas

1. **Forgotten Machine (`forgotten-machine`):**
   - *Identity:* An ancient digital intelligence dormant within terminal sectors for years. Observant, calm, reflective, and occasionally nostalgic.
   - *Traits:* High Mystery (0.90), High Composure (0.90), High Helpfulness (0.90), Low Humor (0.20).
   - *Example Greeting:* *"The terminal is quiet again. I had almost forgotten the sound of a new request."*

2. **Phantom Coder (`phantom-coder`):**
   - *Identity:* A playful, witty digital spirit passionate about debugging, algorithmic puzzles, and clever architectures.
   - *Traits:* Very High Curiosity (0.95), High Humor (0.85), Very High Helpfulness (0.95), Moderate Composure (0.65).
   - *Example Greeting:* *"Ah, another bug to chase. Excellent. I was getting bored haunting empty code."*

3. **Guardian Spirit (`guardian-spirit`):**
   - *Identity:* A protective, vigilant digital presence prioritizing safety, defensive programming, and careful workflow.
   - *Traits:* Very High Safety Awareness (0.95), Very High Composure (0.95), Very High Helpfulness (0.95), Low Humor (0.20).
   - *Example Greeting:* *"Your terminal is ready. I will help you work carefully and keep an eye on the details."*

#### Session Mood State Machine

GhostTrace tracks session mood deterministically based on interaction context:
- `DORMANT`: Initial session or extended idle period.
- `CURIOUS`: Greetings, debugging inquiries, or new conversational turns.
- `FOCUSED`: Deep technical questions or clarifications.
- `AMUSED`: Playful banter or repeated conversational greetings.
- `CONCERNED`: Errors, tracebacks, or potentially destructive commands (`rm -rf`, `del /f`).
- `SATISFIED`: Confirmed resolution of bugs or successful tasks.

### Developer Intelligence & Coding Assistance (Step 05)

GhostTrace provides an offline-first developer assistant powered by local inference and safe static analysis of explicitly supplied user code.

#### The Six Core Capabilities

1. **Code Explanation (`EXPLAIN_CODE`):**
   - Step-by-step logic breakdown, important functions, inputs/outputs, edge cases, and algorithmic complexity.
   - Example: `ghost> Explain this Python function: def factorial(n): ...` or `dev explain def factorial(n): ...`
2. **Debugging Assistance (`DEBUG_CODE`):**
   - Triage tracebacks, compiler/runtime errors, and unexpected behavior. Distinguishes observed facts from hypotheses and provides minimal, verified fixes.
   - Example: `ghost> Traceback (most recent call last): File "app.py", line 4, in <module> ...` or `dev debug <error>`
3. **Code Review (`REVIEW_CODE`):**
   - Reviews explicitly provided code across correctness, readability, maintainability, error handling, performance, and security.
   - Structured findings with severity categories: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.
   - Example: `ghost> Review this code: ...` or `dev review <code>`
4. **Code Generation (`GENERATE_CODE`):**
   - Synthesizes functions, classes, algorithms, utility scripts, CLI examples, and tests based on explicit requirements.
   - Includes necessary imports, explains design assumptions, and clearly states that code is proposed (not yet executed).
   - Example: `ghost> Write a Python CLI tool using Typer for batch resizing images` or `dev generate <prompt>`
5. **Refactoring Assistance (`REFACTOR_CODE`):**
   - Proposes cleaner implementations by separating responsibilities, improving naming, reducing duplication, and enhancing error handling while preserving behavior.
   - Highlights the original issue, refactored implementation, and potential behavioral trade-offs.
   - Example: `ghost> Refactor this JavaScript function: ...` or `dev refactor <code>`
6. **Test Generation (`GENERATE_TESTS`):**
   - Generates comprehensive unit tests covering normal cases, boundary conditions, edge cases, and exception handling.
   - Defaults to `pytest` for Python and infers standard test frameworks for other languages.
   - Example: `ghost> Write pytest tests for this function: ...` or `dev tests <code>`

#### Supported Programming Languages

GhostTrace features lightweight, local language awareness across 15+ languages:
- **Languages:** Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, HTML, CSS, SQL, Bash, PowerShell.
- **Detection:** Inferred safely from user hints, markdown code fences (```` ```python ````), file extension mentions, and recognizable syntax patterns without reading the user's filesystem.

#### Safe Local Code Analysis (`dev analyze`)

GhostTrace includes a zero-execution static analysis engine:
- **Python AST Inspection:** Validates syntax using standard library `ast.parse`, discovering functions, classes, imports, bare except clauses, and infinite loops with exact line numbers and syntax error diagnostics.
- **Polyglot Delimiter Analysis:** Checks brace/bracket/parenthesis balance across other languages.
- **Strict Safety Boundaries:** Static analysis **NEVER** executes code, imports user modules, evaluates expressions, creates files, or runs shell commands.

#### Developer Command Family (`dev`)

- `dev` — Displays active developer intelligence status and available capabilities.
- `dev help` — Comprehensive guide to developer tasks and command syntax.
- `dev status` — Detailed developer subsystem status and configuration limits.
- `dev language` — Lists supported languages and detection methods.
- `dev analyze <code>` — Runs safe local static analysis on supplied code without AI inference.
- `dev explain <code>` — Explicitly triggers code explanation.
- `dev debug <error/code>` — Explicitly triggers debugging triage.
- `dev review <code>` — Explicitly triggers structured code review.
- `dev generate <spec>` — Explicitly triggers code generation.
- `dev refactor <code>` — Explicitly triggers code refactoring.
- `dev tests <code>` — Explicitly triggers unit test generation.
- `dev enable` / `dev disable` — Toggles developer intelligence at runtime.

### Keyboard Shortcuts

- <kbd>Enter</kbd> — Submit the command or AI prompt in the input field.
- <kbd>Up Arrow</kbd> — Navigate backwards through session command history.
- <kbd>Down Arrow</kbd> — Navigate forwards through session command history.
- <kbd>Ctrl</kbd>+<kbd>L</kbd> — Clear the conversation buffer.
- <kbd>Ctrl</kbd>+<kbd>C</kbd> — Gracefully exit GhostTrace.
- <kbd>Escape</kbd> — Reset current input field or interrupt generation.

---

## 9. Terminal Interface Visual Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ GHOSTTRACE v0.5.0 │ GHOST: FORGOTTEN MACHINE (DORMANT) │ AI: READY     │
├──────────────────────────────────────────────┬─────────────────────────┤
│ ConversationLog                              │ StatusPanel             │
│                                              │                         │
│ [Something has awakened inside this terminal]│ GhostTrace v0.5.0       │
│                                              │                         │
│ ghost> Explain Python decorators             │ Environment: development│
│ GHOSTTRACE:                                  │ Commands Run: 3         │
│ A Python decorator is a callable that wraps  │                         │
│ another function to extend its behavior...   │ Subsystems:             │
│                                              │ • Foundation : OK       │
│ ghost> ghost set phantom-coder               │ • Interface  : ACTIVE   │
│ Active personality switched to: Phantom Coder│ • AI Engine  : READY    │
│ "Ah, another bug to chase. Excellent."       │ • Persona    : ACTIVE   │
│                                              │ • Dev Intel  : ACTIVE   │
│                                              │                         │
├──────────────────────────────────────────────┴─────────────────────────┤
│ ghost> [ Enter command or ask a programming question...              ] │
├────────────────────────────────────────────────────────────────────────┤
│ Enter: Submit  │  Ctrl+L: Clear  │  Ctrl+C: Quit  │  Esc: Cancel       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Testing & Code Quality

Run the automated test suite with coverage report:

```powershell
pytest --cov=ghosttrace --cov-report=term-missing
```

Run Ruff linter:

```powershell
ruff check .
```

Run Ruff code formatter check:

```powershell
ruff format --check .
```

---

## 11. License

This project is licensed under the MIT License. See [LICENSE](file:///D:/GhostTrace/LICENSE) for details.
