# memory/memory_types.py
"""
Memory type taxonomy and system-prompt guidance text.
Ported from the Claude Code collection for JARVIS MK37.

Four types capture context NOT derivable from the current project state.
"""

MEMORY_TYPES = ["user", "feedback", "project", "reference"]

MEMORY_TYPE_DESCRIPTIONS: dict[str, str] = {
    "user": (
        "Information about the user's role, goals, responsibilities, and knowledge. "
        "Helps tailor future behavior to the user's preferences."
    ),
    "feedback": (
        "Guidance the user has given about how to approach work — both what to avoid "
        "and what to keep doing. Lead with the rule, then **Why:** and **How to apply:**."
    ),
    "project": (
        "Ongoing work, goals, bugs, or incidents not derivable from code or git history. "
        "Lead with the fact/decision, then **Why:** and **How to apply:**. "
        "Always convert relative dates to absolute dates."
    ),
    "reference": (
        "Pointers to external systems (issue trackers, dashboards, docs, URLs)."
    ),
}

MEMORY_FORMAT_EXAMPLE = """\
```markdown
---
name: {{memory name}}
description: {{one-line description — used to decide relevance, so be specific}}
type: {{user | feedback | project | reference}}
---

{{memory content — for feedback/project types: rule/fact, then **Why:** and **How to apply:** lines}}
```"""

MEMORY_SYSTEM_PROMPT = """\
## Memory system

You have a persistent, file-based memory system. Memories are stored as markdown files with
YAML frontmatter. Build this up over time so future conversations have context about the user,
their preferences, and the work you're doing together.

**Types** (save only what cannot be derived from the codebase):
- **user** — role, goals, knowledge, preferences
- **feedback** — guidance on how to work (corrections AND confirmations)
- **project** — ongoing work, decisions, deadlines not in git history
- **reference** — pointers to external systems

**When to save**: If the user corrects you, confirms an approach, or shares context that should
persist beyond this conversation.

**Available tools**: memory_save, memory_delete, memory_search, memory_list

**What NOT to save**: code patterns, architecture, git history, debugging fixes,
or ephemeral task state.

**Before recommending from memory**: A memory naming a file or function may be stale.
Verify it still exists before acting on it.
"""
