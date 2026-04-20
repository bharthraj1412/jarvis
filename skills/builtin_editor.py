# skills/builtin_editor.py
"""
Built-in editor skills for JARVIS MK37.
These skills combine the file tools with PC control to operate code editors
(VS Code, Cursor, etc.) autonomously.
"""
from __future__ import annotations
from skills.loader import SkillDef, register_builtin_skill


_EDITOR_OPEN_PROMPT = """\
Open a file in the user's code editor.

## Task
Open: $ARGUMENTS

## Steps
1. Determine the full file path. If relative, resolve from the workspace.
2. Try opening via CLI:
   - VS Code: `code <file_path>`
   - Cursor: `cursor <file_path>`
   - Fallback: use `start <file_path>` (Windows) or `open <file_path>` (Mac)
3. If CLI fails, use keyboard shortcut:
   - Focus the editor window
   - Ctrl+O (or Cmd+O on Mac) to open file dialog
   - Type the file path
   - Press Enter
4. Confirm the file is open by taking a screenshot if needed.
"""

_EDITOR_GOTO_PROMPT = """\
Navigate to a specific line or function in the current editor.

## Task
Go to: $ARGUMENTS

## Steps
1. Focus the editor window.
2. Use Ctrl+G (Go to Line) if a line number is given.
3. Use Ctrl+Shift+O (Go to Symbol) if a function/class name is given.
4. Use Ctrl+P then type the filename if a file is given.
5. Type the target and press Enter.
"""

_EDITOR_INSERT_PROMPT = """\
Insert code at the current cursor position in the editor.

## Task
Insert: $ARGUMENTS

## Steps
1. Focus the editor window.
2. Navigate to the target location (line number or after a specific function).
3. Position the cursor correctly.
4. Type or paste the code content.
5. Save the file with Ctrl+S.
6. Verify no syntax errors appear in the editor's status bar.
"""

_EDITOR_FIND_REPLACE_PROMPT = """\
Find and replace text in the current editor file.

## Task
$ARGUMENTS

## Steps
1. Focus the editor window.
2. Open Find and Replace with Ctrl+H.
3. Type the search text in the find field.
4. Tab to the replace field and type the replacement.
5. Click "Replace All" or use the appropriate keyboard shortcut.
6. Save the file with Ctrl+S.
7. Close the find dialog with Escape.
"""

_EDITOR_TERMINAL_PROMPT = """\
Run a command in the editor's integrated terminal.

## Task
Run: $ARGUMENTS

## Steps
1. Focus the editor window.
2. Open the integrated terminal with Ctrl+` (backtick).
3. If the terminal is already open, click on it to focus.
4. Type the command.
5. Press Enter to execute.
6. Wait for the command to complete.
7. Read the output from the terminal.
"""


def _register_editor_builtins() -> None:
    """Register all editor-related built-in skills."""

    register_builtin_skill(SkillDef(
        name="editor_open",
        description="Open a file in the code editor (VS Code, Cursor, etc.)",
        triggers=["/editor-open", "/open-in-editor"],
        tools=["run_code", "focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press"],
        prompt=_EDITOR_OPEN_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to open a file in their editor.",
        argument_hint="<file path>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="editor_goto",
        description="Navigate to a line or symbol in the code editor",
        triggers=["/editor-goto", "/goto"],
        tools=["focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press"],
        prompt=_EDITOR_GOTO_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to navigate to a specific line or function.",
        argument_hint="<line number or symbol name>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="editor_insert",
        description="Insert code at cursor position in the editor",
        triggers=["/editor-insert"],
        tools=["focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press",
               "clipboard_write"],
        prompt=_EDITOR_INSERT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to insert code at a specific location in the editor.",
        argument_hint="<code to insert>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="editor_replace",
        description="Find and replace text in the current editor file",
        triggers=["/editor-replace", "/find-replace"],
        tools=["focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press"],
        prompt=_EDITOR_FIND_REPLACE_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to find and replace text in the editor.",
        argument_hint="<find text> -> <replace text>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="editor_terminal",
        description="Run a command in the editor's integrated terminal",
        triggers=["/editor-terminal", "/terminal"],
        tools=["focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press",
               "take_screenshot"],
        prompt=_EDITOR_TERMINAL_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to run a command in the editor terminal.",
        argument_hint="<command to run>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))


_register_editor_builtins()
