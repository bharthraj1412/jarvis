# history/audit_writer.py
"""
Structured JSON audit writer for JARVIS MK37.

Replaces the old plain-text audit.log with a structured JSONL format
while maintaining a parallel human-readable log for grep compatibility.

Writes to:
  ~/.jarvis/history/audit.jsonl  — structured JSON Lines (machine-readable)
  ~/.jarvis/audit.log            — human-readable plain text (grep-friendly)

Thread-safe: all writes go through a threading.Lock().
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_JSONL_PATH = Path.home() / ".jarvis" / "history" / "audit.jsonl"
_PLAINTEXT_PATH = Path.home() / ".jarvis" / "audit.log"
_lock = threading.Lock()

# Module-level session_id — set by the orchestrator on session start
_current_session_id: str = ""


def set_session_id(session_id: str) -> None:
    """Set the current session ID for audit entries."""
    global _current_session_id
    _current_session_id = session_id


def write_audit(
    tool: str,
    args: dict | str | None,
    decision: str,
    latency_ms: int = 0,
    error: str | None = None,
    session_id: str | None = None,
) -> None:
    """Write a structured audit entry to both JSONL and plain-text logs.

    Args:
        tool:       name of the tool that was invoked
        args:       tool arguments (dict or string, truncated for storage)
        decision:   authorization decision (ALLOWED, DENIED, CONFIRMED, etc.)
        latency_ms: execution time in milliseconds
        error:      error message if the tool call failed, or None
        session_id: override session ID (uses module-level default if None)
    """
    sid = session_id or _current_session_id
    now = datetime.now(tz=timezone.utc)

    # Truncate args for storage
    args_truncated: dict | str | None = None
    if args is not None:
        if isinstance(args, dict):
            try:
                args_str = json.dumps(args, default=str)
                if len(args_str) > 500:
                    args_truncated = json.loads(args_str[:500] + "}")
                else:
                    args_truncated = args
            except (TypeError, ValueError, json.JSONDecodeError):
                args_truncated = str(args)[:500]
        else:
            args_truncated = str(args)[:500]

    # Build the JSONL entry
    entry = {
        "ts": now.isoformat(),
        "session_id": sid,
        "tool": tool,
        "args": args_truncated,
        "decision": decision,
        "latency_ms": latency_ms,
        "error": error,
    }

    # Build the human-readable line
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    args_summary = ""
    if args_truncated:
        try:
            args_summary = json.dumps(args_truncated, default=str)[:200]
        except (TypeError, ValueError):
            args_summary = str(args_truncated)[:200]

    plain_line = f"[{timestamp_str}] {decision:20s} | {tool:25s} | {args_summary}"
    if error:
        plain_line += f" | ERROR: {error[:100]}"
    if latency_ms:
        plain_line += f" | {latency_ms}ms"
    plain_line += "\n"

    with _lock:
        try:
            _JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_JSONL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass  # Audit logging must never crash the system

        try:
            _PLAINTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_PLAINTEXT_PATH, "a", encoding="utf-8") as f:
                f.write(plain_line)
        except Exception:
            pass
