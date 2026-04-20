# start.py — JARVIS MK37 Unified Launcher (v3)
from __future__ import annotations
"""
Production-grade launcher mapping to the complete suite.
Features Rich TUI for Windows-compatible colorization.
"""

import importlib
import json
import os
import platform
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Fix terminal encoding issues on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Setup Rich formatting
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.live import Live
    from rich import print as rprint
    console = Console()
except ImportError:
    # Very basic fallback if rich isn't installed (though it should be for JARVIS)
    print("Oops! 'rich' module is missing. Please run: pip install rich")
    sys.exit(1)

# ── Constants ────────────────────────────────────────────────────────────────

VERSION = "37.1.0"
BUILD   = "2026-04-21"
CODENAME = "MARK XXXVII"

BASE_DIR = Path(__file__).resolve().parent
PYTHON   = sys.executable
LOG_DIR  = BASE_DIR / "logs"
PID_FILE = BASE_DIR / ".jarvis.pid"

# ── Banner ───────────────────────────────────────────────────────────────────

def _banner():
    console.clear()
    now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
    text = Text(justify="center")
    text.append("\nJ.A.R.V.I.S  —  MARK XXXVII\n", style="bold cyan")
    text.append("Just A Rather Very Intelligent System\n\n", style="dim")
    text.append(f"Version: {VERSION} | Build: {BUILD}\n", style="bold green")
    text.append(f"Python: {sys.version.split()[0]} | Platform: {platform.system()}\n", style="green")
    text.append(now, style="dim")
    
    panel = Panel(text, border_style="cyan", expand=False, padding=(1, 4))
    console.print(panel)
    console.print()

# ── Status and Check Helpers ──────────────────────────────────────────────────

def _check_env() -> dict:
    """Check environment configuration and return status dict."""
    status = {"env_file": False, "config_file": False, "api_keys": {}}
    env_file    = BASE_DIR / ".env"
    config_file = BASE_DIR / "config" / "api_keys.json"

    status["env_file"]    = env_file.exists()
    status["config_file"] = config_file.exists()

    try:
        import dotenv
        if env_file.exists():
            dotenv.load_dotenv(env_file)
    except ImportError:
        pass

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
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "OK")
        return True, str(ver)
    except ImportError as e:
        return False, str(e)

# ── Health Diagnostic Command ─────────────────────────────────────────────────

