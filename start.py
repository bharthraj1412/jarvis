# start.py — JARVIS MK37 Unified Launcher
from __future__ import annotations
"""
Easy-start launcher for JARVIS MK37.
Launches voice assistant, CLI, or both simultaneously.

Usage:
    python start.py          → Interactive mode selector
    python start.py voice    → Voice assistant only (Gemini Live Audio GUI)
    python start.py cli      → CLI only (Rich terminal + multi-backend ReAct)
    python start.py both     → Both voice GUI + CLI in parallel
    python start.py --silent → Auto-start voice (used by Windows Startup)
    python start.py --status → Show system status
"""

import os
import sys
import signal
import subprocess
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def _banner():
    print()
    print("=" * 58)
    print("       J.A.R.V.I.S  —  MARK XXXVII  LAUNCHER")
    print("=" * 58)
    print()


def _check_env():
    """Quick check that at least one API key is configured."""
    env_file = BASE_DIR / ".env"
    config_file = BASE_DIR / "config" / "api_keys.json"
    if not env_file.exists() and not config_file.exists():
        print("[!] No .env or config/api_keys.json found.")
        print("    Copy .env.template to .env and add at least one API key.")
        print()


def launch_voice():
    """Launch the Tkinter GUI voice assistant (main.py)."""
    print("[LAUNCHER] Starting Voice Assistant (Gemini Live Audio)...")
    try:
        subprocess.run([PYTHON, str(BASE_DIR / "main.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Voice assistant stopped.")


def launch_cli():
    """Launch the Rich CLI assistant (main_mk37.py)."""
    print("[LAUNCHER] Starting CLI Assistant (Multi-Backend ReAct)...")
    try:
        subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print("\n[LAUNCHER] CLI stopped.")


def launch_both():
    """Launch voice in a subprocess, CLI in the main process."""
    print("[LAUNCHER] Starting BOTH modes...")
    print("  -> Voice GUI launching in background...")

    # Launch voice as a detached process so it doesn't block
    popen_kwargs = {
        "cwd": str(BASE_DIR),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    voice_proc = subprocess.Popen(
        [PYTHON, str(BASE_DIR / "main.py")],
        **popen_kwargs,
    )

    print(f"  -> Voice GUI started (PID: {voice_proc.pid})")
    print("  -> CLI launching in foreground...")
    print()

    try:
        subprocess.run([PYTHON, str(BASE_DIR / "main_mk37.py")], cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print("\n[LAUNCHER] CLI interrupted.")
    finally:
        # When CLI exits, cleanly terminate voice
        try:
            voice_proc.terminate()
            voice_proc.wait(timeout=5)
            print("[LAUNCHER] Voice GUI terminated.")
        except subprocess.TimeoutExpired:
            voice_proc.kill()
            print("[LAUNCHER] Voice GUI force-killed.")
        except Exception:
            pass


def launch_silent():
    """Silent auto-start mode — used by Windows Startup."""
    print("[LAUNCHER] Silent mode — starting voice assistant...")
    try:
        popen_kwargs = {
            "cwd": str(BASE_DIR),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            [PYTHON, str(BASE_DIR / "main.py")],
            **popen_kwargs,
        )
        print("[LAUNCHER] Voice assistant launched in background.")
    except Exception as e:
        print(f"[LAUNCHER] Failed to start: {e}")


def show_status():
    """Show system status information."""
    print("=" * 50)
    print("  JARVIS MK37 — System Status")
    print("=" * 50)
    print(f"  Python:    {sys.version.split()[0]}")
    print(f"  Base Dir:  {BASE_DIR}")

    env_file = BASE_DIR / ".env"
    print(f"  .env:      {'Found' if env_file.exists() else 'MISSING'}")

    # Check which backends have API keys
    try:
        import dotenv
        if env_file.exists():
            dotenv.load_dotenv(env_file)
    except ImportError:
        pass  # dotenv not installed; env vars must be set manually
    backends = {
        "ANTHROPIC_API_KEY": "Claude",
        "OPENAI_API_KEY": "GPT",
        "GEMINI_API_KEY": "Gemini",
        "MISTRAL_API_KEY": "Mistral",
    }
    for key, name in backends.items():
        status = "✓" if os.environ.get(key) else "✗"
        print(f"  {name:10s}: {status}")

    # Count skills
    try:
        sys.path.insert(0, str(BASE_DIR))
        from skills import load_skills
        print(f"  Skills:    {len(load_skills())}")
    except Exception:
        print("  Skills:    N/A")

    print("=" * 50)


def main():
    # Graceful Ctrl+C handling
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    _banner()
    _check_env()

    # Check for command-line argument
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower().strip()
    else:
        print("  Select launch mode:")
        print()
        print("    [1]  VOICE   — Gemini Live Audio GUI (main.py)")
        print("    [2]  CLI     — Multi-Backend ReAct CLI (main_mk37.py)")
        print("    [3]  BOTH    — Voice GUI + CLI in parallel")
        print()
        try:
            choice = input("  Enter choice (1/2/3) or mode name: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[LAUNCHER] Cancelled.")
            return

        mode_map = {"1": "voice", "2": "cli", "3": "both"}
        mode = mode_map.get(choice, choice)

    if mode in ("voice", "v", "gui"):
        launch_voice()
    elif mode in ("cli", "c", "terminal"):
        launch_cli()
    elif mode in ("both", "b", "all"):
        launch_both()
    elif mode in ("--silent", "silent"):
        launch_silent()
    elif mode in ("--status", "status"):
        show_status()
    else:
        print(f"[LAUNCHER] Unknown mode: '{mode}'")
        print("           Use: voice, cli, both, --silent, --status")
        sys.exit(1)


if __name__ == "__main__":
    main()
