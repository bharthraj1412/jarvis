<div align="center">
  <h1>🤖 JARVIS MK37</h1>
  <p><b>The Ultimate Multi-Backend, Cross-Platform Personal AI Assistant</b></p>
  <p><i>Engineered by Bharth Raj</i></p>
</div>

---

## ✨ Overview

**JARVIS MK37** is an advanced, multi-modal AI assistant platform that transforms your operating system into a living, breathing intelligent entity. Operating as both a voice-powered interactive assistant and a high-performance command-line orchestrator, it allows for dynamic switching between multiple LLM backends to execute complex workflows across different environments.

Whether you're running DevSecOps, scheduling tasks, automating UI clicks, or chatting locally, JARVIS MK37 is an extension of your digital life—running locally and supporting zero subscriptions.

---

## ⚡ Core Features

- 🎙️ **Real-time Voice & Vision:** Ultra-low latency conversation coupled with real-time screen processing and webcam vision.
- 📺 **Live Screen Sharing:** Real-time WebSocket-based desktop broadcasting via native UI viewer at high frame rates (`mss` powered).
- 🧠 **Multi-Backend AI:** Intelligent routing between Gemini, Anthropic, OpenAI, Mistral, NVIDIA NIM, and 100% offline, privacy-first **Ollama**.
- 🛠️ **System Control & Automation:** Launch apps, manage files, fetch system telemetry, execute terminal commands, and perform Python-native mouse/keyboard automation.
- 🫂 **Sub-Agent Delegation:** Spin up isolated sub-agents mimicking specialized roles (Coder, Reviewer, Devops, Sysadmin) to handle multi-step workflows.
- 💾 **Persistent Hyper-Memory & History:** SQLite-backed complete session tracking. ChromaDB vector embeddings prevent context-amnesia. JARVIS actively remembers your projects, relationships, and history between reboots.
- 🛡️ **Red Teaming & Security:** Built for DevSecOps users with `ALLOW_ALL` / `CONFIRM_ALL` permission modes, persistent JSONL audit logs, and strict Scope Enforcement.

---

## 🖥️ Cross-Platform Support
**Fully Supported on:** Windows 10/11, macOS, and Linux.

JARVIS MK37 leverages `sys.platform`, absolute pathlib resolution, and `utf-8` enforcing mechanisms to seamlessly operate from a WSL instance to native Windows 11.

---

## 🚀 Quick Start

Ensure you have Python 3.11 or 3.12 installed.

```bash
git clone https://github.com/bharthraj1412/jarvis.git
cd jarvis
pip install -r requirements_mk37.txt
pip install -r requirements.txt
playwright install
```

> ⚠️ **Installation Note:** Due to the cross-platform integration, OS-specific libraries are not all forcefully bundled. If you encounter a `ModuleNotFoundError`, simply run `pip install <module_name>` for your specific system.

### Launching JARVIS

**Option 1: Voice Interface**
```bash
python main.py
```
*Uses local audio transcription and system TTS. Features natively injected vision capabilities.*

**Option 2: CLI DevSecOps Orchestrator**
```bash
python main_mk37.py
```
*A professional, rich-text terminal interface featuring explicit slash commands (`/skills`, `/memory`, `/install-skills`).*

---

## ⚙️ Architecture & Tools

JARVIS combines over 30 deterministic Python tools with a dynamic "Skill" ecosystem representing repeatable prompt templates.

- **Tool Registry**: Includes Sandbox for secure code execution, Computer Settings manipulation via OS native queries, and Red Team OSINT recon.
- **Skill Ecosystem**: Ships with 45 built-in professional skills (DevOps templates, Security Scans, CI/CD).
- **External Installer**: Natively pull missing abilities from massive open-source GitHub hubs using `/install-skills`.

---

## 🛡️ Privacy & Restrictions

**Your Data Stays Yours.** 
With the Offline **Ollama Backend**, you can enforce 100% local, on-machine inference. 
A physical mute button is built-in (F4 / UI) to pause execution globally.

---

## 👤 Author

Developed and maintained by **Bharth Raj** [@bharthraj1412](https://github.com/bharthraj1412)

⭐ **Star the repository to support project development and the journey to Mark 85!**
