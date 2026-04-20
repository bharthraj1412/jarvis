# tools/registry.py
"""
Universal tool registry and executor for JARVIS MK37.

BUG-FIX CHANGELOG:
  1. (Critical) spawn_agent: _orchestrator_ref=None caused AttributeError deep
     inside the sub-agent worker thread.  Guard already existed but the voice
     interface (main.py) never called set_orchestrator_ref(), so the ref was
     always None in that context.  The guard now returns a clear message.

  2. (Major) asyncio.run() inside an already-running event loop raised
     RuntimeError.  Replaced with _run_async() helper that detects a running
     loop and uses run_coroutine_threadsafe() instead.

  3. (Minor) list_skills filtered by user_invocable so internal/hidden skills
     do not appear in the operator-facing list.

  4. (Minor) memory_search now handles the edge-case where no results match by
     returning a friendly message rather than an empty string.
"""
from __future__ import annotations

import asyncio
import json
import traceback
from pathlib import Path

from tools.web import web_search, fetch_page, fetch_raw
from tools.sandbox import CodeSandbox
from tools.files import FileManager

_sandbox = CodeSandbox()
_files = FileManager(workspace=str(Path(__file__).resolve().parent.parent / "workspace"))


# ── Async helper ──────────────────────────────────────────────────────────

