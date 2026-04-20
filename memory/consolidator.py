# memory/consolidator.py
"""
Memory consolidator: extract long-term insights from completed sessions.
Ported from the Claude Code collection for JARVIS MK37.

Called on /quit or programmatically after a session.
Uses a lightweight AI call to identify preferences, feedback, and project
decisions worth promoting to persistent memory.

Design principles:
  - Hard cap of 3 memories per session to avoid noise accumulation
  - Auto-extracted memories start at 0.8 confidence
  - Won't overwrite a higher-confidence existing memory
  - Skips short sessions (< MIN_MESSAGES_TO_CONSOLIDATE turns)
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime

MIN_MESSAGES_TO_CONSOLIDATE = 8

_SYSTEM = """\
You are a memory consolidation assistant. Analyze the conversation below and extract
insights that are worth storing as persistent memories for future sessions.

Focus ONLY on:
1. New user preferences or working-style corrections revealed in this session
2. Project decisions or facts made explicit (NOT derivable from code/git)
3. Behavioral feedback given to the AI (what to do or avoid, and why)

Return a JSON object with key "memories" containing a list of objects, each with:
  "name":        short slug, e.g. "user_prefers_concise_responses"
  "type":        "user" | "feedback" | "project"
  "description": one-line description (used for search relevance)
  "content":     memory body
  "confidence":  float 0.0–1.0 (use ~0.8 for inferred, ~0.9 for clearly stated)

Return {"memories": []} if nothing new or worth saving.

Do NOT extract:
- Code patterns, architecture, file paths — derivable from the codebase
- Git history or debugging fixes — already in commits
- Ephemeral task state or tool results

Keep to AT MOST 3 memories. Quality over quantity."""


def consolidate_session(messages: list, router=None) -> list[str]:
    """Analyze a session's messages and extract memories worth keeping.

    Args:
        messages: the conversation message list
        router:   AgentRouter instance (to call an LLM)

    Returns:
        List of memory names that were saved. Empty list on skip or error.
    """
    if len(messages) < MIN_MESSAGES_TO_CONSOLIDATE:
        return []

    if router is None:
        return []

    try:
        from memory.persistent_store import MemoryEntry, save_memory, check_conflict

        # Build condensed transcript from the last 40 messages
        recent = messages[-40:]
        parts: list[str] = []
        for m in recent:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                prefix = "User" if role == "user" else "Assistant"
                snippet = content[:600].replace("\n", " ")
                parts.append(f"{prefix}: {snippet}")

        if not parts:
            return []

        transcript = "\n".join(parts)

        # Use the router's default backend for consolidation
        consolidation_messages = [
            {"role": "user", "content": f"Conversation:\n\n{transcript}"}
        ]

        try:
            result_text = router.run(
                router.default,
                consolidation_messages,
                _SYSTEM,
            )
        except Exception:
            return []

        if not result_text:
            return []

        # Parse JSON from the response
        # Strip markdown code blocks if present
        import re
        clean = re.sub(r"```(?:json)?", "", result_text).strip().rstrip("`").strip()
        parsed = json.loads(clean)
        memories_data = parsed.get("memories", [])
        if not isinstance(memories_data, list):
            return []

        saved: list[str] = []
        for m in memories_data[:3]:  # hard cap
            required = ("name", "type", "description", "content")
            if not all(k in m for k in required):
                continue

            entry = MemoryEntry(
                name=str(m["name"]),
                description=str(m["description"]),
                type=str(m.get("type", "user")),
                content=str(m["content"]),
                created=datetime.now().strftime("%Y-%m-%d"),
                confidence=float(m.get("confidence", 0.8)),
                source="consolidator",
            )

            # Don't overwrite a more confident existing memory
            conflict = check_conflict(entry, scope="user")
            if conflict and conflict["existing_confidence"] >= entry.confidence:
                continue

            save_memory(entry, scope="user")
            saved.append(entry.name)

        return saved

    except Exception:
        traceback.print_exc()
        return []
