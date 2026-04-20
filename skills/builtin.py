# skills/builtin.py
"""
Built-in skills that ship with JARVIS MK37.
Importing this module registers all built-in skills into the loader.
"""
from __future__ import annotations
from skills.loader import SkillDef, register_builtin_skill


# ── /commit ────────────────────────────────────────────────────────────────

_COMMIT_PROMPT = """\
Review the current git state and create a well-structured commit.

## Steps

1. Run `git status` and `git diff --staged` to see what is staged.
   - If nothing is staged, run `git diff` to see unstaged changes, then stage relevant files.
2. Analyze the changes:
   - Summarize the nature of the change (feature, bug fix, refactor, docs, etc.)
   - Write a concise commit title (≤72 chars) focusing on *why*, not just *what*.
   - If multiple logical changes exist, ask the user whether to split them.
3. Create the commit:
   ```
   git commit -m "<title>"
   ```
   If additional context is needed, add a body separated by a blank line.
4. Print the commit hash and summary when done.

**Rules:**
- Never use `--no-verify`.
- Never commit files that likely contain secrets (.env, credentials, keys).
- Prefer imperative mood in the title: "Add X", "Fix Y", "Refactor Z".

User context: $ARGUMENTS
"""

_REVIEW_PROMPT = """\
Review the code or pull request and provide structured feedback.

## Steps

1. Understand the scope:
   - If a PR number or URL is given in $ARGUMENTS, use `gh pr view $ARGUMENTS --patch` to get the diff.
   - Otherwise, use `git diff main...HEAD` (or `git diff HEAD~1`) for local changes.
2. Analyze the diff:
   - Correctness: Are there bugs, edge cases, or logic errors?
   - Security: Injection, auth issues, exposed secrets, unsafe operations?
   - Performance: N+1 queries, unnecessary allocations, blocking calls?
   - Style: Does it follow existing conventions in the codebase?
   - Tests: Are new behaviors tested? Do existing tests cover the change?
3. Write a structured review:
   ```
   ## Summary
   One-line overview of what the change does.

   ## Issues
   - [CRITICAL/MAJOR/MINOR] Description and location

   ## Suggestions
   - Nice-to-have improvements

   ## Verdict
   APPROVE / REQUEST CHANGES / COMMENT
   ```
4. If changes are needed, list specific file:line references.

User context: $ARGUMENTS
"""

_EDIT_PROMPT = """\
You are an expert code editor. Edit files precisely as instructed.

## Task
$ARGUMENTS

## Rules
1. Read the target file first to understand its structure.
2. Make minimal, targeted changes — do NOT rewrite entire files.
3. Preserve all existing comments and formatting unrelated to your change.
4. After editing, verify the file is syntactically valid.
5. If editing Python, ensure PEP 8 compliance.
6. If editing JS/TS, ensure no syntax errors.
7. Report exactly what you changed and why.

## Available actions
- Use file_read to read the current content
- Use file_write to write the updated content
- Use run_code to validate syntax if needed
"""

_PC_CONTROL_PROMPT = """\
You are a PC automation specialist. Control the user's computer as instructed.

## Task
$ARGUMENTS

## Available actions
- cursor_move: Move mouse to coordinates (x, y)
- cursor_click: Click at position (left/right/double)
- keyboard_type: Type text at cursor position
- keyboard_hotkey: Key combinations (e.g., ctrl+c, alt+tab)
- keyboard_press: Single key press (enter, tab, escape, etc.)
- screen_find: AI-powered element finder (describe what to find)
- screen_click: Find and click an element by description
- clipboard_read / clipboard_write: Clipboard operations
- focus_window: Bring a window to the foreground
- take_screenshot: Capture the screen

## Rules
1. Always take a screenshot first to understand the current screen state.
2. Use screen_find to locate elements before clicking.
3. Add small waits between rapid actions to let the UI update.
4. Report what you did at each step.
"""

_WEB_RESEARCH_PROMPT = """\
Conduct thorough web research on the given topic and provide a comprehensive summary.

## Topic
$ARGUMENTS

## Steps
1. Search the web for the topic using multiple relevant queries.
2. Fetch and read the most promising results.
3. Synthesize the information into a well-structured report:
   - Overview / Definition
   - Key findings / Facts
   - Sources cited with URLs
4. If the user wants the results saved, write them to a file.

## Rules
- Use at least 2-3 different search queries to get comprehensive coverage.
- Cross-reference facts across multiple sources.
- Clearly separate facts from opinions.
- Always cite sources.
"""


def _register_builtins() -> None:
    """Register all built-in skills."""

    register_builtin_skill(SkillDef(
        name="commit",
        description="Review staged changes and create a well-structured git commit",
        triggers=["/commit"],
        tools=["run_code", "file_read"],
        prompt=_COMMIT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to commit changes. Triggers: '/commit', 'commit changes'.",
        argument_hint="[optional context]",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="review",
        description="Review code changes or a pull request and provide structured feedback",
        triggers=["/review", "/review-pr"],
        tools=["run_code", "file_read", "web_search"],
        prompt=_REVIEW_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants a code review. Triggers: '/review', '/review-pr'.",
        argument_hint="[PR number or URL]",
        arguments=["pr"],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="edit",
        description="Precisely edit files in the workspace with minimal changes",
        triggers=["/edit"],
        tools=["file_read", "file_write", "run_code"],
        prompt=_EDIT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to edit a specific file or make code changes.",
        argument_hint="<file path> <what to change>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="pc_control",
        description="Control mouse, keyboard, and screen elements on the user's PC",
        triggers=["/pc", "/control"],
        tools=["cursor_move", "cursor_click", "keyboard_type", "keyboard_hotkey",
               "keyboard_press", "screen_find", "screen_click", "take_screenshot",
               "focus_window", "clipboard_read", "clipboard_write"],
        prompt=_PC_CONTROL_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to automate mouse/keyboard/screen interactions.",
        argument_hint="<what to do on screen>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="research",
        description="Deep web research with multi-query coverage and source citations",
        triggers=["/research", "/web-research"],
        tools=["web_search", "fetch_page", "fetch_raw", "file_write"],
        prompt=_WEB_RESEARCH_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants comprehensive research on a topic.",
        argument_hint="<topic to research>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))


_register_builtins()
