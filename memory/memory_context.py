# memory/memory_context.py
"""
Memory context building for system prompt injection.
Ported from the Claude Code collection for JARVIS MK37.

Provides:
  get_memory_context()      — full context string for system prompt
  find_relevant_memories()  — keyword relevance filtering
"""
from __future__ import annotations

from memory.persistent_store import (
    INDEX_FILENAME,
    MAX_INDEX_LINES,
    MAX_INDEX_BYTES,
    get_index_content,
    search_memory,
)
from memory.memory_scan import scan_all_memories, memory_freshness_text
from memory.memory_types import MEMORY_SYSTEM_PROMPT


# ── Index truncation ───────────────────────────────────────────────────────

def truncate_index_content(raw: str) -> str:
    """Truncate MEMORY.md content to line AND byte limits, appending a warning."""
    trimmed = raw.strip()
    content_lines = trimmed.split("\n")
    line_count = len(content_lines)
    byte_count = len(trimmed.encode())

    was_line_truncated = line_count > MAX_INDEX_LINES
    was_byte_truncated = byte_count > MAX_INDEX_BYTES

    if not was_line_truncated and not was_byte_truncated:
        return trimmed

    truncated = "\n".join(content_lines[:MAX_INDEX_LINES]) if was_line_truncated else trimmed

    if len(truncated.encode()) > MAX_INDEX_BYTES:
        raw_bytes = truncated.encode()
        cut = raw_bytes[:MAX_INDEX_BYTES].rfind(b"\n")
        truncated = raw_bytes[: cut if cut > 0 else MAX_INDEX_BYTES].decode(errors="replace")

    if was_byte_truncated and not was_line_truncated:
        reason = f"{byte_count:,} bytes (limit: {MAX_INDEX_BYTES:,})"
    elif was_line_truncated and not was_byte_truncated:
        reason = f"{line_count} lines (limit: {MAX_INDEX_LINES})"
    else:
        reason = f"{line_count} lines and {byte_count:,} bytes"

    warning = (
        f"\n\n> WARNING: {INDEX_FILENAME} is {reason}. "
        "Only part of it was loaded."
    )
    return truncated + warning


# ── System prompt context ──────────────────────────────────────────────────

def get_memory_context(include_guidance: bool = False) -> str:
    """Return memory context for injection into the system prompt.

    Combines user-level and project-level MEMORY.md content (if present).
    Returns empty string when no memories exist.
    """
    parts: list[str] = []

    user_content = get_index_content("user")
    if user_content:
        truncated = truncate_index_content(user_content)
        parts.append(truncated)

    proj_content = get_index_content("project")
    if proj_content:
        truncated = truncate_index_content(proj_content)
        parts.append(f"[Project memories]\n{truncated}")

    if not parts:
        return ""

    body = "\n\n".join(parts)
    if include_guidance:
        return f"{MEMORY_SYSTEM_PROMPT}\n\n## MEMORY.md\n{body}"
    return body


# ── Relevant memory finder ─────────────────────────────────────────────────

def find_relevant_memories(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """Find memories relevant to a query via keyword matching.

    Returns:
        List of dicts with keys: name, description, type, scope, content,
        file_path, mtime_s, freshness_text, confidence, source
    """
    keyword_results = search_memory(query)
    if not keyword_results:
        return []

    headers = scan_all_memories()
    path_to_mtime = {h.file_path: h.mtime_s for h in headers}

    results = []
    for entry in keyword_results[:max_results * 3]:
        mtime_s = path_to_mtime.get(entry.file_path, 0)
        results.append({
            "name": entry.name,
            "description": entry.description,
            "type": entry.type,
            "scope": entry.scope,
            "content": entry.content,
            "file_path": entry.file_path,
            "mtime_s": mtime_s,
            "freshness_text": memory_freshness_text(mtime_s),
            "confidence": entry.confidence,
            "source": entry.source,
        })
    results.sort(key=lambda r: r["mtime_s"], reverse=True)
    return results[:max_results]
