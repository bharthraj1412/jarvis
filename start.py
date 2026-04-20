# start.py — JARVIS MK37 Unified Launcher (v2)
from __future__ import annotations
"""
Production-grade launcher for JARVIS MK37.
Includes full system diagnostics, dependency verification, health checks,
and graceful process lifecycle management.

Usage:
    python start.py              → Interactive mode selector
    python start.py voice        → Voice assistant only (Gemini Live Audio GUI)
    python start.py cli          → CLI only (Rich terminal + multi-backend ReAct)
    python start.py both         → Both voice GUI + CLI in parallel
    python start.py --silent     → Auto-start voice (used by Windows Startup)
    python start.py --status     → Full system diagnostics
    python start.py --doctor     → Check + auto-install missing dependencies
    python start.py --version    → Show version info
"""

import importlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

VERSION = "37.1.0"
BUILD   = "2026-04-21"
CODENAME = "MARK XXXVII"

BASE_DIR = Path(__file__).resolve().parent
PYTHON   = sys.executable
LOG_DIR  = BASE_DIR / "logs"
PID_FILE = BASE_DIR / ".jarvis.pid"

# Force UTF-8 on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ── ANSI Helpers ─────────────────────────────────────────────────────────────

def _supports_color() -> bool:
    if sys.platform == "win32":
        os.system("")  # enable VT100 escape sequences on Windows 10+
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_COLOR = _supports_color()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text

def _bold(t: str) -> str:       return _c("1", t)
def _dim(t: str) -> str:        return _c("2", t)
def _cyan(t: str) -> str:       return _c("36", t)
def _green(t: str) -> str:      return _c("32", t)
def _yellow(t: str) -> str:     return _c("33", t)
def _red(t: str) -> str:        return _c("31", t)
def _magenta(t: str) -> str:    return _c("35", t)
def _blue(t: str) -> str:       return _c("34", t)
def _white_bold(t: str) -> str: return _c("1;37", t)

_OK   = _green("✓")
_WARN = _yellow("⚠")
_FAIL = _red("✗")
_SKIP = _dim("○")
_DOT  = _dim("·")


# ── Banner ───────────────────────────────────────────────────────────────────

def _banner():
    now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
    lines = [
        "",
        _cyan("  ╔══════════════════════════════════════════════════════╗"),
        _cyan("  ║") + _white_bold("        J.A.R.V.I.S  —  MARK XXXVII               ") + _cyan("║"),
        _cyan("  ║") + _dim("        Just A Rather Very Intelligent System       ") + _cyan("║"),
        _cyan("  ╠══════════════════════════════════════════════════════╣"),
        _cyan("  ║") + f"  Version : {_green(VERSION)}  {_dim('|')}  Build : {_dim(BUILD)}            " + _cyan("║"),
        _cyan("  ║") + f"  Python  : {_green(sys.version.split()[0])}   {_dim('|')}  Platform: {_dim(platform.system())}         " + _cyan("║"),
        _cyan("  ║") + f"  {_dim(now)}" + " " * max(0, 53 - len(now)) + _cyan("║"),
        _cyan("  ╚══════════════════════════════════════════════════════╝"),
        "",
    ]
    for line in lines:
        print(line)


# ── Dependency & Environment Checks ──────────────────────────────────────────

def _check_env() -> dict:
    """Check environment configuration and return status dict."""
    status = {"env_file": False, "config_file": False, "api_keys": {}}

    env_file    = BASE_DIR / ".env"
    config_file = BASE_DIR / "config" / "api_keys.json"

    status["env_file"]    = env_file.exists()
    status["config_file"] = config_file.exists()

    # Load .env if python-dotenv is available
    try:
        import dotenv
        if env_file.exists():
            dotenv.load_dotenv(env_file)
    except ImportError:
        pass

    # Check API keys
    key_map = {
        "GEMINI_API_KEY":    "Gemini",
        "GOOGLE_API_KEY":    "Gemini (alt)",
        "ANTHROPIC_API_KEY": "Claude",
        "OPENAI_API_KEY":    "GPT",
        "MISTRAL_API_KEY":   "Mistral",
        "NVIDIA_API_KEY":    "NVIDIA NIM",
    }
    for env_key, label in key_map.items():
        val = os.environ.get(env_key, "")
        status["api_keys"][label] = bool(val and len(val) > 5)

    # Also check config/api_keys.json
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                cfg = json.load(f)
            if cfg.get("gemini_api_key") and len(cfg["gemini_api_key"]) > 5:
                status["api_keys"]["Gemini"] = True
        except Exception:
            pass

    return status


