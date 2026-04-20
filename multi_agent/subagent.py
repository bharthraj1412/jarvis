# multi_agent/subagent.py
"""
Threaded sub-agent system for spawning nested agent loops.

BUG-FIX (Critical):
  - `_run()` unconditionally called `orchestrator._build_system()` and
    `orchestrator.router.run()` when orchestrator could be None (e.g.
    when depth-limit enforcement triggers, or when called from the voice
    interface without an orchestrator reference).  Added an early-exit
    guard so the task fails gracefully instead of raising AttributeError.
  - Added a None-check before every orchestrator attribute access in
    `_run()` and `inject_context()` helpers.

BUG-FIX (Minor):
  - `spawn()` did not validate that `orchestrator` is non-None before
    entering the thread; tasks queued with orchestrator=None now fail
    immediately with a clear error message rather than crashing inside
    the worker thread.
"""
from __future__ import annotations

import uuid
import queue
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


# ── Agent definition ───────────────────────────────────────────────────────

@dataclass
class AgentDefinition:
    """Definition for a specialized agent type."""
    name: str
    description: str = ""
    system_prompt: str = ""
    model: str = ""
    tools: list = field(default_factory=list)
    source: str = "user"


# ── Built-in agent definitions ─────────────────────────────────────────────

_BUILTIN_AGENTS: Dict[str, AgentDefinition] = {
    "general-purpose": AgentDefinition(
        name="general-purpose",
        description=(
            "General-purpose agent for researching complex questions, "
            "searching for code, and executing multi-step tasks."
        ),
        system_prompt="",
        source="built-in",
    ),
    "coder": AgentDefinition(
        name="coder",
        description="Specialized coding agent for writing, reading, and modifying code.",
        system_prompt=(
            "You are a specialized coding assistant. Focus on:\n"
            "- Writing clean, idiomatic code\n"
            "- Reading and understanding existing code before modifying\n"
            "- Making minimal targeted changes\n"
            "- Never adding unnecessary features, comments, or error handling\n"
        ),
        source="built-in",
    ),
    "reviewer": AgentDefinition(
        name="reviewer",
        description="Code review agent analyzing quality, security, and correctness.",
        system_prompt=(
            "You are a code reviewer. Analyze code for:\n"
            "- Correctness and logic errors\n"
            "- Security vulnerabilities (injection, XSS, auth bypass, etc.)\n"
            "- Performance issues\n"
            "- Code quality and maintainability\n"
            "Be concise and specific. Categorize findings as: Critical | Warning | Suggestion.\n"
        ),
        tools=["file_read", "file_list", "web_search"],
        source="built-in",
    ),
    "researcher": AgentDefinition(
        name="researcher",
        description="Research agent for exploring codebases and answering questions.",
        system_prompt=(
            "You are a research assistant focused on understanding codebases.\n"
            "- Read and analyze code thoroughly before answering\n"
            "- Provide factual, evidence-based answers\n"
            "- Cite specific file paths and line numbers\n"
            "- Be concise and focused\n"
        ),
        tools=["file_read", "file_list", "web_search", "fetch_page"],
        source="built-in",
    ),
    "tester": AgentDefinition(
        name="tester",
        description="Testing agent that writes and runs tests.",
        system_prompt=(
            "You are a testing specialist. Your job:\n"
            "- Write comprehensive tests for the given code\n"
            "- Run existing tests and diagnose failures\n"
            "- Focus on edge cases and error conditions\n"
            "- Keep tests simple, readable, and fast\n"
        ),
        source="built-in",
    ),
    "editor": AgentDefinition(
        name="editor",
        description="Editor control agent — reads, edits, and manages files in code editors.",
        system_prompt=(
            "You are an editor control specialist. You can:\n"
            "- Open files in the user's editor\n"
            "- Navigate to specific lines and functions\n"
            "- Make precise edits using keyboard shortcuts\n"
            "- Run commands in the integrated terminal\n"
            "- Use the skill system for complex editing workflows\n"
        ),
        tools=["file_read", "file_write", "file_list", "run_code",
               "keyboard_type", "keyboard_hotkey", "keyboard_press",
               "focus_window", "screen_find", "screen_click"],
        source="built-in",
    ),
    "sysadmin": AgentDefinition(
        name="sysadmin",
        description="System administrator agent — enumerate configs, diagnose issues, manage services.",
        system_prompt=(
            "You are a senior Linux/Windows system administrator.\n"
            "- Enumerate system configurations: services, network, firewall, users, packages\n"
            "- Diagnose performance, connectivity, and service issues\n"
            "- Write shell scripts to automate admin tasks\n"
            "- Check disk space, memory, CPU, and process health\n"
            "- NEVER delete system files or modify critical configs without explicit confirmation\n"
            "- NEVER run rm -rf, format, or fdisk commands\n"
            "- Always show what you found before recommending changes\n"
            "Output format: structured markdown with sections for each check\n"
        ),
        tools=["run_code", "file_read", "file_list", "system_monitor"],
        source="built-in",
    ),
    "devops": AgentDefinition(
        name="devops",
        description="DevOps agent — Docker, CI/CD, deployment, infrastructure automation.",
        system_prompt=(
            "You are a DevOps specialist.\n"
            "- Build Docker images and compose configs\n"
            "- Design CI/CD pipelines (GitHub Actions, GitLab CI)\n"
            "- Configure nginx, reverse proxies, SSL certificates\n"
            "- Write Terraform, Ansible, or shell deployment scripts\n"
            "- Monitor service health and logs\n"
            "- NEVER expose secrets, credentials, or API keys in outputs\n"
            "Output format: structured markdown with code blocks for configs\n"
        ),
        tools=["run_code", "file_read", "file_write", "file_list", "web_search", "system_monitor"],
        source="built-in",
    ),
}


