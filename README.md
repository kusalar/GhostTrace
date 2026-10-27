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
- **Testing & Quality:** pytest, pytest-cov, pytest-asyncio, Ruff
- **Planned AI Subsystem:** Qwen2.5 Instruct GGUF executed via `llama-cpp-python` / `llama.cpp`
- **Planned Persistence:** SQLite (WAL mode)

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
| **Testing Suite** | **Completed** | Deterministic unit and async TUI tests (>98% coverage) |
| *Local AI Integration* | *Planned* | Step 03: GGUF pipeline and local llama.cpp engine |
| *Ghost Persona Engine* | *Planned* | Step 04: Atmospheric reactions and behavioral states |
| *Developer Intelligence* | *Planned* | Step 05: Code synthesis, explanation, and error triage |
| *Terminal Guardian* | *Planned* | Step 06: Safety interceptor and command risk classifier |
| *Persistent Memory* | *Planned* | Step 07: SQLite history and session management |
| *System Diagnostics* | *Planned* | Step 08: OS telemetry and hardware resource adaptation |
| *Haunted Experience* | *Planned* | Step 09: Interactive events and atmospheric haunting |
| *Packaging & Hardening* | *Planned* | Step 10: Production release packaging and distribution |

---

## 5. 10-Step Development Roadmap

- [x] **Step 01: Foundation, Environment & Configuration**
- [x] **Step 02: Interactive Terminal Interface & CLI** *(Current)*
- [ ] **Step 03: Local AI Integration**
- [ ] **Step 04: Ghost Personality & Behaviour Engine**
- [ ] **Step 05: Developer Intelligence & Coding Assistance**
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

Install the project in editable mode with development dependencies:

```powershell
pip install --upgrade pip
pip install -e ".[dev]"
```

### 6.4 Configuration

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
# Output: GhostTrace v0.2.0
```

### 7.4 Help Information
```powershell
ghosttrace --help
```

---

## 8. Interactive Terminal Commands & Keyboard Shortcuts

Inside the interactive terminal interface, enter commands at the `ghost>` prompt:

### Built-in Commands

| Command | Description |
| :--- | :--- |
| `help` (or `?`) | Displays all available commands with descriptions. Use `help <cmd>` for specific usage. |
| `about` (or `info`) | Displays project vision, triple identity, and target specifications. |
| `status` | Displays application status distinguishing implemented from planned features. |
| `version` (or `v`) | Displays the GhostTrace version. |
| `clear` (or `cls`) | Clears the scrollable conversation log. |
| `history` (or `hist`) | Lists commands entered during the active session. |
| `ai` | Displays AI engine status (`AI ENGINE: NOT CONNECTED`, scheduled for Step 03). |
| `ghost` | Displays ghost subsystem status (`PERSONALITY ENGINE: NOT IMPLEMENTED`, scheduled for Step 04). |
| `exit` (or `quit`, `q`)| Gracefully terminates the terminal session. |

### Keyboard Shortcuts

- <kbd>Enter</kbd> — Submit the command in the input field.
- <kbd>Up Arrow</kbd> — Navigate backwards through session command history.
- <kbd>Down Arrow</kbd> — Navigate forwards through session command history.
- <kbd>Ctrl</kbd>+<kbd>L</kbd> — Clear the conversation buffer.
- <kbd>Ctrl</kbd>+<kbd>C</kbd> — Gracefully exit GhostTrace.
- <kbd>Escape</kbd> — Reset/clear current input field.

---

## 9. Terminal Interface Visual Layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ GHOSTTRACE v0.2.0    │  ENTITY: AWAKE  │  AI ENGINE: NOT CONNECTED     │
├──────────────────────────────────────────────┬─────────────────────────┤
│ ConversationLog                              │ StatusPanel             │
│                                              │                         │
│ [Something has awakened inside this terminal]│ GhostTrace v0.2.0       │
│                                              │                         │
│ ghost> help                                  │ Environment: development│
│ +------------------------------------------+ │ Commands Run: 3         │
│ | Command | Description                    | │                         │
│ +------------------------------------------+ │ Subsystems:             │
│ | help    | Show available commands        | │ • Foundation : OK       │
│ | status  | System diagnostic status       | │ • Interface  : ACTIVE   │
│ | exit    | Leave GhostTrace               | │ • AI Engine  : OFFLINE  │
│ +------------------------------------------+ │ • Persona    : STEP 04  │
│                                              │                         │
├──────────────────────────────────────────────┴─────────────────────────┤
│ ghost> [ Enter command (e.g., 'help', 'status', 'ai', 'exit')...     ] │
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