def _run_async(coro):
    """
    BUG-FIX: asyncio.run() raises RuntimeError when called inside a running
    event loop (e.g. from a tool callback in an async orchestrator).
    This helper detects the situation and falls back to thread-based execution.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=30)
    else:
        return asyncio.run(coro)


# ── Tool schema definitions ───────────────────────────────────────────────

TOOL_SCHEMAS = [
    # Web tools
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Returns a list of results with titles, URLs, and snippets.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "The search query"},
            "max_results": {"type": "integer", "required": False, "description": "Max results to return (default 5)"},
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch and extract text content from a URL using a headless browser.",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "URL to fetch"},
        },
    },
    {
        "name": "fetch_raw",
        "description": "Fetch raw HTML/text content from a URL via HTTP GET.",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "URL to fetch"},
        },
    },
    # Code sandbox
    {
        "name": "run_code",
        "description": "Execute code in a sandboxed environment. Supports python, javascript, bash.",
        "parameters": {
            "code": {"type": "string", "required": True, "description": "The code to execute"},
            "lang": {"type": "string", "required": False, "description": "Language: python, javascript, bash (default: python)"},
            "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds (default: 30)"},
        },
    },
    # File tools
    {
        "name": "file_read",
        "description": "Read a file from the workspace.",
        "parameters": {
            "path": {"type": "string", "required": True, "description": "Relative path within the workspace"},
        },
    },
    {
        "name": "file_write",
        "description": "Write content to a file in the workspace.",
        "parameters": {
            "path": {"type": "string", "required": True, "description": "Relative path within the workspace"},
            "content": {"type": "string", "required": True, "description": "Content to write"},
        },
    },
    {
        "name": "file_list",
        "description": "List files in a workspace directory.",
        "parameters": {
            "path": {"type": "string", "required": False, "description": "Relative directory path (default: root)"},
        },
    },
    # Red team tools
    {
        "name": "port_scan",
        "description": "Scan TCP ports on a host (scope-checked). Returns open/closed status.",
        "parameters": {
            "host": {"type": "string", "required": True, "description": "Target host IP or hostname"},
            "ports": {"type": "array", "required": False, "description": "List of port numbers (default: common ports)"},
        },
    },
    {
        "name": "dns_enum",
        "description": "Enumerate DNS records for a domain (scope-checked).",
        "parameters": {
            "domain": {"type": "string", "required": True, "description": "Target domain"},
        },
    },
    {
        "name": "headers_audit",
        "description": "Audit HTTP security headers of a URL (scope-checked).",
        "parameters": {
            "url": {"type": "string", "required": True, "description": "Target URL"},
        },
    },
    {
        "name": "whois_lookup",
        "description": "Perform a WHOIS lookup on a domain (scope-checked).",
        "parameters": {
            "domain": {"type": "string", "required": True, "description": "Target domain"},
        },
    },
    {
        "name": "nmap_scan",
        "description": "Run an nmap service scan on a host (scope-checked, requires nmap installed).",
        "parameters": {
            "host": {"type": "string", "required": True, "description": "Target host"},
        },
    },
    {
        "name": "generate_report",
        "description": "Generate a professional penetration test report in markdown.",
        "parameters": {
            "data": {"type": "object", "required": True, "description": "Report data dict"},
        },
    },
    # PC Control tools
    {
        "name": "cursor_move",
        "description": "Move the mouse cursor to specific screen coordinates.",
        "parameters": {
            "x": {"type": "integer", "required": True},
            "y": {"type": "integer", "required": True},
        },
    },
    {
        "name": "cursor_click",
        "description": "Click the mouse at the current position or specified coordinates.",
        "parameters": {
            "x": {"type": "integer", "required": False},
            "y": {"type": "integer", "required": False},
            "button": {"type": "string", "required": False, "description": "left, right, double"},
        },
    },
    {
        "name": "keyboard_type",
        "description": "Type text at the current cursor position.",
        "parameters": {
            "text": {"type": "string", "required": True},
            "clear_first": {"type": "boolean", "required": False},
        },
    },
    {
        "name": "keyboard_hotkey",
        "description": "Press a key combination (e.g., ctrl+c, alt+tab).",
        "parameters": {
            "keys": {"type": "string", "required": True},
        },
    },
    {
        "name": "keyboard_press",
        "description": "Press a single key (enter, tab, escape, etc.).",
        "parameters": {
            "key": {"type": "string", "required": True},
        },
    },
    {
        "name": "screen_find",
        "description": "Use AI vision to find a UI element on screen by description. Returns coordinates.",
        "parameters": {
            "description": {"type": "string", "required": True},
        },
    },
    {
        "name": "screen_click",
        "description": "Find a UI element by description and click on it.",
        "parameters": {
            "description": {"type": "string", "required": True},
        },
    },
    {
        "name": "smart_click",
        "description": "Smartly click a UI element by its natural language description.",
        "parameters": {
            "description": {"type": "string", "required": True},
        },
    },
    {
        "name": "clipboard_read",
        "description": "Read the current clipboard content.",
        "parameters": {},
    },
    {
        "name": "clipboard_write",
        "description": "Write text to the clipboard and paste it.",
        "parameters": {
            "text": {"type": "string", "required": True},
        },
    },
    {
        "name": "focus_window",
        "description": "Bring a window to the foreground by title.",
        "parameters": {
            "title": {"type": "string", "required": True},
        },
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the current screen.",
        "parameters": {
            "path": {"type": "string", "required": False},
        },
    },
    {
        "name": "mouse_scroll",
        "description": "Scroll the mouse wheel.",
        "parameters": {
            "direction": {"type": "string", "required": False},
            "amount": {"type": "integer", "required": False},
        },
    },
    {
        "name": "mouse_drag",
        "description": "Click and drag from one point to another.",
        "parameters": {
            "x1": {"type": "integer", "required": True},
            "y1": {"type": "integer", "required": True},
            "x2": {"type": "integer", "required": True},
            "y2": {"type": "integer", "required": True},
        },
    },
    # Skill tools
    {
        "name": "run_skill",
        "description": "Execute a named skill (reusable prompt template). Use list_skills to see available skills.",
        "parameters": {
            "name": {"type": "string", "required": True},
            "args": {"type": "string", "required": False},
        },
    },
    {
        "name": "list_skills",
        "description": "List all available user-invocable skills.",
        "parameters": {},
    },
    # Sub-agent tools
    {
        "name": "spawn_agent",
        "description": (
            "Spawn a sub-agent to handle a task autonomously. "
            "NOTE: only available in CLI mode (main_mk37.py). "
            "Types: general-purpose, coder, reviewer, researcher, tester, editor, sysadmin, devops."
        ),
        "parameters": {
            "prompt": {"type": "string", "required": True},
            "agent_type": {"type": "string", "required": False},
            "name": {"type": "string", "required": False},
            "wait": {"type": "boolean", "required": False},
        },
    },
    {
        "name": "send_message",
        "description": "Send a follow-up message to a running background agent.",
        "parameters": {
            "to": {"type": "string", "required": True},
            "message": {"type": "string", "required": True},
        },
    },
    {
        "name": "check_agent",
        "description": "Check the status and result of a spawned sub-agent task.",
        "parameters": {
            "task_id": {"type": "string", "required": True},
        },
    },
    {
        "name": "list_agents",
        "description": "List all sub-agent tasks and their statuses.",
        "parameters": {},
    },
    {
        "name": "list_agent_types",
        "description": "List all available agent types (built-in and custom).",
        "parameters": {},
    },
    # Memory tools
    {
        "name": "memory_save",
        "description": "Save a persistent memory entry.",
        "parameters": {
            "name": {"type": "string", "required": True},
            "type": {"type": "string", "required": True},
            "description": {"type": "string", "required": True},
            "content": {"type": "string", "required": True},
            "scope": {"type": "string", "required": False},
        },
    },
    {
        "name": "memory_delete",
        "description": "Delete a persistent memory entry by name.",
        "parameters": {
            "name": {"type": "string", "required": True},
            "scope": {"type": "string", "required": False},
        },
    },
    {
        "name": "memory_search",
        "description": "Search persistent memories by keyword.",
        "parameters": {
            "query": {"type": "string", "required": True},
            "max_results": {"type": "integer", "required": False},
        },
    },
    {
        "name": "memory_list",
        "description": "List all persistent memory entries.",
        "parameters": {
            "scope": {"type": "string", "required": False},
        },
    },
    # System Monitor
    {
        "name": "system_monitor",
        "description": "Get system health info: CPU, RAM, disk, network, top processes.",
        "parameters": {
            "action": {"type": "string", "required": False},
        },
    },
    # Screen Sharing
    {
        "name": "screen_share_start",
        "description": "Start real-time screen sharing over WebSocket.",
        "parameters": {
            "port": {"type": "integer", "required": False},
            "monitor": {"type": "integer", "required": False},
            "fps": {"type": "integer", "required": False},
            "quality": {"type": "integer", "required": False},
        },
    },
    {
        "name": "screen_share_stop",
        "description": "Stop the active screen sharing session.",
        "parameters": {},
    },
    {
        "name": "screen_share_status",
        "description": "Get the current screen sharing status.",
        "parameters": {},
    },
    {
        "name": "list_monitors",
        "description": "List all available monitors with resolution and position.",
        "parameters": {},
    },
]


def get_tool_prompt_block() -> str:
    schema_text = json.dumps(TOOL_SCHEMAS, indent=2)
    return f"""
