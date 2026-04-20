# main_mk37.py — JARVIS MK37 CLI Entry Point
"""
JARVIS MK37 — Multi-backend AI assistant with Claude Cowork architecture.
Features: Skills, Sub-agents, PC Control, Persistent Memory, Auto-Allow.
Run this to start the interactive CLI session.
"""

import os
import sys
import signal
import traceback
from pathlib import Path

# ── Force UTF-8 encoding on Windows ──────────────────────────────────────────
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Try the template as fallback
    _template = Path(__file__).parent / ".env.template"
    if _template.exists():
        load_dotenv(_template)

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table

from router import AgentRouter, AgentProfile

console = Console(force_terminal=True)

BANNER = r"""
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
                  M K 3 7
        ╔═══════════════════════════════╗
        ║   Claude Cowork Architecture  ║
        ║   Skills │ Agents │ AutoAllow ║
        ╚═══════════════════════════════╝
"""

HELP_TEXT = """
[bold cyan]Commands:[/]
  /mode <name>       Switch persona mode
  /tools             List available tools
  /skills            List available skills
  /skill <name>      Execute a skill by name
  /agents            List available agent types
  /models            Show active model configuration
  /install-skills    Install external skill packs (claude-skills, openclaw)
  /installed-skills  List installed skill packs
  /remove-skill      Remove a skill by name
  /memory <cmd>      Memory operations (search/list)
  /clear             Clear conversation history
  /help              Show this help
  /status            Show active mode and backend info
  /quit              Exit JARVIS (consolidates memories)

[bold cyan]Modes:[/]
  recon    — OSINT & network mapping
  exploit  — Authorized vuln analysis (scope-gated)
  report   — Professional report writer
  planner  — Goal decomposition
  coder    — DevSecOps engineer
  analyst  — Threat intel synthesis
  general  — Default adaptive mode

[bold cyan]Skills (45 built-in):[/]
  [bold white]Core:[/] commit, review, edit, pc_control, research
  [bold white]Editor:[/] editor_open, editor_goto, editor_insert, editor_replace, editor_terminal
  [bold white]Extra:[/] github_scan, screenshot_fix, docker_deploy, scaffold, monitor
  [bold white]Code:[/] tdd, code_review, refactor, api_design, git_flow, dep_audit
  [bold white]Security:[/] security_scan, osint_recon, log_analysis, ssl_check, hash_lookup
  [bold white]Data:[/] csv_analysis, json_transform, regex_builder, db_query, chart_gen
  [bold white]DevOps:[/] docker_compose, ci_cd, nginx_config, env_setup, terraform_gen
  [bold white]Docs:[/] doc_gen, changelog, meeting_notes, email_draft
  [bold white]Admin:[/] system_info, process_mgr, network_diag, disk_cleanup, cron_scheduler

[bold cyan]External Skills:[/]
  /install-skills claude-skills     — Install 300+ Claude skills
  /install-skills openclaw-master   — Install 560+ OpenClaw skills
  /install-skills <git_url>         — Install from any git repo

[bold cyan]PC Control:[/]
  JARVIS can control your mouse, keyboard, clipboard, and screen.
  Use natural language: "Click the submit button" or "Type hello world"

[bold cyan]Sub-Agents:[/]
  JARVIS can spawn specialized sub-agents: coder, reviewer, researcher, tester, editor
  "Spawn a coder agent to build a REST API"

[bold cyan]Memory:[/]
  /memory search <query> — Search persistent memories
  /memory list           — List all memories
  Memories persist across sessions automatically.
"""


