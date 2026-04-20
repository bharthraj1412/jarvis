# permissions.py
"""
JARVIS MK37 — Permission & Audit System.

Provides a global permission gate that controls tool execution,
plus an audit log that records every tool invocation.

Modes:
  allow_all           — no prompts, everything runs (default)
  confirm_destructive — prompt before file deletes, system changes
  confirm_all         — prompt before every tool (debug mode)

Audit log: ~/.jarvis/audit.log (every tool call logged with timestamp)
Per-tool deny: JARVIS_DENY_TOOLS env var (comma-separated tool names)
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class PermissionMode(Enum):
    ALLOW_ALL = "allow_all"
    CONFIRM_DESTRUCTIVE = "confirm_destructive"
    CONFIRM_ALL = "confirm_all"


# Tools that are considered destructive (only used in confirm_destructive mode)
DESTRUCTIVE_TOOLS = frozenset({
    "file_delete",
    "nmap_scan",
    "port_scan",
})

# Tools that are always allowed regardless of mode
ALWAYS_ALLOWED = frozenset({
    "web_search",
    "fetch_page",
    "fetch_raw",
    "file_read",
    "file_list",
    "list_skills",
    "list_agents",
    "list_agent_types",
    "check_agent",
    "memory_search",
    "memory_list",
    "take_screenshot",
    "clipboard_read",
})

# Audit log path
AUDIT_LOG_PATH = Path.home() / ".jarvis" / "audit.log"


def _load_deny_list() -> frozenset:
    """Load per-tool deny list from env var JARVIS_DENY_TOOLS."""
    raw = os.environ.get("JARVIS_DENY_TOOLS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(t.strip().lower() for t in raw.split(",") if t.strip())


@dataclass
class PermissionPolicy:
    """Controls whether tools require user confirmation before execution."""
    mode: PermissionMode = PermissionMode.ALLOW_ALL
    deny_names: frozenset = field(default_factory=frozenset)
    deny_prefixes: tuple = ()
    audit_enabled: bool = True

    def check(self, tool_name: str, args: dict = None) -> bool:
        """
        Check if a tool is allowed to execute.

        Returns:
            True if allowed, False if denied.
        """
        lowered = tool_name.lower()

        # Hard deny list (static + env-based)
        if lowered in self.deny_names:
            self._audit(tool_name, args, "DENIED (deny_list)")
            return False
        for prefix in self.deny_prefixes:
            if lowered.startswith(prefix):
                self._audit(tool_name, args, "DENIED (prefix)")
                return False

        # Mode-based checks
        if self.mode == PermissionMode.ALLOW_ALL:
            self._audit(tool_name, args, "ALLOWED")
            return True

        if self.mode == PermissionMode.CONFIRM_DESTRUCTIVE:
            if lowered in DESTRUCTIVE_TOOLS:
                result = self._confirm(tool_name, args)
                self._audit(tool_name, args, "CONFIRMED" if result else "REJECTED")
                return result
            self._audit(tool_name, args, "ALLOWED")
            return True

        if self.mode == PermissionMode.CONFIRM_ALL:
            if lowered in ALWAYS_ALLOWED:
                self._audit(tool_name, args, "ALLOWED (safe)")
                return True
            result = self._confirm(tool_name, args)
            self._audit(tool_name, args, "CONFIRMED" if result else "REJECTED")
            return result

        self._audit(tool_name, args, "ALLOWED (fallback)")
        return True

    def _confirm(self, tool_name: str, args: dict = None) -> bool:
        """Ask user for confirmation. In auto-allow mode this is never called."""
        try:
            response = input(f"[JARVIS] Allow tool '{tool_name}'? (y/N): ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def _audit(self, tool_name: str, args: dict = None, decision: str = ""):
        """Log tool execution to the audit trail."""
        if not self.audit_enabled:
            return
        try:
            AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            args_summary = ""
            if args:
                # Truncate large args for log readability
                try:
                    args_str = json.dumps(args, default=str)
                    args_summary = args_str[:200]
                except Exception:
                    args_summary = str(args)[:200]
            log_line = f"[{timestamp}] {decision:20s} | {tool_name:25s} | {args_summary}\n"
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass  # Audit logging should never crash the system

    def blocks(self, tool_name: str) -> bool:
        """Inverse of check — returns True if the tool is blocked."""
        return not self.check(tool_name)


def _load_permission_mode() -> PermissionMode:
    """Load permission mode from environment variable."""
    mode_str = os.environ.get("JARVIS_PERMISSION_MODE", "allow_all").lower()
    try:
        return PermissionMode(mode_str)
    except ValueError:
        return PermissionMode.ALLOW_ALL


def _load_audit_setting() -> bool:
    """Check JARVIS_AUDIT_LOG env var. Default: True."""
    val = os.environ.get("JARVIS_AUDIT_LOG", "true").lower()
    return val not in ("false", "0", "no", "off")


# ── Global singleton ──────────────────────────────────────────────────────────
PERMISSIONS = PermissionPolicy(
    mode=_load_permission_mode(),
    deny_names=_load_deny_list(),
    audit_enabled=_load_audit_setting(),
)