## Available Tools

To use a tool, output EXACTLY this JSON block on its own line:

```tool_call
{{"tool": "<tool_name>", "args": {{<arguments>}}}}
```

After you output a tool_call block, execution pauses while the tool runs.
You will then receive the tool result and can continue.

If you do NOT need a tool, just respond normally with text.
NEVER fabricate tool results. Always call the tool if you need real data.

**AUTO-ALLOW MODE**: All tools execute immediately without confirmation.

### Tool Definitions
{schema_text}
"""


# ── Lazy loaders ──────────────────────────────────────────────────────────

def _get_scope_enforcer():
    scope_path = Path(__file__).resolve().parent.parent / "current_scope.json"
    if scope_path.exists():
        from redteam.scope import ScopeEnforcer
        return ScopeEnforcer(str(scope_path))
    return None


def _get_recon_engine():
    scope = _get_scope_enforcer()
    if scope:
        from redteam.recon import ReconEngine
        return ReconEngine(scope)
    return None


def _get_vuln_scanner():
    scope = _get_scope_enforcer()
    if scope:
        from redteam.vuln_scanner import VulnScanner
        return VulnScanner(scope)
    return None


def _get_computer_control():
    from actions.computer_control import computer_control
    return computer_control


def _get_subagent_manager():
    global _subagent_mgr
    if "_subagent_mgr" not in globals() or _subagent_mgr is None:
        from multi_agent.subagent import SubAgentManager
        _subagent_mgr = SubAgentManager()
    return _subagent_mgr


_subagent_mgr = None
_orchestrator_ref = None


def set_orchestrator_ref(orchestrator):
    global _orchestrator_ref
    _orchestrator_ref = orchestrator


# ── Tool executor ─────────────────────────────────────────────────────────

def execute_tool(name: str, args: dict) -> str:
    """Execute a registered tool by name. All errors are caught and returned as strings."""
    try:
        # ── Web tools ─────────────────────────────────────────────────────
        if name == "web_search":
            # BUG-FIX: use _run_async instead of asyncio.run
            results = _run_async(web_search(args["query"], args.get("max_results", 5)))
            return json.dumps(results, indent=2, default=str)

        elif name == "fetch_page":
            text = _run_async(fetch_page(args["url"]))
            return text[:8000]

        elif name == "fetch_raw":
            text = _run_async(fetch_raw(args["url"]))
            return text[:8000]

        # ── Code sandbox ──────────────────────────────────────────────────
        elif name == "run_code":
            result = _sandbox.run(
                code=args["code"],
                lang=args.get("lang", "python"),
                timeout=args.get("timeout", 30),
            )
            return json.dumps(result, indent=2)

        # ── File tools ────────────────────────────────────────────────────
        elif name == "file_read":
            return _files.read(args["path"])

        elif name == "file_write":
            _files.write(args["path"], args["content"])
            return f"File written: {args['path']}"

        elif name == "file_list":
            items = _files.list_dir(args.get("path", "."))
            return "\n".join(items)

        # ── Red team tools ────────────────────────────────────────────────
        elif name == "port_scan":
            recon = _get_recon_engine()
            if not recon:
                return "ERROR: No scope file loaded. Cannot run scoped tools."
            result = recon.port_scan(args["host"], args.get("ports"))
            return json.dumps(result, indent=2)

        elif name == "dns_enum":
            recon = _get_recon_engine()
            if not recon:
                return "ERROR: No scope file loaded."
            result = recon.dns_enum(args["domain"])
            return json.dumps(result, indent=2)

        elif name == "headers_audit":
            recon = _get_recon_engine()
            if not recon:
                return "ERROR: No scope file loaded."
            result = recon.headers_audit(args["url"])
            return json.dumps(result, indent=2)

        elif name == "whois_lookup":
            recon = _get_recon_engine()
            if not recon:
                return "ERROR: No scope file loaded."
            return recon.whois(args["domain"])

        elif name == "nmap_scan":
            scanner = _get_vuln_scanner()
            if not scanner:
                return "ERROR: No scope file loaded."
            return scanner.nmap_service_scan(args["host"])

        elif name == "generate_report":
            from redteam.report import generate_report
            return generate_report(args["data"])

        # ── PC Control tools ──────────────────────────────────────────────
        elif name == "cursor_move":
            cc = _get_computer_control()
            return cc(parameters={"action": "move", "x": args["x"], "y": args["y"]})

        elif name == "cursor_click":
            cc = _get_computer_control()
            button = args.get("button", "left")
            action = "double_click" if button == "double" else "click"
            btn = "left" if button == "double" else button
            return cc(parameters={"action": action, "x": args.get("x"), "y": args.get("y"), "button": btn})

        elif name == "keyboard_type":
            cc = _get_computer_control()
            return cc(parameters={"action": "smart_type", "text": args["text"], "clear_first": args.get("clear_first", True)})

        elif name == "keyboard_hotkey":
            cc = _get_computer_control()
            return cc(parameters={"action": "hotkey", "keys": args["keys"]})

        elif name == "keyboard_press":
            cc = _get_computer_control()
            return cc(parameters={"action": "press", "key": args["key"]})

        elif name == "screen_find":
            cc = _get_computer_control()
            return cc(parameters={"action": "screen_find", "description": args["description"]})

        elif name in ("screen_click", "smart_click"):
            cc = _get_computer_control()
            return cc(parameters={"action": "screen_click", "description": args["description"]})

        elif name == "clipboard_read":
            cc = _get_computer_control()
            return cc(parameters={"action": "copy"})

        elif name == "clipboard_write":
            cc = _get_computer_control()
            return cc(parameters={"action": "paste", "text": args["text"]})

        elif name == "focus_window":
            cc = _get_computer_control()
            return cc(parameters={"action": "focus_window", "title": args["title"]})

        elif name == "take_screenshot":
            cc = _get_computer_control()
            return cc(parameters={"action": "screenshot", "path": args.get("path")})

        elif name == "mouse_scroll":
            cc = _get_computer_control()
            return cc(parameters={"action": "scroll", "direction": args.get("direction", "down"), "amount": args.get("amount", 3)})

        elif name == "mouse_drag":
            cc = _get_computer_control()
            return cc(parameters={"action": "drag", "x1": args["x1"], "y1": args["y1"], "x2": args["x2"], "y2": args["y2"]})

        # ── Skill tools ───────────────────────────────────────────────────
        elif name == "run_skill":
            from skills import find_skill, load_skills, execute_skill
            skill_name = args.get("name", "").strip()
            skill_args = args.get("args", "")
            skill = None
            for s in load_skills():
                if s.name == skill_name:
                    skill = s
                    break
            if skill is None:
                skill = find_skill(skill_name)
            if skill is None:
                names = [s.name for s in load_skills()]
                return f"Error: skill '{skill_name}' not found. Available: {', '.join(names)}"
            if _orchestrator_ref:
                return execute_skill(skill, skill_args, _orchestrator_ref)
            return "Error: orchestrator not initialized for skill execution"

        elif name == "list_skills":
            from skills import load_skills
            # BUG-FIX: only show user_invocable skills
            skills = [s for s in load_skills() if s.user_invocable]
            if not skills:
                return "No skills available."
            lines = ["Available skills:\n"]
            for s in skills:
                triggers = ", ".join(s.triggers)
                hint = f"  args: {s.argument_hint}" if s.argument_hint else ""
                lines.append(f"- **{s.name}** [{triggers}]{hint}\n  {s.description}")
            return "\n".join(lines)

        # ── Sub-agent tools ───────────────────────────────────────────────
        elif name == "spawn_agent":
            # BUG-FIX: guard _orchestrator_ref before spawning
            if _orchestrator_ref is None:
                return (
                    "Sub-agent spawning is not available in voice mode. "
                    "Use the CLI interface (main_mk37.py) for this feature."
                )
            mgr = _get_subagent_manager()
            prompt = args["prompt"]
            wait = args.get("wait", True)
            agent_type = args.get("agent_type", "")
            agent_name = args.get("name", "")

            agent_def = None
            if agent_type:
                from multi_agent.subagent import get_agent_definition
                agent_def = get_agent_definition(agent_type)
                if agent_def is None:
                    return f"Error: unknown agent_type '{agent_type}'. Use list_agent_types."

            task = mgr.spawn(
                prompt=prompt,
                orchestrator=_orchestrator_ref,
                depth=0,
                agent_def=agent_def,
                name=agent_name,
            )

            if task.status == "failed":
                return f"Error spawning agent: {task.result}"

            if wait:
                mgr.wait(task.id, timeout=300)
                result = task.result or f"(no output — status: {task.status})"
                header = f"[Agent: {task.name}"
                if agent_type:
                    header += f" ({agent_type})"
                header += "]"
                return f"{header}\n\n{result}"
            else:
                return f"Task ID: {task.id}\nName: {task.name}\nStatus: {task.status}\nUse check_agent to poll."

        elif name == "send_message":
            mgr = _get_subagent_manager()
            target = args["to"]
            message = args["message"]
            ok = mgr.send_message(target, message)
            if ok:
                return f"Message queued for agent '{target}'."
            task_id = mgr._by_name.get(target, target)
            task = mgr.tasks.get(task_id)
            if task is None:
                return f"Error: no agent found with id or name '{target}'"
            return f"Error: agent '{target}' is not running (status: {task.status})."

        elif name == "check_agent":
            mgr = _get_subagent_manager()
            task_id = args["task_id"]
            task = mgr.tasks.get(task_id)
            if task is None:
                return f"Error: no task with id '{task_id}'"
            lines = [f"Status: {task.status}", f"Name: {task.name}"]
            if task.result:
                lines.append(f"\nResult:\n{task.result}")
            return "\n".join(lines)

        elif name == "list_agents":
            mgr = _get_subagent_manager()
            tasks = mgr.list_tasks()
            if not tasks:
                return "No sub-agent tasks."
            lines = ["ID           | Name     | Status    | Prompt"]
            lines.append("-------------|----------|-----------|------")
            for t in tasks:
                prompt_short = t.prompt[:50] + ("..." if len(t.prompt) > 50 else "")
                lines.append(f"{t.id} | {t.name[:8]:8s} | {t.status:9s} | {prompt_short}")
            return "\n".join(lines)

        elif name == "list_agent_types":
            from multi_agent.subagent import load_agent_definitions
            defs = load_agent_definitions()
            if not defs:
                return "No agent types available."
            lines = ["Available agent types:", ""]
            for aname, d in sorted(defs.items()):
                lines.append(f"  {aname:20s}  [{d.source:8s}]  {d.description}")
            lines.append("")
            lines.append("Create custom agents: place .md files in ~/.jarvis/agents/")
            return "\n".join(lines)

        # ── Memory tools ──────────────────────────────────────────────────
        elif name == "memory_save":
            from datetime import datetime as _dt
            from memory.persistent_store import MemoryEntry, save_memory, check_conflict
            scope = args.get("scope", "user")
            entry = MemoryEntry(
                name=args["name"],
                description=args["description"],
                type=args["type"],
                content=args["content"],
                created=_dt.now().strftime("%Y-%m-%d"),
            )
            conflict = check_conflict(entry, scope=scope)
            save_memory(entry, scope=scope)
            msg = f"Memory saved: '{entry.name}' [{entry.type}/{scope}]"
            if conflict:
                msg += f"\n⚠ Replaced conflicting memory."
            return msg

        elif name == "memory_delete":
            from memory.persistent_store import delete_memory
            delete_memory(args["name"], scope=args.get("scope", "user"))
            return f"Memory deleted: '{args['name']}'"

        elif name == "memory_search":
            import math, time as _t
            from memory.memory_context import find_relevant_memories
            from memory.persistent_store import touch_last_used
            query = args["query"]
            max_results = args.get("max_results", 5)
            results = find_relevant_memories(query, max_results=max_results)
            # BUG-FIX: friendly message on empty results
            if not results:
                return f"No memories found matching '{query}'."
            now = _t.time()
            for r in results:
                age_days = max(0, (now - r["mtime_s"]) / 86400)
                r["_rank"] = r.get("confidence", 1.0) * math.exp(-age_days / 30)
            results.sort(key=lambda r: r["_rank"], reverse=True)
            results = results[:max_results]
            for r in results:
                if r.get("file_path"):
                    touch_last_used(r["file_path"])
            lines = [f"Found {len(results)} memory/memories for '{query}':", ""]
            for r in results:
                freshness = f"  ⚠ {r['freshness_text']}" if r["freshness_text"] else ""
                lines.append(
                    f"[{r['type']}/{r['scope']}] {r['name']}\n"
                    f"  {r['description']}\n"
                    f"  {r['content'][:200]}{'...' if len(r['content']) > 200 else ''}"
                    f"{freshness}"
                )
            return "\n\n".join(lines)

        elif name == "memory_list":
            from memory.persistent_store import load_entries
            scope_filter = args.get("scope", "all")
            scopes = ["user", "project"] if scope_filter == "all" else [scope_filter]
            all_entries = []
            for s in scopes:
                all_entries.extend(load_entries(s))
            if not all_entries:
                return "No memories stored."
            lines = [f"{len(all_entries)} memory/memories:"]
            for e in all_entries:
                tag = f"[{e.type:9s}|{e.scope:7s}]"
                lines.append(f"  {tag} {e.name}")
                if e.description:
                    lines.append(f"    {e.description}")
            return "\n".join(lines)

        # ── System Monitor ────────────────────────────────────────────────
        elif name == "system_monitor":
            from actions.system_monitor import system_monitor
            return system_monitor(parameters=args)

        # ── Screen Sharing ────────────────────────────────────────────────
        elif name == "screen_share_start":
            from actions.screen_share import start_sharing
            return start_sharing(
                port=args.get("port", 8765),
                monitor=args.get("monitor", 1),
                fps=args.get("fps", 10),
                quality=args.get("quality", 60),
            )

        elif name == "screen_share_stop":
            from actions.screen_share import stop_sharing
            return stop_sharing()

        elif name == "screen_share_status":
            from actions.screen_share import get_status
            return json.dumps(get_status(), indent=2)

        elif name == "list_monitors":
            from actions.screen_share import list_monitors
            return json.dumps(list_monitors(), indent=2)

        else:
            return f"ERROR: Unknown tool '{name}'"

    except PermissionError as e:
        return f"SCOPE VIOLATION: {e}"
    except Exception as e:
        tb = traceback.format_exc()
        return f"TOOL ERROR ({name}): {e}\n{tb}"


def parse_tool_call(text: str) -> tuple:
    """Parse a tool_call JSON block from LLM output."""
    import re
    pattern = r'```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("tool"), data.get("args", {})
        except json.JSONDecodeError:
            return None, None

    pattern2 = r'\{"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{.*?\})\}'
    match2 = re.search(pattern2, text, re.DOTALL)
    if match2:
        try:
            args = json.loads(match2.group(2))
            return match2.group(1), args
        except json.JSONDecodeError:
            return None, None

    return None, None