def _init_backends() -> dict:
    """Initialize available backends based on environment keys."""
    backends = {}

    # Claude (Anthropic)
    try:
        from anthropic_backend import ClaudeBackend
        b = ClaudeBackend()
        backends[AgentProfile.CLAUDE] = b
        console.print(f"  [green]✓[/] Claude — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ Claude: {e}[/]")

    # GPT (OpenAI)
    try:
        from openai_backend import OpenAIBackend
        b = OpenAIBackend()
        backends[AgentProfile.GPT] = b
        console.print(f"  [green]✓[/] GPT — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ GPT: {e}[/]")

    # Gemini (Google)
    try:
        from gemini_backend import GeminiBackend
        b = GeminiBackend()
        backends[AgentProfile.GEMINI] = b
        console.print(f"  [green]✓[/] Gemini — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ Gemini: {e}[/]")

    # Ollama (Local)
    try:
        from ollama_backend import OllamaBackend
        b = OllamaBackend()
        backends[AgentProfile.OLLAMA] = b
        console.print(f"  [green]✓[/] Ollama — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ Ollama: {e}[/]")

    # NVIDIA NIM
    try:
        from nvidia_backend import NvidiaBackend
        b = NvidiaBackend()
        backends[AgentProfile.NVIDIA] = b
        console.print(f"  [green]✓[/] NVIDIA — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ NVIDIA: {e}[/]")

    # Mistral
    try:
        from mistral_backend import MistralBackend
        b = MistralBackend()
        backends[AgentProfile.MISTRAL] = b
        console.print(f"  [green]✓[/] Mistral — {b.model}")
    except Exception as e:
        console.print(f"  [dim]✗ Mistral: {e}[/]")

    return backends


def _show_status(jarvis, backends, router):
    """Display a rich status table."""
    table = Table(title="JARVIS MK37 Status", border_style="bright_blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Active Mode", jarvis.current_mode.upper())
    table.add_row("Default Backend", router.default.value)
    table.add_row("Active Backends", ", ".join(p.value for p in backends))
    table.add_row("History Length", str(len(jarvis.working_memory.history)))
    table.add_row("Vector Memory", "Active" if jarvis.vector_memory else "Disabled")
    table.add_row("Permission Mode", "AUTO-ALLOW (all tools execute immediately)")

    # Show model config
    from config.models import get_model_config
    cfg = get_model_config()
    table.add_row("Config Source", "env > models.json > defaults")
    table.add_row("Default Backend", cfg.get('default_backend', 'N/A'))

    # Count skills
    try:
        from skills import load_skills
        skill_count = len(load_skills())
        table.add_row("Skills Loaded", str(skill_count))
    except Exception:
        table.add_row("Skills Loaded", "N/A")

    # Count agent types
    try:
        from multi_agent.subagent import load_agent_definitions
        agent_count = len(load_agent_definitions())
        table.add_row("Agent Types", str(agent_count))
    except Exception:
        table.add_row("Agent Types", "N/A")

    # Count memories
    try:
        from memory.persistent_store import load_index
        mem_count = len(load_index("all"))
        table.add_row("Persistent Memories", str(mem_count))
    except Exception:
        table.add_row("Persistent Memories", "N/A")

    console.print(table)


def _show_tools():
    """Display available tools."""
    try:
        from tools.registry import TOOL_SCHEMAS
        table = Table(title="Available Tools", border_style="green")
        table.add_column("Tool", style="cyan bold")
        table.add_column("Description", style="white")
        for tool in TOOL_SCHEMAS:
            table.add_row(tool["name"], tool["description"][:80])
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error loading tools: {e}[/]")


def _show_skills():
    """Display available skills."""
    try:
        from skills import load_skills
        skills = load_skills()
        if not skills:
            console.print("[yellow]No skills available.[/]")
            return
        table = Table(title="Available Skills", border_style="magenta")
        table.add_column("Skill", style="cyan bold")
        table.add_column("Triggers", style="yellow")
        table.add_column("Description", style="white")
        table.add_column("Context", style="dim")
        for s in skills:
            triggers = ", ".join(s.triggers)
            table.add_row(s.name, triggers, s.description[:60], s.context)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error loading skills: {e}[/]")


def _show_agents():
    """Display available agent types."""
    try:
        from multi_agent.subagent import load_agent_definitions
        defs = load_agent_definitions()
        if not defs:
            console.print("[yellow]No agent types available.[/]")
            return
        table = Table(title="Available Agent Types", border_style="blue")
        table.add_column("Type", style="cyan bold")
        table.add_column("Source", style="dim")
        table.add_column("Description", style="white")
        for name, d in sorted(defs.items()):
            table.add_row(name, d.source, d.description[:70])
        console.print(table)
        console.print("[dim]Custom agents: place .md files in ~/.jarvis/agents/ or .jarvis/agents/[/]")
    except Exception as e:
        console.print(f"[red]Error loading agents: {e}[/]")


