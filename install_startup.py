# install_startup.py
"""
Installs JARVIS MK37 into the Windows auto-startup folder.
Creates a VBScript launcher that runs silently (no CMD flash) on login.

Usage:
    python install_startup.py            # Install auto-startup
    python install_startup.py --remove   # Remove auto-startup
    python install_startup.py --status   # Check if installed
"""

import os
import sys
from pathlib import Path


def get_startup_folder() -> Path:
    """Get the Windows Startup folder path. Returns empty path on non-Windows."""
    if sys.platform != "win32":
        return Path("/dev/null")
    startup = Path(os.environ.get(
        "APPDATA", Path.home() / "AppData" / "Roaming"
    )) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup


def get_project_dir() -> Path:
    return Path(__file__).resolve().parent


def install():
    """Install JARVIS MK37 to Windows startup using a silent VBScript launcher."""
    if sys.platform != "win32":
        print("[ERROR] Auto-startup installer is only supported on Windows.")
        sys.exit(1)

    startup_dir = get_startup_folder()
    project_dir = get_project_dir()
    bat_source = project_dir / "startup.bat"

    if not bat_source.exists():
        print(f"[ERROR] startup.bat not found at {bat_source}")
        sys.exit(1)

    if not startup_dir.exists():
        print(f"[ERROR] Startup folder not found at {startup_dir}")
        sys.exit(1)

    # Create VBScript for silent launch (no CMD flash on login)
    vbs_file = startup_dir / "JARVIS_MK37.vbs"
    vbs_content = (
        f'Set WShell = CreateObject("WScript.Shell")\n'
        f'WShell.CurrentDirectory = "{project_dir}"\n'
        f'WShell.Run """{bat_source}"" --silent", 0, False\n'
    )

    # Also create a fallback .bat in case VBS is blocked by policy
    bat_file = startup_dir / "JARVIS_MK37.bat"
    bat_content = (
        f'@echo off\r\n'
        f'start "" /D "{project_dir}" /MIN "{bat_source}" --silent\r\n'
    )

    try:
        vbs_file.write_text(vbs_content, encoding="utf-8")
        bat_file.write_text(bat_content, encoding="utf-8")

        print("=" * 55)
        print("  JARVIS MK37 — Auto-Startup Installed")
        print("=" * 55)
        print(f"  VBS Launcher: {vbs_file}")
        print(f"  BAT Fallback: {bat_file}")
        print(f"  Project Dir:  {project_dir}")
        print()
        print("  JARVIS will now start automatically when you log in.")
        print("  It launches the Voice Assistant in silent mode.")
        print()
        print("  To remove: python install_startup.py --remove")
        print("  To check:  python install_startup.py --status")
        print("=" * 55)
    except PermissionError:
        print(f"[ERROR] Permission denied writing to {startup_dir}")
        print(f"        Try running: python install_startup.py")
        print(f"        Or manually copy startup.bat to:")
        print(f"        {startup_dir}")
        sys.exit(1)


def remove():
    """Remove JARVIS MK37 from Windows startup."""
    startup_dir = get_startup_folder()
    removed = []

    for name in ("JARVIS_MK37.vbs", "JARVIS_MK37.bat"):
        f = startup_dir / name
        if f.exists():
            f.unlink()
            removed.append(str(f))

    if removed:
        print("[OK] JARVIS MK37 auto-startup removed.")
        for r in removed:
            print(f"     Deleted: {r}")
    else:
        print("[INFO] No auto-startup entry found.")


def status():
    """Check if JARVIS MK37 is installed in auto-startup."""
    startup_dir = get_startup_folder()
    vbs = startup_dir / "JARVIS_MK37.vbs"
    bat = startup_dir / "JARVIS_MK37.bat"

    print("=" * 50)
    print("  JARVIS MK37 — Auto-Startup Status")
    print("=" * 50)
    print(f"  Startup folder: {startup_dir}")
    print(f"  VBS launcher:   {'INSTALLED' if vbs.exists() else 'not found'}")
    print(f"  BAT fallback:   {'INSTALLED' if bat.exists() else 'not found'}")
    print(f"  Project dir:    {get_project_dir()}")
    print(f"  startup.bat:    {'EXISTS' if (get_project_dir() / 'startup.bat').exists() else 'MISSING'}")
    print("=" * 50)

    if vbs.exists() or bat.exists():
        print("  Status: ACTIVE — JARVIS will start on login")
    else:
        print("  Status: NOT INSTALLED")
        print("  Run: python install_startup.py")


if __name__ == "__main__":
    if "--remove" in sys.argv or "--uninstall" in sys.argv:
        remove()
    elif "--status" in sys.argv:
        status()
    else:
        install()