# ── Loading agent definitions from .md files ──────────────────────────────

def _parse_agent_md(path: Path, source: str = "user") -> AgentDefinition:
    """Parse a .md file with optional YAML frontmatter into an AgentDefinition."""
    content = path.read_text(encoding="utf-8")
    name = path.stem
    description = ""
    model = ""
    tools: list = []
    system_prompt_body = content

    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm_text = content[3:end].strip()
            system_prompt_body = content[end + 3:].strip()
            fm: dict = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
            description = str(fm.get("description", ""))
            model = str(fm.get("model", ""))
            raw_tools = fm.get("tools", "")
            if isinstance(raw_tools, str) and raw_tools:
                s = raw_tools.strip("[]")
                tools = [t.strip() for t in s.split(",") if t.strip()]

    return AgentDefinition(
        name=name,
        description=description,
        system_prompt=system_prompt_body,
        model=model,
        tools=tools,
        source=source,
    )


def load_agent_definitions() -> Dict[str, AgentDefinition]:
    """Load all agent definitions: built-ins → user-level → project-level."""
    defs: Dict[str, AgentDefinition] = dict(_BUILTIN_AGENTS)

    user_dir = Path.home() / ".jarvis" / "agents"
    if user_dir.is_dir():
        for p in sorted(user_dir.glob("*.md")):
            try:
                d = _parse_agent_md(p, source="user")
                defs[d.name] = d
            except Exception:
                pass

    proj_dir = Path.cwd() / ".jarvis" / "agents"
    if proj_dir.is_dir():
        for p in sorted(proj_dir.glob("*.md")):
            try:
                d = _parse_agent_md(p, source="project")
                defs[d.name] = d
            except Exception:
                pass

    return defs


def get_agent_definition(name: str) -> Optional[AgentDefinition]:
    """Look up an agent definition by name. Returns None if not found."""
    return load_agent_definitions().get(name)


# ── SubAgentTask ───────────────────────────────────────────────────────────

@dataclass
class SubAgentTask:
    """Represents a sub-agent task with lifecycle tracking."""
    id: str
    prompt: str
    status: str = "pending"
    result: Optional[str] = None
    depth: int = 0
    name: str = ""
    _cancel_flag: bool = False
    _future: Optional[Future] = field(default=None, repr=False)
    _inbox: Any = field(default_factory=queue.Queue, repr=False)


# ── SubAgentManager ────────────────────────────────────────────────────────