def show_status():
    _banner()
    env = _check_env()

    # Environment
    table_env = Table(title="Environment", title_style="bold magenta", show_header=False, box=None)
    table_env.add_column("Property", style="bold")
    table_env.add_column("Value")
    table_env.add_row("Base Dir", str(BASE_DIR))
    table_env.add_row("Python Exec", sys.executable)
    venv = hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    table_env.add_row("Virtual Env", "[green]Active[/]" if venv else "[yellow]Not detected[/]")
    table_env.add_row("Env File", "[green]✓ Found[/]" if env["env_file"] else "[red]✗ MISSING[/]")
    
    # Backends
    table_be = Table(title="Backends", title_style="bold magenta", show_header=False, box=None)
    has_any = False
    for label, ok in env["api_keys"].items():
        if "alt" in label and not ok: continue
        table_be.add_row(f"[green]✓ {label}[/]" if ok else f"[dim]○ {label}[/]", "[green]Configured[/]" if ok else "[dim]Not Configured[/]")
        if ok: has_any = True

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import urllib.request
        req = urllib.request.Request(f"{ollama_host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1) as resp:
            table_be.add_row(f"[green]✓ Ollama[/]", f"[green]Running[/] at {ollama_host}")
            has_any = True
    except Exception:
        table_be.add_row(f"[dim]○ Ollama[/]", f"[dim]Not Running ({ollama_host})[/]")

    # Modules
    table_mod = Table(title="Core Modules", title_style="bold magenta", show_header=False, box=None)
    core_modules = [
        ("google.genai", "Google GenAI SDK"), ("sounddevice", "Audio I/O"), 
        ("requests", "HTTP Client"), ("httpx", "Async HTTP"),
        ("PIL", "Image Processing"), ("numpy", "Numerics"), ("psutil", "System Monitor")
    ]
    core_ok = 0
    for mod_name, label in core_modules:
        ok, ver = _check_module(mod_name)
        if ok:
            table_mod.add_row(f"[green]✓ {label}[/]", f"[dim]{ver}[/]")
            core_ok += 1
        else:
            table_mod.add_row(f"[red]✗ {label}[/]", "[red]MISSING[/]")
            
    table_sys = Table(title="System & Memory", title_style="bold magenta", show_header=False, box=None)
    try:
        sys.path.insert(0, str(BASE_DIR))
        from skills import load_skills
        table_sys.add_row("[green]✓ Skills Loaded[/]", str(len(load_skills())))
        
        from multi_agent.subagent import load_agent_definitions
        table_sys.add_row("[green]✓ Agent Types[/]", str(len(load_agent_definitions())))
        
        from tools.registry import TOOL_SCHEMAS
        table_sys.add_row("[green]✓ Tools Registered[/]", str(len(TOOL_SCHEMAS)))
    except Exception:
        pass
        
    try:
        from memory.vector_store import VectorMemory
        vm = VectorMemory()
        table_sys.add_row("[green]✓ Vector Memory[/]" if vm.available else "[yellow]⚠ Vector Memory[/]", "[green]Operational[/]" if vm.available else "[yellow]Degraded[/]")
    except Exception:
        pass

    console.print(table_env)
    console.print()
    if not has_any:
        console.print("[bold yellow]⚠ No backends configured. AI chat will not work. Add keys to .env[/]")
    console.print(table_be)
    console.print()
    console.print(table_mod)
    console.print()
    console.print(table_sys)
    console.print()

# ── Dependencies Doctor ────────────────────────────────────────────────────────

def doctor():
    _banner()
    console.print("[bold magenta]JARVIS Doctor — Dependency Fix[/]\n")

    required = {"google-genai": "google.genai", "sounddevice": "sounddevice", "requests": "requests", 
                "httpx": "httpx", "Pillow": "PIL", "numpy": "numpy", "psutil": "psutil"}
    
    missing = []
    
    table = Table(title="Required Dependencies", box=None)
    table.add_column("Package", style="bold")
    table.add_column("Status")
    
    for pip_name, import_name in required.items():
        ok, ver = _check_module(import_name)
        if ok:
            table.add_row(pip_name, f"[green]✓ Installed[/] [dim]({ver})[/]")
        else:
            table.add_row(pip_name, "[red]✗ MISSING[/]")
            missing.append(pip_name)
            
    console.print(table)
    console.print()
    
    if not missing:
        console.print("[bold green]System is healthy. All dependencies met.[/]")
        return
        
    console.print(f"[bold red]{len(missing)} required packages missing.[/]")
    if Prompt.ask("Install missing packages now?", choices=["y", "n"], default="y") == "y":
        console.print("\nInstalling...")
        for pkg in missing:
            console.print(f"  [dim]Installing[/] {pkg}...")
            result = subprocess.run([PYTHON, "-m", "pip", "install", pkg, "--quiet"], capture_output=True)
            if result.returncode == 0:
                console.print(f"  [green]✓ {pkg} installed[/]")
            else:
                console.print(f"  [red]✗ Failed to install {pkg}[/]")
        console.print("\n[bold green]Scan complete.[/]")

# ── Process Execution ─────────────────────────────────────────────────────────

def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def _write_pid(pid: int, mode: str):
    try:
        data = {"pid": pid, "mode": mode, "started": datetime.now().isoformat()}
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def _clear_pid():
    try: PID_FILE.unlink(missing_ok=True)
    except Exception: pass

def _pre_launch_check() -> bool:
    env = _check_env()
    if not any(env["api_keys"].values()):
        console.print("\n[bold yellow]⚠ No API keys detected![/]")
        console.print("  Duplicate [cyan].env.template[/] as [cyan].env[/] and insert your Gemini API Key.")
        if Prompt.ask("Continue anyway?", choices=["y", "n"], default="n") != "y":
            return False
    return True

def launch_voice():
    console.print("\n[bold cyan]▶ Starting Voice Assistant (Gemini Live GUI)[/]")
    console.print("[dim]Note: The GUI will open in a new window. Press Ctrl+C to stop.[/]\n")
    try: subprocess.run([PYTHON, str(BASE_DIR / "main.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt: console.print("\n[dim]Voice assistant stopped.[/]")

def launch_cli():
    console.print("\n[bold cyan]▶ Starting CLI Orchestrator[/]")
    console.print("[dim]Type /quit to exit.[/]\n")
    try: subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt: console.print("\n[dim]CLI stopped.[/]")

def launch_screen_share():
    console.print("\n[bold cyan]▶ Starting Screen Share Server[/]")
    viewer_path = BASE_DIR / "screen_server" / "viewer.html"
    console.print(f"  [green]Server Running on[/] ws://localhost:8765")
    console.print(f"  [green]Viewer Interface[/]  Access [cyan]file:///{viewer_path}[/]")
    console.print("[dim]Press Ctrl+C to shut down.[/]\n")
    try: subprocess.run([PYTHON, str(BASE_DIR / "screen_server" / "ws_server.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt: console.print("\n[dim]Screen Share shutdown.[/]")

def launch_both():
    console.print("\n[bold cyan]▶ Starting Modes in Parallel[/]\n")
    _ensure_log_dir()
    voice_log = LOG_DIR / f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    kwargs = {"cwd": str(BASE_DIR), "stdout": open(voice_log, "w", encoding="utf-8"), "stderr": subprocess.STDOUT}
    if sys.platform == "win32": kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    
    vproc = subprocess.Popen([PYTHON, str(BASE_DIR / "main.py")], **kwargs)
    console.print(f"  [green]✓ Voice GUI Started[/] (PID: {vproc.pid})")
    console.print(f"    [dim]Logs: {voice_log}[/]")
    _write_pid(vproc.pid, "voice+cli")
    
    console.print("\n  [cyan]Launching CLI...[/]\n")
    try: subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt: console.print("\n[dim]CLI closed.[/]")
    finally:
        console.print(f"  [dim]Shutting down Voice GUI (PID: {vproc.pid})...[/]", end=" ")
        try:
            vproc.terminate()
            vproc.wait(timeout=5)
            console.print("[green]Done.[/]")
        except subprocess.TimeoutExpired:
            vproc.kill()
            console.print("[yellow]Force Killed.[/]")
        except Exception:
            console.print("[dim]Ignored.[/]")
        _clear_pid()

def launch_silent():
    _ensure_log_dir()
    voice_log = LOG_DIR / f"voice_silent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    try:
        kwargs = {"cwd": str(BASE_DIR), "stdout": open(voice_log, "w", encoding="utf-8"), "stderr": subprocess.STDOUT}
        if sys.platform == "win32": kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen([PYTHON, str(BASE_DIR / "main.py")], **kwargs)
        _write_pid(proc.pid, "silent")
    except Exception: pass

# ── Main Entry ───────────────────────────────────────────────────────────────

def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower().strip().lstrip("-")
    else:
        _banner()
        _check_env()
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Num", style="bold cyan")
        table.add_column("Action", style="bold")
        table.add_column("Desc", style="dim")
        
        table.add_row("1", "VOICE", "Gemini Live Audio Graphical Interface")
        table.add_row("2", "CLI", "ReAct Terminal Interface (Multi Backend)")
        table.add_row("3", "BOTH", "Voice + CLI running simultaneously")
        table.add_row("4", "SCREEN SHARE", "Launch WebSocket Monitor Tool")
        table.add_row("5", "STATUS", "Check AI configuration and module health")
        table.add_row("6", "DOCTOR", "Auto-install missing dependencies")
        
        console.print(Panel(table, title="[bold]Select Module Sequence[/]", expand=False))
        console.print()
        
        choice = Prompt.ask("  [cyan]❯[/] Ready", choices=["1", "2", "3", "4", "5", "6"], default="1")
        mode = {"1": "voice", "2": "cli", "3": "both", "4": "screenshare", "5": "status", "6": "doctor"}[choice]

    if mode in ("voice", "v", "gui"): launch_voice() if _pre_launch_check() else None
    elif mode in ("cli", "c", "terminal"): launch_cli() if _pre_launch_check() else None
    elif mode in ("both", "b", "all"): launch_both() if _pre_launch_check() else None
    elif mode in ("screenshare", "s", "monitor"): launch_screen_share()
    elif mode in ("status", "health"): show_status()
    elif mode in ("doctor", "fix"): doctor()
    elif mode in ("silent",): launch_silent()
    else:
        console.print(f"[red]✗ Unknown launch argument provided.[/]")
        sys.exit(1)

if __name__ == "__main__":
    main()
