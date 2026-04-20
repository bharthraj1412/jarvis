# skills/installer.py
"""
JARVIS MK37 Skill Installer — Fetch, convert, and install external skills.

Supports:
  - Git-based skill packs (claude-skills, openclaw-master-skills, etc.)
  - Individual SKILL.md files
  - Auto-conversion of OpenClaw/Claude SKILL.md format → JARVIS .md format
  - Skill management: install, list, remove, update

Usage:
    from skills.installer import install_skill_pack, list_installed, remove_skill
    
CLI:
    python -m skills.installer install claude-skills
    python -m skills.installer install openclaw-master
    python -m skills.installer list
    python -m skills.installer remove <skill_name>
    python -m skills.installer update
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────
SKILLS_USER_DIR = Path.home() / ".jarvis" / "skills"
SKILLS_PACKS_DIR = Path.home() / ".jarvis" / "skill_packs"
SKILLS_REGISTRY = Path.home() / ".jarvis" / "installed_packs.json"

# ── Skill Pack Definitions ────────────────────────────────────────────────
KNOWN_PACKS = {
    "claude-skills": {
        "repo": "https://github.com/alirezarezvani/claude-skills.git",
        "description": "305+ Python tools and 232+ skills for AI agents",
        "skill_dirs": ["commands", "agents"],
        "skill_file": "SKILL.md",
    },
    "openclaw-master": {
        "repo": "https://github.com/LeoYeAI/openclaw-master-skills.git",
        "description": "560+ curated OpenClaw skills updated weekly",
        "skill_dirs": ["skills"],
        "skill_file": "SKILL.md",
    },
}


def _ensure_dirs():
    """Create skill directories if they don't exist."""
    SKILLS_USER_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_PACKS_DIR.mkdir(parents=True, exist_ok=True)


def _load_registry() -> dict:
    """Load installed packs registry."""
    if SKILLS_REGISTRY.exists():
        try:
            return json.loads(SKILLS_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_registry(data: dict):
    """Save installed packs registry."""
    SKILLS_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    SKILLS_REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _convert_skill_md(source_path: Path, skill_name: str) -> str | None:
    """Convert an OpenClaw/Claude SKILL.md into JARVIS MK37 .md format."""
    try:
        text = source_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Parse existing frontmatter if present
    name = skill_name
    description = ""
    triggers = [f"/{skill_name}"]
    tools = []
    prompt_body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            prompt_body = parts[2].strip()

            for line in frontmatter.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()

                if key == "name":
                    name = val.strip('"').strip("'")
                    triggers = [f"/{name}"]
                elif key == "description":
                    description = val.strip('"').strip("'")
                elif key in ("tools", "allowed-tools"):
                    tools_str = val.strip("[]")
                    tools = [t.strip().strip('"').strip("'")
                             for t in tools_str.split(",") if t.strip()]

    # Map external tool names to JARVIS tool names
    tool_map = {
        "Bash": "run_code", "bash": "run_code", "shell": "run_code",
        "Read": "file_read", "read": "file_read",
        "Write": "file_write", "write": "file_write",
        "Edit": "file_write", "edit": "file_write",
        "WebSearch": "web_search", "web_search": "web_search",
        "WebFetch": "fetch_page", "web_fetch": "fetch_page",
        "Browser": "fetch_page", "browser": "fetch_page",
        "Screenshot": "take_screenshot",
    }
    mapped_tools = []
    for t in tools:
        mapped = tool_map.get(t, t.lower().replace(" ", "_"))
        if mapped not in mapped_tools:
            mapped_tools.append(mapped)

    # If no tools detected, default to common set
    if not mapped_tools:
        mapped_tools = ["run_code", "file_read", "file_write", "web_search"]

    # Build JARVIS .md file
    jarvis_md = f"""---
name: {name}
description: {description or name.replace('-', ' ').replace('_', ' ').title()}
triggers: [{', '.join(triggers)}]
tools: [{', '.join(mapped_tools)}]
user-invocable: true
context: inline
---
{prompt_body}
"""
    return jarvis_md


def install_skill_pack(pack_name: str) -> str:
    """Install a skill pack by name or git URL."""
    _ensure_dirs()
    registry = _load_registry()

    # Check if it's a known pack
    if pack_name in KNOWN_PACKS:
        pack_info = KNOWN_PACKS[pack_name]
        repo_url = pack_info["repo"]
    elif pack_name.startswith(("http://", "https://", "git@")):
        repo_url = pack_name
        pack_name = repo_url.split("/")[-1].replace(".git", "")
        pack_info = {
            "description": f"Custom pack from {repo_url}",
            "skill_dirs": ["skills", "commands", "."],
            "skill_file": "SKILL.md",
        }
    else:
        return (
            f"Unknown pack: '{pack_name}'. Known packs: {', '.join(KNOWN_PACKS.keys())}\n"
            f"Or provide a git URL: python -m skills.installer install <git_url>"
        )

    # Clone or pull
    pack_dir = SKILLS_PACKS_DIR / pack_name
    if pack_dir.exists():
        print(f"[Installer] Updating {pack_name}...")
        try:
            subprocess.run(
                ["git", "pull"], cwd=str(pack_dir),
                capture_output=True, timeout=60
            )
        except Exception as e:
            return f"Git pull failed: {e}"
    else:
        print(f"[Installer] Cloning {pack_name}...")
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", repo_url, str(pack_dir)],
                capture_output=True, timeout=120
            )
        except Exception as e:
            return f"Git clone failed: {e}"

    if not pack_dir.exists():
        return f"Failed to download {pack_name}."

    # Find and convert SKILL.md files
    converted = 0
    skipped = 0
    skill_file_name = pack_info.get("skill_file", "SKILL.md")

    for skill_dir_name in pack_info.get("skill_dirs", ["skills"]):
        search_dir = pack_dir / skill_dir_name
        if not search_dir.exists():
            search_dir = pack_dir  # Fallback: search entire pack

        for skill_file in search_dir.rglob(skill_file_name):
            # Get skill name from parent directory
            skill_name = skill_file.parent.name
            if skill_name in (".", "", pack_name):
                skill_name = skill_file.stem.lower()

            # Clean the name
            skill_name = re.sub(r"[^a-z0-9_-]", "-", skill_name.lower())
            if not skill_name or skill_name == "skill":
                continue

            # Convert and write
            jarvis_md = _convert_skill_md(skill_file, skill_name)
            if jarvis_md:
                out_file = SKILLS_USER_DIR / f"{skill_name}.md"
                if out_file.exists():
                    skipped += 1
                    continue
                out_file.write_text(jarvis_md, encoding="utf-8")
                converted += 1

    # Update registry
    registry[pack_name] = {
        "repo": repo_url,
        "description": pack_info.get("description", ""),
        "installed": datetime.now().isoformat(),
        "skills_installed": converted,
        "skills_skipped": skipped,
    }
    _save_registry(registry)

    return (
        f"{'=' * 50}\n"
        f"  Skill Pack: {pack_name}\n"
        f"  Installed: {converted} skills\n"
        f"  Skipped: {skipped} (already exist)\n"
        f"  Location: {SKILLS_USER_DIR}\n"
        f"{'=' * 50}"
    )