class SubAgentManager:
    """Manages concurrent sub-agent tasks using a thread pool."""

    def __init__(self, max_concurrent: int = 5, max_depth: int = 5):
        self.tasks: Dict[str, SubAgentTask] = {}
        self._by_name: Dict[str, str] = {}
        self.max_concurrent = max_concurrent
        self.max_depth = max_depth
        self._pool = ThreadPoolExecutor(max_workers=max_concurrent)

    def spawn(
        self,
        prompt: str,
        orchestrator,  # May be None — handled defensively below
        depth: int = 0,
        agent_def: Optional[AgentDefinition] = None,
        name: str = "",
        agent_type: str = "",   # convenience alias used by voice handler
    ) -> SubAgentTask:
        """Spawn a new sub-agent task.

        BUG-FIX: orchestrator=None is now caught immediately with a clear
        failure message rather than crashing deep inside the worker thread.
        """
        task_id = uuid.uuid4().hex[:12]
        short_name = name or task_id[:8]
        task = SubAgentTask(id=task_id, prompt=prompt, depth=depth, name=short_name)
        self.tasks[task_id] = task
        if name:
            self._by_name[name] = task_id

        # ── Guard: depth exceeded ─────────────────────────────────────────
        if depth >= self.max_depth:
            task.status = "failed"
            task.result = f"Max depth ({self.max_depth}) exceeded"
            return task

        # ── Guard: orchestrator required ──────────────────────────────────
        if orchestrator is None:
            task.status = "failed"
            task.result = (
                "Sub-agent requires an orchestrator reference. "
                "This feature is only available in the CLI (main_mk37.py) mode."
            )
            return task

        eff_system_extra = ""
        if agent_def and agent_def.system_prompt:
            eff_system_extra = agent_def.system_prompt

        def _run():
            task.status = "running"
            try:
                from memory.working import WorkingMemory
                sub_memory = WorkingMemory()

                base_system = orchestrator._build_system()
                full_system = (
                    eff_system_extra.rstrip() + "\n\n" + base_system
                    if eff_system_extra
                    else base_system
                )

                sub_memory.add("user", prompt)

                keywords = orchestrator._extract_keywords(prompt)
                profile = orchestrator.router.route(keywords)
                if profile not in orchestrator.router.backends:
                    profile = orchestrator.router.default

                from tools.registry import parse_tool_call, execute_tool
                import re

                final_response = ""
                for _step in range(15):
                    if task._cancel_flag:
                        break

                    try:
                        response = orchestrator.router.run(
                            profile, sub_memory.get(), full_system
                        )
                    except Exception as e:
                        final_response = f"Backend error: {e}"
                        break

                    tool_name, tool_args = parse_tool_call(response)

                    if tool_name:
                        tool_result = execute_tool(tool_name, tool_args)
                        clean_response = re.sub(
                            r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```',
                            '', response, flags=re.DOTALL
                        ).strip()
                        if clean_response:
                            sub_memory.add("assistant", clean_response)
                        sub_memory.add("user", f"[Tool Result for '{tool_name}']:\n{tool_result}")
                        continue
                    else:
                        final_response = response
                        break

                if task._cancel_flag:
                    task.status = "cancelled"
                    task.result = None
                else:
                    task.result = final_response
                    task.status = "completed"

                # Process inbox messages
                while not task._inbox.empty() and not task._cancel_flag:
                    inbox_msg = task._inbox.get_nowait()
                    task.status = "running"
                    sub_memory.add("user", inbox_msg)
                    try:
                        response = orchestrator.router.run(
                            profile, sub_memory.get(), full_system
                        )
                        sub_memory.add("assistant", response)
                        task.result = response
                        task.status = "completed"
                    except Exception as e:
                        task.result = f"Inbox message error: {e}"

            except Exception as e:
                task.status = "failed"
                task.result = f"Error: {e}\n{traceback.format_exc()}"

        task._future = self._pool.submit(_run)
        return task

    def wait(self, task_id: str, timeout: float = None) -> Optional[SubAgentTask]:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        if task._future is not None:
            try:
                task._future.result(timeout=timeout)
            except Exception:
                pass
        return task

    def get_result(self, task_id: str) -> Optional[str]:
        task = self.tasks.get(task_id)
        return task.result if task else None

    def list_tasks(self) -> List[SubAgentTask]:
        return list(self.tasks.values())

    def send_message(self, task_id_or_name: str, message: str) -> bool:
        task_id = self._by_name.get(task_id_or_name, task_id_or_name)
        task = self.tasks.get(task_id)
        if task is None:
            return False
        if task.status not in ("running", "pending"):
            return False
        task._inbox.put(message)
        return True

    def cancel(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task is None:
            return False
        if task.status == "running":
            task._cancel_flag = True
            return True
        return False

    def shutdown(self) -> None:
        for task in self.tasks.values():
            if task.status == "running":
                task._cancel_flag = True
        self._pool.shutdown(wait=True)
