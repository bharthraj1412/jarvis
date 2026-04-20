<div align="center">

# 🤖 J.A.R.V.I.S — MK37

**Just A Rather Very Intelligent System**

*A multi-modal, multi-backend AI assistant that transforms your OS into a living, intelligent platform.*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)]()
[![Tools](https://img.shields.io/badge/Tools-43-orange)]()
[![Skills](https://img.shields.io/badge/Skills-45-purple)]()
[![Agents](https://img.shields.io/badge/Sub--Agents-8-red)]()

*Engineered by [Bharth Raj](https://github.com/bharthraj1412)*

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Tool Registry (43 Tools)](#-tool-registry-43-tools)
- [Skill Library (45 Skills)](#-skill-library-45-skills)
- [Sub-Agent System (8 Agents)](#-sub-agent-system-8-agents)
- [Memory & Persistence](#-memory--persistence)
- [Red Team & Security](#-red-team--security)
- [Screen Sharing](#-screen-sharing)
- [Configuration](#-configuration)
- [Contributing](#-contributing)

---

## 🧠 Overview

**JARVIS MK37** is a production-grade, multi-modal AI assistant platform featuring:

- **Voice Interface** — Real-time conversation via Gemini Live with native audio I/O
- **CLI Orchestrator** — ReAct-loop terminal for chained, autonomous multi-step task execution
- **Multi-Backend Routing** — Intelligent dispatch across 6 LLM providers (Gemini, Anthropic, OpenAI, Mistral, NVIDIA NIM, Ollama)
- **43 Deterministic Tools** — From web search and code sandboxing to red-team recon and full desktop automation
- **45 Reusable Skills** — Professional prompt templates for DevOps, security, data analysis, and more
- **8 Sub-Agent Types** — Spawn isolated worker agents for parallel, specialized workflows
- **Persistent Memory** — ChromaDB vector embeddings + SQLite session history with semantic linking

Whether you're automating DevSecOps workflows, controlling your desktop by voice, or running full penetration test reconnaissance — JARVIS MK37 handles it locally, privately, and with zero subscriptions when running Ollama.

---

## ⚡ Key Features

| Category | Capabilities |
|---|---|
| **Voice & Vision** | Real-time Gemini Live audio, screen capture analysis, webcam vision processing |
| **Multi-Backend AI** | Gemini • Anthropic Claude • OpenAI GPT • Mistral • NVIDIA NIM • Ollama (100% offline) |
| **Desktop Automation** | Mouse/keyboard control, AI-powered screen element detection, window management |
| **System Control** | App launching, file management, system monitoring, computer settings (brightness, volume, WiFi) |
| **Code Execution** | Sandboxed Python/JS/Bash/PowerShell execution with timeout and isolation |
| **Web Intelligence** | DuckDuckGo search, headless browser page fetching, raw HTTP scraping |
| **Red Team / OSINT** | Port scanning, DNS enumeration, HTTP header audits, WHOIS, nmap integration |
| **Sub-Agents** | Threaded worker agents (coder, reviewer, researcher, tester, editor, sysadmin, devops) |
| **Memory Engine** | ChromaDB vector similarity, persistent file-based memory, working memory with consolidation |
| **Screen Sharing** | WebSocket-based real-time desktop broadcasting with multi-monitor support |
| **Game Management** | Steam & Epic Games library management, update scheduling, download monitoring |
| **Media** | YouTube search/play/summarize/trending, flight search via Google Flights |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JARVIS MK37                          │
├──────────────┬──────────────────────────────────────────┤
│  main.py     │  main_mk37.py                           │
│  Voice GUI   │  CLI Orchestrator (ReAct Loop)           │
├──────────────┴──────────────────────────────────────────┤
│                   router.py                             │
│      Keyword-based intelligent backend routing          │
├─────┬─────┬─────┬─────┬─────┬───────────────────────────┤
│Gemini│Claude│GPT │Mistrl│NVIDIA│ Ollama (offline)       │
├─────┴─────┴─────┴─────┴─────┴───────────────────────────┤
│                tools/registry.py                        │
│            43 tools · _run_async() helper               │
├──────────────┬──────────────┬───────────────────────────┤
│  actions/    │  redteam/    │  multi_agent/             │
│  18 modules  │  scope+recon │  8 agent types            │
├──────────────┴──────────────┴───────────────────────────┤
│                  memory/                                │
│  vector_store · memory_manager · persistent_store       │
│  working · consolidator · context · scan                │
├─────────────────────────────────────────────────────────┤
│             skills/ (45 built-in)                       │
│       YAML/Markdown prompt templates                    │
└─────────────────────────────────────────────────────────┘
```

### Backend Routing

The `router.py` engine uses keyword-based routing to dispatch tasks to the optimal backend:

| Backend | Optimized For | Offline? |
|---|---|---|
| **Gemini** | Search, long context, vision, general chat | No |
| **Anthropic Claude** | Coding, security analysis, structured output | No |
| **OpenAI GPT** | Creative tasks, broad knowledge | No |
| **Mistral** | Fast inference, multilingual | No |
| **NVIDIA NIM** | GPU-accelerated inference | No |
| **Ollama** | Privacy-first, fully local | ✅ Yes |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (tested on 3.11, 3.12, 3.14)
- **Git**
- A microphone + speakers (for voice mode)

### Installation

```bash
# Clone the repository
git clone https://github.com/bharthraj1412/jarvis.git
cd jarvis

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_mk37.txt

# Install browser automation (for web tools)
playwright install
```

### Configuration

1. Copy `.env.template` to `.env` and fill in your API keys:
   ```
   GEMINI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here     # optional
   OPENAI_API_KEY=your_key_here        # optional
   MISTRAL_API_KEY=your_key_here       # optional
   ```

2. Create `config/api_keys.json`:
   ```json
   {
     "gemini_api_key": "your_gemini_key"
   }
   ```

> **💡 Minimum requirement:** Only a Gemini API key is needed. All other backends are optional and degrade gracefully.

---

## 🎯 Usage

### Option 1: Voice Interface

```bash
python main.py
```

Opens a native GUI with real-time voice conversation powered by Gemini Live. Features:
- Push-to-talk and always-on listening modes
- Mute toggle (F4)
- Full tool execution via voice commands
- Real-time output/input transcription logging

### Option 2: CLI Orchestrator

```bash
python main_mk37.py
```

A rich terminal interface with the ReAct (Reason + Act) loop for autonomous multi-step task execution. Slash commands:

| Command | Description |
|---|---|
| `/skills` | List all available skills |
| `/memory` | Browse persistent memories |
| `/agents` | List active sub-agents |
| `/mode recon` | Switch persona (recon, exploit, coder, analyst, general) |
| `/install-skills` | Install skills from external GitHub repos |
| `/quit` | Exit (auto-consolidates working memory) |

### Option 3: Auto-Start (Windows)

```bash
python install_startup.py
```

Installs a silent background launcher that starts JARVIS automatically on Windows login.

---

## 🔧 Tool Registry (43 Tools)

### Web & Search
| Tool | Description |
|---|---|
| `web_search` | DuckDuckGo search with configurable result count |
| `fetch_page` | Headless browser page text extraction |
| `fetch_raw` | Raw HTTP GET content fetching |

### Code Execution
| Tool | Description |
|---|---|
| `run_code` | Sandboxed Python/JS/Bash execution with timeout |

### File Management
| Tool | Description |
|---|---|
| `file_read` | Read workspace files |
| `file_write` | Write to workspace files |
| `file_list` | List workspace directory contents |

### Desktop Automation
| Tool | Description |
|---|---|
| `cursor_move` / `cursor_click` | Mouse positioning and clicking |
| `keyboard_type` / `keyboard_hotkey` / `keyboard_press` | Text input and key combos |
| `screen_find` / `screen_click` / `smart_click` | AI-powered visual element detection |
| `clipboard_read` / `clipboard_write` | Clipboard operations |
| `focus_window` | Bring windows to foreground |
| `take_screenshot` | Screen capture |
| `mouse_scroll` / `mouse_drag` | Scrolling and drag operations |

### Red Team / Security
| Tool | Description |
|---|---|
| `port_scan` | Scope-checked TCP port scanning |
| `dns_enum` | DNS record enumeration (A, MX, NS, TXT, CNAME) |
| `headers_audit` | HTTP security header analysis |
| `whois_lookup` | Domain WHOIS information |
| `nmap_scan` | Service scan (requires nmap) |
| `generate_report` | Professional pentest report generation |

### Memory
| Tool | Description |
|---|---|
| `memory_save` / `memory_delete` | Persistent memory CRUD |
| `memory_search` / `memory_list` | Memory search and browsing |

### Sub-Agents
| Tool | Description |
|---|---|
| `spawn_agent` | Launch autonomous worker agents |
| `send_message` / `check_agent` / `list_agents` | Agent communication and monitoring |
| `list_agent_types` | Show available agent definitions |

### Skills
| Tool | Description |
|---|---|
| `run_skill` / `list_skills` | Execute and browse reusable skills |

### System
| Tool | Description |
|---|---|
| `system_monitor` | CPU, RAM, disk, network, process telemetry |
| `screen_share_start` / `screen_share_stop` / `screen_share_status` | WebSocket desktop broadcasting |
| `list_monitors` | Multi-monitor enumeration |

---

## 📚 Skill Library (45 Skills)

Skills are reusable prompt templates executed via the `/skills` system or the `run_skill` tool.

### Core Development
| Skill | Description |
|---|---|
| `commit` | Git commit with structured messages |
| `review` / `code_review` | Code review with severity levels |
| `edit` | Precise file editing with minimal changes |
| `refactor` | Refactor without changing behavior |
| `tdd` | Test-driven development workflow |

### DevOps & Infrastructure
| Skill | Description |
|---|---|
| `docker_deploy` / `docker_compose` | Docker container management |
| `ci_cd` | CI/CD pipeline generation (GitHub Actions, GitLab CI) |
| `nginx_config` | Nginx configuration generation |
| `terraform_gen` | Infrastructure-as-Code templates |
| `env_setup` | Development environment setup |
| `cron_scheduler` | Scheduled task creation |

### Security & OSINT
| Skill | Description |
|---|---|
| `security_scan` | Automated security scanning |
| `osint_recon` | Open-source intelligence gathering |
| `ssl_check` | SSL/TLS certificate auditing |
| `hash_lookup` | File hash computation and lookup |
| `log_analysis` | Security log threat analysis |
| `dep_audit` | Dependency vulnerability audit |

### Data & APIs
| Skill | Description |
|---|---|
| `csv_analysis` | CSV/JSON data analysis |
| `json_transform` | JSON format transformation |
| `regex_builder` | Regex pattern building and testing |
| `db_query` | SQL query writing and optimization |
| `chart_gen` | Data visualization generation |
| `api_design` | RESTful API design |

### Editor Integration
| Skill | Description |
|---|---|
| `editor_open` / `editor_goto` | File navigation in VS Code/Cursor |
| `editor_insert` / `editor_replace` | Direct code editing |
| `editor_terminal` | Integrated terminal commands |

### Documentation & Communication
| Skill | Description |
|---|---|
| `doc_gen` | Technical documentation generation |
| `changelog` | Changelog from git history |
| `meeting_notes` | Structured meeting notes |
| `email_draft` | Professional email drafting |

### System Administration
| Skill | Description |
|---|---|
| `system_info` | System diagnostics report |
| `process_mgr` | Process monitoring and management |
| `network_diag` | Network troubleshooting |
| `disk_cleanup` | Disk space analysis |

### Specialized
| Skill | Description |
|---|---|
| `github_scan` | GitHub repository analysis |
| `screenshot_fix` | Visual error detection and auto-fix |
| `project_scaffold` | Full project generation from description |
| `site_monitor` | Website uptime monitoring |
| `research` | Deep web research with citations |
| `pc_control` | Desktop automation workflows |
| `git_flow` | Git branch management |

---

## 🤖 Sub-Agent System (8 Agents)

JARVIS can delegate complex workflows by spawning threaded sub-agents that operate independently within the ReAct loop.

| Agent | Specialization | Tools |
|---|---|---|
| `general-purpose` | Multi-step research and task execution | All |
| `coder` | Clean, idiomatic code writing and modification | All |
| `reviewer` | Code quality, security, and correctness analysis | file_read, file_list, web_search |
| `researcher` | Codebase exploration and evidence-based answers | file_read, file_list, web_search, fetch_page |
| `tester` | Test writing and failure diagnosis | All |
| `editor` | File editing via keyboard/mouse automation | file_*, run_code, keyboard_*, screen_* |
| `sysadmin` | System configuration and service diagnostics | run_code, file_read, file_list, system_monitor |
| `devops` | Docker, CI/CD, deployment, infrastructure | run_code, file_*, web_search, system_monitor |

> **Custom agents:** Create `.md` files in `~/.jarvis/agents/` with YAML frontmatter to define custom agent types.

---

## 💾 Memory & Persistence

JARVIS maintains full context between sessions through a layered memory system:

### Working Memory
- Short-term conversation context
- Automatic trimming to stay within token limits
- Consolidates to persistent storage on session exit

### Persistent Memory (File-Based)
- Markdown files with YAML frontmatter in `~/.jarvis/memory/`
- Supports user, project, system, and insight memory types
- Keyword search with freshness scoring and decay ranking

### Vector Memory (ChromaDB)
- Semantic similarity search via `all-MiniLM-L6-v2` embeddings
- Graceful degradation — fully functional without chromadb installed
- Automatic empty-collection handling

### Session History (SQLite)
- Complete session tracking with semantic linking
- Cross-session context retrieval

---

## 🛡 Red Team & Security

### Permission System

| Mode | Behavior |
|---|---|
| `ALLOW_ALL` | All tools execute immediately (default) |
| `CONFIRM_ALL` | User approval required for each tool |
| `DENY_LIST` | Block specific tools via `JARVIS_DENY_TOOLS` env var |

### Scope Enforcement
- Defined in `current_scope.json`
- Restricts target hosts, domains, and allowed actions
- All red-team tools check scope before execution
- Persistent audit logging to `~/.jarvis/audit.log`

---

## 📺 Screen Sharing

Real-time WebSocket-based desktop broadcasting:

```bash
# Start sharing (from JARVIS or via tool)
screen_share_start  # default: port 8765, 10 FPS, 60% quality

# Open viewer
# Navigate to screen_server/viewer.html in your browser
```

Features:
- Multi-monitor support with `list_monitors`
- Configurable FPS and JPEG quality
- Built-in HTML5 viewer with auto-reconnect

---

## ⚙ Configuration

### Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (required) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (optional) |
| `OPENAI_API_KEY` | OpenAI API key (optional) |
| `MISTRAL_API_KEY` | Mistral AI API key (optional) |
| `NVIDIA_API_KEY` | NVIDIA NIM API key (optional) |
| `OLLAMA_HOST` | Ollama server URL (default: http://localhost:11434) |
| `JARVIS_DENY_TOOLS` | Comma-separated list of blocked tools |

### File Structure

```
Jarvis-MK37/
├── main.py                 # Voice GUI interface
├── main_mk37.py            # CLI orchestrator
├── orchestrator.py          # ReAct loop engine
├── router.py               # Multi-backend routing
├── start.py                # Unified launcher
├── actions/                # 18 action modules
│   ├── browser_control.py
│   ├── computer_control.py
│   ├── computer_settings.py
│   ├── flight_finder.py
│   ├── game_updater.py
│   ├── screen_share.py
│   ├── youtube_video.py
│   └── ...
├── agent/                  # Task executor + planner
│   ├── executor.py
│   ├── planner.py
│   └── error_handler.py
├── memory/                 # Memory subsystem
│   ├── vector_store.py
│   ├── memory_manager.py
│   ├── persistent_store.py
│   ├── working.py
│   └── consolidator.py
├── multi_agent/            # Sub-agent system
│   └── subagent.py
├── tools/                  # Tool registry + web tools
│   ├── registry.py
│   ├── web.py
│   ├── sandbox.py
│   └── files.py
├── redteam/                # Security tooling
│   ├── scope.py
│   ├── recon.py
│   └── vuln_scanner.py
├── skills/                 # 45 built-in skills
├── screen_server/          # WebSocket screen sharing
│   └── viewer.html
├── config/                 # API keys + model config
├── *_backend.py            # 6 LLM backend adapters
└── requirements*.txt       # Dependencies
```

---

## 🔄 Recent Updates (v37.1 — April 2026)

### Bug Fixes (15 fixes across 8 files)
- **Critical:** Fixed crash on startup without chromadb — now degrades gracefully
- **Critical:** Fixed sub-agent crash when spawned from voice mode (orchestrator=None)
- **Critical:** Fixed YouTube TTS silence — speak parameter now correctly passed
- **Major:** Fixed `asyncio.run()` inside running event loop — new `_run_async()` helper
- **Major:** Fixed `_VoiceBridge` missing attributes for fork-mode skills
- **Major:** Fixed `mk37_chat` overwriting voice session's orchestrator reference
- **Major:** Replaced fragile `from config import` with portable `platform.system()` helpers
- **Minor:** Fixed dict mutation during memory trimming iteration
- **Minor:** Fixed `winreg` import on non-Windows platforms
- **Minor:** Hidden skills no longer shown in `/skills` list
- **Minor:** Empty memory search returns friendly message instead of empty string
- **Minor:** Empty ChromaDB collection query handled safely

### Dependency Updates
- Installed `psutil` for system monitoring
- Installed `youtube-transcript-api` for video summarization

---

## 👤 Author

Developed and maintained by **Bharth Raj** — [@bharthraj1412](https://github.com/bharthraj1412)

---

<div align="center">

⭐ **Star this repository to support the journey to Mark 85!** ⭐

</div>