def list_installed() -> str:
    """List all installed skill packs and individual skills."""
    _ensure_dirs()
    registry = _load_registry()

    lines = ["=" * 55]
    lines.append("  JARVIS MK37 — Installed Skills")
    lines.append("=" * 55)

    # Installed packs
    if registry:
        lines.append("\n  Skill Packs:")
        for name, info in registry.items():
            lines.append(f"    [{name}] {info.get('description', '')}")
            lines.append(f"      Skills: {info.get('skills_installed', '?')}")
            lines.append(f"      Date:   {info.get('installed', '?')[:10]}")
    else:
        lines.append("\n  No skill packs installed.")

    # Individual skill files
    if SKILLS_USER_DIR.exists():
        skill_files = list(SKILLS_USER_DIR.glob("*.md"))
        lines.append(f"\n  User Skills ({len(skill_files)}):")
        for f in sorted(skill_files)[:30]:
            lines.append(f"    - {f.stem}")
        if len(skill_files) > 30:
            lines.append(f"    ... and {len(skill_files) - 30} more")
    else:
        lines.append("\n  No user skills found.")

    lines.append("=" * 55)
    return "\n".join(lines)


def remove_skill(name: str) -> str:
    """Remove a skill by name."""
    _ensure_dirs()
    skill_file = SKILLS_USER_DIR / f"{name}.md"
    if skill_file.exists():
        skill_file.unlink()
        return f"Removed skill: {name}"
    return f"Skill not found: {name}"


def remove_pack(pack_name: str) -> str:
    """Remove an entire skill pack."""
    _ensure_dirs()
    registry = _load_registry()
    pack_dir = SKILLS_PACKS_DIR / pack_name

    if pack_dir.exists():
        shutil.rmtree(pack_dir)

    if pack_name in registry:
        del registry[pack_name]
        _save_registry(registry)

    return f"Removed skill pack: {pack_name}"


def update_all() -> str:
    """Update all installed skill packs."""
    registry = _load_registry()
    if not registry:
        return "No skill packs installed to update."

    results = []
    for pack_name in registry:
        result = install_skill_pack(pack_name)
        results.append(f"[{pack_name}] {result}")

    return "\n\n".join(results)


# ── CLI Interface ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("JARVIS MK37 Skill Installer")
        print()
        print("Commands:")
        print("  install <pack_name|git_url>  Install a skill pack")
        print("  list                         List installed skills")
        print("  remove <skill_name>          Remove a skill")
        print("  remove-pack <pack_name>      Remove entire pack")
        print("  update                       Update all packs")
        print()
        print(f"Known packs: {', '.join(KNOWN_PACKS.keys())}")
        sys.exit(0)

    cmd = args[0]

    if cmd == "install" and len(args) > 1:
        print(install_skill_pack(args[1]))
    elif cmd == "list":
        print(list_installed())
    elif cmd == "remove" and len(args) > 1:
        print(remove_skill(args[1]))
    elif cmd == "remove-pack" and len(args) > 1:
        print(remove_pack(args[1]))
    elif cmd == "update":
        print(update_all())
    else:
        print(f"Unknown command: {cmd}")
        print("Use: install, list, remove, remove-pack, update")