def _check_module(name: str) -> tuple[bool, str]:
    """Check if a Python module is importable. Returns (ok, version_or_error)."""
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "OK")
        return True, str(ver)
    except ImportError as e:
        return False, str(e)


# ── System Diagnostics ───────────────────────────────────────────────────────

def show_status():
    """Comprehensive system health report."""
    _banner()
    env = _check_env()

    # ── Environment
    print(_bold("  ── Environment ─────────────────────────────────────"))
    print(f"   Base Directory  : {_dim(str(BASE_DIR))}")
    print(f"   Python          : {_green(sys.version.split()[0])} ({_dim(sys.executable)})")
    print(f"   Platform        : {platform.system()} {platform.release()}")

    venv = hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    print(f"   Virtual Env     : {_green('Active') if venv else _yellow('Not detected')}")

    env_icon = _OK if env["env_file"] else _FAIL
    cfg_icon = _OK if env["config_file"] else _WARN
    print(f"   .env file       : {env_icon} {'Found' if env['env_file'] else 'MISSING'}")
    print(f"   config/api_keys : {cfg_icon} {'Found' if env['config_file'] else 'Optional — not found'}")
    print()

    # ── API Keys / Backends
    print(_bold("  ── Backends ────────────────────────────────────────"))
    has_any = False
    for label, ok in env["api_keys"].items():
        if "alt" in label and not ok:
            continue  # don't show alt key if not set
        icon = _OK if ok else _SKIP
        status_txt = _green("Configured") if ok else _dim("Not configured")
        print(f"   {icon} {label:14s} : {status_txt}")
        if ok:
            has_any = True

    # Check Ollama
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import urllib.request
        req = urllib.request.Request(f"{ollama_host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            print(f"   {_OK} {'Ollama':14s} : {_green('Running')} at {_dim(ollama_host)}")
            has_any = True
    except Exception:
        print(f"   {_SKIP} {'Ollama':14s} : {_dim('Not running')} ({_dim(ollama_host)})")

    if not has_any:
        print(f"\n   {_WARN} {_yellow('No backends configured! Add at least one API key to .env')}")
    print()

    # ── Core Modules
    print(_bold("  ── Core Modules ────────────────────────────────────"))
    core_modules = [
        ("google.genai",     "Google GenAI SDK"),
        ("sounddevice",      "Audio I/O"),
        ("requests",         "HTTP Client"),
        ("httpx",            "Async HTTP"),
        ("PIL",              "Image Processing"),
        ("numpy",            "Numerics"),
        ("psutil",           "System Monitor"),
    ]
    core_ok = 0
    for mod_name, label in core_modules:
        ok, ver = _check_module(mod_name)
        if ok:
            print(f"   {_OK} {label:20s} {_dim(ver)}")
            core_ok += 1
        else:
            print(f"   {_FAIL} {label:20s} {_red('MISSING')} — pip install {mod_name}")
    print()

    # ── Optional Modules
    print(_bold("  ── Optional Modules ────────────────────────────────"))
    optional_modules = [
        ("chromadb",                "ChromaDB Vector Store"),
        ("sentence_transformers",   "Sentence Transformers"),
        ("youtube_transcript_api",  "YouTube Transcripts"),
        ("anthropic",               "Anthropic SDK"),
        ("openai",                  "OpenAI SDK"),
        ("mistralai",               "Mistral SDK"),
        ("pyautogui",               "Desktop Automation"),
        ("rich",                    "Rich Terminal UI"),
        ("playwright",              "Browser Automation"),
    ]
    for mod_name, label in optional_modules:
        ok, ver = _check_module(mod_name)
        if ok:
            print(f"   {_OK} {label:24s} {_dim(ver)}")
        else:
            print(f"   {_SKIP} {label:24s} {_dim('Not installed (optional)')}")
    print()

    # ── Skills & Agents
    print(_bold("  ── Skills & Agents ─────────────────────────────────"))
    try:
        sys.path.insert(0, str(BASE_DIR))
        from skills import load_skills
        skills = load_skills()
        print(f"   {_OK} Skills loaded    : {_green(str(len(skills)))}")
    except Exception as e:
        print(f"   {_FAIL} Skills           : {_red(str(e)[:60])}")

    try:
        from multi_agent.subagent import load_agent_definitions
        defs = load_agent_definitions()
        print(f"   {_OK} Agent types      : {_green(str(len(defs)))} ({_dim(', '.join(sorted(defs.keys())))})")
    except Exception as e:
        print(f"   {_FAIL} Agent types      : {_red(str(e)[:60])}")

    try:
        from tools.registry import TOOL_SCHEMAS
        print(f"   {_OK} Tools registered : {_green(str(len(TOOL_SCHEMAS)))}")
    except Exception as e:
        print(f"   {_FAIL} Tools            : {_red(str(e)[:60])}")
    print()

    # ── Memory
    print(_bold("  ── Memory ──────────────────────────────────────────"))
    try:
        from memory.vector_store import VectorMemory
        vm = VectorMemory()
        if vm.available:
            print(f"   {_OK} Vector memory    : {_green('Operational')}")
        else:
            print(f"   {_WARN} Vector memory    : {_yellow('Degraded (chromadb unavailable)')}")
    except Exception as e:
        print(f"   {_FAIL} Vector memory    : {_red(str(e)[:60])}")

    mem_dir = Path.home() / ".jarvis" / "memory"
    if mem_dir.exists():
        mem_count = len(list(mem_dir.glob("*.md")))
        print(f"   {_OK} Persistent store : {_green(f'{mem_count} memories')} in {_dim(str(mem_dir))}")
    else:
        print(f"   {_SKIP} Persistent store : {_dim('No memories saved yet')}")

    history_db = BASE_DIR / "history"
    if history_db.exists():
        db_files = list(history_db.glob("*.db")) + list(history_db.glob("*.sqlite3"))
        if db_files:
            print(f"   {_OK} Session history  : {_green(f'{len(db_files)} database(s)')}")
        else:
            print(f"   {_SKIP} Session history  : {_dim('No sessions recorded yet')}")
    print()

    # ── Summary
    total_checks = len(core_modules)
    pct = int(core_ok / total_checks * 100) if total_checks else 0
    if pct == 100:
        summary = _green(f"System health: {pct}% — All core modules operational")
    elif pct >= 70:
        summary = _yellow(f"System health: {pct}% — Some modules missing")
    else:
        summary = _red(f"System health: {pct}% — Critical modules missing")

    print(_bold("  ── Summary ─────────────────────────────────────────"))
    print(f"   {summary}")
    print()


# ── Doctor (auto-fix) ────────────────────────────────────────────────────────

def doctor():
    """Check dependencies and attempt to install missing ones."""
    _banner()
    print(_bold("  ── JARVIS Doctor — Dependency Check & Auto-Fix ────"))
    print()

    required = {
        "google-genai":       "google.genai",
        "sounddevice":        "sounddevice",
        "requests":           "requests",
        "httpx":              "httpx",
        "Pillow":             "PIL",
        "numpy":              "numpy",
        "psutil":             "psutil",
    }
    recommended = {
        "chromadb":               "chromadb",
        "sentence-transformers":  "sentence_transformers",
        "youtube-transcript-api": "youtube_transcript_api",
        "pyautogui":              "pyautogui",
        "pyperclip":              "pyperclip",
        "rich":                   "rich",
        "python-dotenv":          "dotenv",
        "duckduckgo-search":      "duckduckgo_search",
        "pyyaml":                 "yaml",
    }

    missing_required    = []
    missing_recommended = []

    print(_bold("  Required:"))
    for pip_name, import_name in required.items():
        ok, ver = _check_module(import_name)
        if ok:
            print(f"   {_OK} {pip_name:30s} {_dim(ver)}")
        else:
            print(f"   {_FAIL} {pip_name:30s} {_red('MISSING')}")
            missing_required.append(pip_name)

    print()
    print(_bold("  Recommended:"))
    for pip_name, import_name in recommended.items():
        ok, ver = _check_module(import_name)
        if ok:
            print(f"   {_OK} {pip_name:30s} {_dim(ver)}")
        else:
            print(f"   {_SKIP} {pip_name:30s} {_dim('Not installed')}")
            missing_recommended.append(pip_name)

    print()

    all_missing = missing_required + missing_recommended
    if not all_missing:
        print(f"   {_green('All dependencies satisfied. System is ready.')}")
        return

    if missing_required:
        print(f"   {_red(f'{len(missing_required)} required package(s) missing.')}")
    if missing_recommended:
        print(f"   {_yellow(f'{len(missing_recommended)} recommended package(s) missing.')}")

    print()
    try:
        answer = input(f"   Install {'all' if missing_recommended else 'required'} missing packages? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n   {_dim('Cancelled.')}")
        return

    if answer not in ("y", "yes"):
        if missing_required:
            print(f"\n   {_yellow('Run manually:')} pip install {' '.join(missing_required)}")
        return

    to_install = missing_required if answer == "y" else all_missing
    if missing_recommended and answer in ("y", "yes"):
        to_install = all_missing

    print()
    print(f"   Installing {len(to_install)} package(s)...")
    print()

    for pkg in to_install:
        sys.stdout.write(f"   {_DOT} {pkg:30s} ")
        sys.stdout.flush()
        result = subprocess.run(
            [PYTHON, "-m", "pip", "install", pkg, "--quiet"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(_green("installed"))
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown error"
            print(_red(f"FAILED — {err[:50]}"))

    print()
    print(f"   {_green('Done.')} Re-run {_cyan('python start.py --status')} to verify.")
    print()


# ── Process Launchers ────────────────────────────────────────────────────────

def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_pid(pid: int, mode: str):
    """Write PID info for process tracking."""
    try:
        data = {"pid": pid, "mode": mode, "started": datetime.now().isoformat()}
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _clear_pid():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _pre_launch_check() -> bool:
    """Run quick health check before launching."""
    env = _check_env()
    has_key = any(env["api_keys"].values())

    if not has_key:
        print(f"   {_WARN} {_yellow('No API keys detected.')}")
        print(f"      Copy {_cyan('.env.template')} to {_cyan('.env')} and add your Gemini API key.")
        print()
        try:
            answer = input("   Continue anyway? (y/n): ").strip().lower()
            if answer not in ("y", "yes"):
                return False
        except (EOFError, KeyboardInterrupt):
            return False
    return True


def launch_voice():
    """Launch the Tkinter GUI voice assistant (main.py)."""
    print(f"   {_cyan('▶')} Starting Voice Assistant (Gemini Live Audio)...")
    print(f"   {_dim('Press Ctrl+C to stop')}")
    print()
    try:
        proc = subprocess.run([PYTHON, str(BASE_DIR / "main.py")], cwd=str(BASE_DIR))
        return proc.returncode
    except KeyboardInterrupt:
        print(f"\n   {_dim('Voice assistant stopped.')}")
        return 0


def launch_cli():
    """Launch the Rich CLI assistant (main_mk37.py)."""
    print(f"   {_cyan('▶')} Starting CLI Assistant (Multi-Backend ReAct)...")
    print(f"   {_dim('Type /quit to exit')}")
    print()
    try:
        proc = subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
        return proc.returncode
    except KeyboardInterrupt:
        print(f"\n   {_dim('CLI stopped.')}")
        return 0


def launch_both():
    """Launch voice in a subprocess, CLI in the main process."""
    print(f"   {_cyan('▶')} Starting BOTH modes in parallel...")
    print()

    _ensure_log_dir()
    voice_log = LOG_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Launch voice as a detached process with logging
    popen_kwargs = {
        "cwd":    str(BASE_DIR),
        "stdout": open(voice_log, "w", encoding="utf-8"),
        "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    voice_proc = subprocess.Popen(
        [PYTHON, str(BASE_DIR / "main.py")],
        **popen_kwargs,
    )

    print(f"   {_OK} Voice GUI started  (PID: {_green(str(voice_proc.pid))})")
    print(f"   {_dim(f'   Voice log: {voice_log}')}")
    _write_pid(voice_proc.pid, "voice+cli")
    print(f"   {_cyan('▶')} CLI launching in foreground...\n")

    try:
        subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print(f"\n   {_dim('CLI interrupted.')}")
    finally:
        # When CLI exits, cleanly terminate voice
        print(f"\n   Shutting down voice GUI (PID: {voice_proc.pid})...", end=" ")
        try:
            voice_proc.terminate()
            voice_proc.wait(timeout=5)
            print(_green("done"))
        except subprocess.TimeoutExpired:
            voice_proc.kill()
            print(_yellow("force-killed"))
        except Exception:
            print(_dim("already stopped"))
        _clear_pid()

        # Close log file handle
        try:
            voice_proc.stdout.close()
        except Exception:
            pass


def launch_silent():
    """Silent auto-start mode — used by Windows Startup."""
    _ensure_log_dir()
    voice_log = LOG_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    try:
        popen_kwargs = {
            "cwd":    str(BASE_DIR),
            "stdout": open(voice_log, "w", encoding="utf-8"),
            "stderr": subprocess.STDOUT,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            [PYTHON, str(BASE_DIR / "main.py")],
            **popen_kwargs,
        )
        _write_pid(proc.pid, "silent")
        # Don't print in silent mode — this runs at Windows login
    except Exception:
        pass  # silent = no output on failure


def show_version():
    """Print version info."""
    print(f"  JARVIS {CODENAME} v{VERSION} (build {BUILD})")
    print(f"  Python {sys.version.split()[0]} on {platform.system()} {platform.release()}")
    print()


# ── Interactive Menu ─────────────────────────────────────────────────────────

def _interactive_menu() -> str:
    """Show interactive mode selection menu."""
    print(_bold("  Select launch mode:\n"))
    print(f"    {_cyan('[1]')}  {_bold('VOICE')}    — Gemini Live Audio GUI       {_dim('(main.py)')}")
    print(f"    {_cyan('[2]')}  {_bold('CLI')}      — Multi-Backend ReAct Terminal {_dim('(main_mk37.py)')}")
    print(f"    {_cyan('[3]')}  {_bold('BOTH')}     — Voice GUI + CLI in parallel")
    print(f"    {_cyan('[4]')}  {_bold('STATUS')}   — System diagnostics")
    print(f"    {_cyan('[5]')}  {_bold('DOCTOR')}   — Check & fix dependencies")
    print()

    try:
        choice = input(f"  {_cyan('❯')} Enter choice (1-5): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(f"\n   {_dim('Cancelled.')}")
        sys.exit(0)

    mode_map = {
        "1": "voice", "2": "cli", "3": "both",
        "4": "status", "5": "doctor",
    }
    return mode_map.get(choice, choice)


# ── Main Entry ───────────────────────────────────────────────────────────────

def main():
    # Graceful Ctrl+C handling
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    # Resolve mode from CLI args or interactive menu
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower().strip().lstrip("-")
    else:
        _banner()
        _check_env()  # load dotenv
        mode = _interactive_menu()

    # ── Dispatch ─────────────────────────────────────────────────────────
    if mode in ("voice", "v", "gui", "1"):
        _banner() if len(sys.argv) > 1 else None
        if _pre_launch_check():
            launch_voice()

    elif mode in ("cli", "c", "terminal", "2"):
        _banner() if len(sys.argv) > 1 else None
        if _pre_launch_check():
            launch_cli()

    elif mode in ("both", "b", "all", "3"):
        _banner() if len(sys.argv) > 1 else None
        if _pre_launch_check():
            launch_both()

    elif mode in ("silent",):
        launch_silent()

    elif mode in ("status", "s", "health"):
        show_status()

    elif mode in ("doctor", "fix", "install"):
        doctor()

    elif mode in ("version", "v", "ver"):
        show_version()

    else:
        print(f"   {_FAIL} Unknown mode: '{mode}'")
        print(f"      Use: voice, cli, both, --silent, --status, --doctor, --version")
        sys.exit(1)


if __name__ == "__main__":
    main()