def _handle_memory_command(args: str):
    """Handle /memory subcommands."""
    parts = args.strip().split(maxsplit=1)
    subcmd = parts[0].lower() if parts else "list"
    sub_args = parts[1] if len(parts) > 1 else ""

    if subcmd == "search" and sub_args:
        try:
            from memory.memory_context import find_relevant_memories
            results = find_relevant_memories(sub_args, max_results=5)
            if not results:
                console.print(f"[yellow]No memories found for '{sub_args}'[/]")
                return
            table = Table(title=f"Memories matching '{sub_args}'", border_style="green")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Description", style="white")
            for r in results:
                table.add_row(r["name"], f"{r['type']}/{r['scope']}", r["description"][:60])
            console.print(table)
        except Exception as e:
            console.print(f"[red]Memory search error: {e}[/]")

    elif subcmd == "list":
        try:
            from memory.persistent_store import load_index
            entries = load_index("all")
            if not entries:
                console.print("[yellow]No memories stored.[/]")
                return
            table = Table(title="Persistent Memories", border_style="green")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Scope", style="dim")
            table.add_column("Description", style="white")
            for e in entries:
                table.add_row(e.name, e.type, e.scope, e.description[:50])
            console.print(table)
        except Exception as e:
            console.print(f"[red]Memory list error: {e}[/]")

    else:
        console.print("[yellow]Usage: /memory search <query>  |  /memory list[/]")


