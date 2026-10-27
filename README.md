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
- **Testing & Quality:** pytest, pytest-cov, Ruff
- **Planned AI Subsystem:** Qwen2.5 Instruct GGUF executed via `llama-cpp-python` / `llama.cpp`
- **Planned Terminal UI:** Rich + Textual
- **Planned Persistence:** SQLite (WAL mode)
- **Planned Command CLI:** Typer

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
| **Entry Point CLI** | **Completed** | `ghosttrace` executable and `python -m ghosttrace.main` |
| **Testing Suite** | **Completed** | Deterministic pytest suite (100% test coverage) |
| **Code Formatting & Linting**| **Completed** | Full Ruff rule enforcement and code formatting |
| *Local AI Model Engine* | *Planned* | Step 02 / 03: GGUF pipeline and local llama.cpp engine |
| *Terminal Interface* | *Planned* | Step 05: Rich / Textual interactive TUI |
| *Ghost Persona Engine* | *Planned* | Step 06: Atmospheric reactions and behavioral states |
| *Terminal Guardian* | *Planned* | Step 07: Safety interceptor and command risk classifier |
| *Persistent Memory* | *Planned* | Step 08: SQLite history and session management |

---

## 5. 10-Step Development Roadmap

- [x] **Step 01: Project Foundation, Environment & Configuration** *(Current)*
- [ ] **Step 02: Model Management & GGUF Pipeline**
- [ ] **Step 03: Local Inference Engine (llama.cpp integration)**
- [ ] **Step 04: Prompt Architecture & Streaming AI Orchestration**
- [ ] **Step 05: Rich & Textual Terminal Interface**
- [ ] **Step 06: Digital Ghost Persona & Atmospheric Engine**
- [ ] **Step 07: Terminal Guardian & Command Safety System**
- [ ] **Step 08: Persistent Memory & SQLite History**
- [ ] **Step 09: System Telemetry & Hardware Resource Adaptation**
- [ ] **Step 10: Packaging, Distribution & Production Hardening**

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

Create the Python 3.11 virtual environment:

```powershell
py -3.11 -m venv .venv
```

Activate the virtual environment:

```powershell
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

Application settings can be configured via `.env` or standard environment variables prefixed with `GHOSTTRACE_`:

- `GHOSTTRACE_ENV`: Operational environment (`development`, `production`, `testing`). Default: `development`.
- `GHOSTTRACE_DEBUG`: Enable debug output (`true` / `false`). Default: `false`.
- `GHOSTTRACE_LOG_LEVEL`: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default: `INFO`.
- `GHOSTTRACE_APP_DATA_DIR`: Base storage path. Default: `%LOCALAPPDATA%\GhostTrace`.

---

## 7. Launching the Application

Execute GhostTrace directly through either method:

### Method A: Console Entry Point
```powershell
ghosttrace
```

### Method B: Python Module Invocation
```powershell
python -m ghosttrace.main
```

Expected startup output:
```text
==================================================
 GhostTrace v0.1.0
 Offline-first AI-powered haunted terminal companion.
==================================================
Environment : development
Log Level   : INFO
App Data    : C:\Users\<User>\AppData\Local\GhostTrace
Logs        : C:\Users\<User>\AppData\Local\GhostTrace\logs
--------------------------------------------------
Foundation initialized successfully. Ready for Step 02.
==================================================
```

---

## 8. Testing & Code Quality

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

## 9. License

This project is licensed under the MIT License. See [LICENSE](file:///D:/GhostTrace/LICENSE) for details.