def main():
    # ── Graceful shutdown on Ctrl+C ───────────────────────────────────────
    def _signal_handler(sig, frame):
        console.print("\n[yellow]JARVIS MK37 shutting down.[/]")
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)

    # ── Banner ────────────────────────────────────────────────────────────
    try:
        console.print(Panel(Text(BANNER, style="bold cyan"), border_style="bright_blue"))
    except Exception:
        print(BANNER)

    console.print("[bold white]Initializing backends...[/]")
    backends = _init_backends()

    if not backends:
        console.print("[bold red]No backends available. Check your .env file and API keys.[/]")
        console.print("[dim]Tip: Copy .env.template to .env and fill in at least one API key.[/]")
        sys.exit(1)

    router = AgentRouter(backends)

    # Set default to first available backend if Claude isn't available
    if AgentProfile.CLAUDE not in backends:
        router.default = list(backends.keys())[0]
        console.print(f"[yellow]Default backend: {router.default.value}[/]")

    # ── Initialize orchestrator (vector memory is optional) ───────────────
    from orchestrator import JarvisOrchestrator
    jarvis = JarvisOrchestrator(router, use_vector_memory=True)

    # ── Load skills and editor skills ─────────────────────────────────────
    try:
        from skills import load_skills
        from skills import builtin_editor  # noqa: F401 — registers editor skills
        skill_count = len(load_skills())
        console.print(f"  [green]✓[/] Skills loaded: {skill_count}")
    except Exception as e:
        console.print(f"  [dim]✗ Skills: {e}[/]")

    # ── Load agent definitions ────────────────────────────────────────────
    try:
        from multi_agent.subagent import load_agent_definitions
        agent_count = len(load_agent_definitions())
        console.print(f"  [green]✓[/] Agent types: {agent_count}")
    except Exception as e:
        console.print(f"  [dim]✗ Agents: {e}[/]")

    # ── Permission mode ───────────────────────────────────────────────────
    from permissions import PERMISSIONS
    console.print(f"  [green]✓[/] Permission mode: {PERMISSIONS.mode.value}")

    console.print(f"\n[bold green]JARVIS MK37 online.[/] {len(backends)} backend(s) active.")
    console.print("[dim]Type /help for commands, /quit to exit.[/]\n")

    # ── Main loop ─────────────────────────────────────────────────────────
    while True:
        try:
            user_input = console.input("[bold cyan]OPERATOR >[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]JARVIS MK37 shutting down.[/]")
            jarvis.shutdown()
            break

        if not user_input:
            continue

        # ── Built-in commands ─────────────────────────────────────────────
        cmd = user_input.lower()

        if cmd in ("/quit", "/exit", "exit", "quit"):
            console.print("[yellow]Consolidating session memories...[/]")
            jarvis.shutdown()
            console.print("[yellow]Goodbye, sir.[/]")
            break

        if cmd == "/help":
            console.print(HELP_TEXT)
            continue

        if cmd == "/status":
            _show_status(jarvis, backends, router)
            continue

        if cmd == "/tools":
            _show_tools()
            continue

        if cmd == "/skills":
            _show_skills()
            continue

        if cmd == "/agents":
            _show_agents()
            continue

        if cmd == "/models":
            from config.models import get_model_config
            cfg = get_model_config()
            table = Table(title="Model Configuration", border_style="bright_blue")
            table.add_column("Backend", style="cyan bold")
            table.add_column("Model", style="white")
            table.add_column("Source", style="dim")
            import json as _json
            _json_data = {}
            _json_path = Path(__file__).parent / "config" / "models.json"
            if _json_path.exists():
                try:
                    _json_data = _json.loads(_json_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            _env_map = {
                "claude": "JARVIS_MODEL_CLAUDE", "gpt": "JARVIS_MODEL_GPT",
                "gemini": "JARVIS_MODEL_GEMINI", "ollama": "JARVIS_MODEL_OLLAMA",
                "nvidia": "JARVIS_MODEL_NVIDIA", "voice_live": "JARVIS_MODEL_VOICE",
                "voice_name": "JARVIS_VOICE_NAME", "default_backend": "JARVIS_DEFAULT_BACKEND",
            }
            for key in ["claude", "gpt", "gemini", "ollama", "nvidia", "voice_live", "voice_name", "default_backend"]:
                val = cfg.get(key, "")
                env_key = _env_map.get(key, "")
                if env_key and os.environ.get(env_key, "").strip():
                    src = f"env ({env_key})"
                elif key in _json_data:
                    src = "models.json"
                else:
                    src = "default"
                table.add_row(key, val, src)
            console.print(table)
            console.print("[dim]Edit config/models.json or set env vars (JARVIS_MODEL_*) to change.[/]")
            continue

        if cmd == "/clear":
            jarvis.working_memory.history.clear()
            console.print("[green]Conversation history cleared.[/]")
            continue

        if cmd.startswith("/memory"):
            _handle_memory_command(cmd[7:].strip())
            continue

        # ── Skill Installer Commands ──────────────────────────────────────
        if cmd.startswith("/install-skills"):
            pack_name = user_input[15:].strip()
            if not pack_name:
                console.print("[yellow]Usage: /install-skills <pack_name|git_url>[/]")
                console.print("[dim]Known packs: claude-skills, openclaw-master[/]")
                console.print("[dim]Or: /install-skills https://github.com/user/repo.git[/]")
            else:
                console.print(f"[bright_blue]Installing skill pack: {pack_name}...[/]")
                try:
                    from skills.installer import install_skill_pack
                    result = install_skill_pack(pack_name)
                    console.print(result)
                except Exception as e:
                    console.print(f"[red]Install failed: {e}[/]")
            continue

        if cmd == "/installed-skills":
            try:
                from skills.installer import list_installed
                console.print(list_installed())
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
            continue

        if cmd.startswith("/remove-skill"):
            skill_name = user_input[13:].strip()
            if not skill_name:
                console.print("[yellow]Usage: /remove-skill <skill_name>[/]")
            else:
                try:
                    from skills.installer import remove_skill
                    console.print(remove_skill(skill_name))
                except Exception as e:
                    console.print(f"[red]Error: {e}[/]")
            continue

        # ── Mode switching via /mode ──────────────────────────────────────
        if cmd.startswith("/mode "):
            # Let the orchestrator handle mode switches
            pass

        # ── Chat with ReAct loop ──────────────────────────────────────────
        try:
            with console.status("[bold bright_blue]JARVIS is thinking...[/]", spinner="dots"):
                response = jarvis.chat(user_input)

            console.print(Panel(
                Markdown(response),
                title="[bold bright_blue]JARVIS[/]",
                border_style="bright_blue",
                padding=(1, 2),
            ))

        except KeyboardInterrupt:
            console.print("[yellow]Request cancelled.[/]")
            continue
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            console.print(f"[dim]{traceback.format_exc()}[/]")
            continue


if __name__ == "__main__":
    main()
