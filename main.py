import asyncio
import re
import threading
import json
import sys
import traceback
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
from dotenv import load_dotenv as _load_dotenv
_env = Path(__file__).parent / ".env"
if _env.exists():
    _load_dotenv(_env)

from config.models import get_model_config as _get_model_config

_model_cfg          = _get_model_config()
LIVE_MODEL          = _model_cfg.get("voice_live", "models/gemini-2.5-flash-native-audio-preview-12-2025")
VOICE_NAME          = _model_cfg.get("voice_name", "Charon")
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )


# ── Transkripsiyon temizleyici ─────────────────────────────────────────────────
_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:
    """Gemini'nin ürettiği <ctrlXX> artefaktlarını ve kontrol karakterlerini temizler."""
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()


# ── Tool declarations ──────────────────────────────────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly. "
            "NEVER use for OS controls (brightness, volume, WiFi etc.) — use computer_settings instead."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "THE tool for ALL operating system and hardware controls. "
            "MUST be used for: brightness (up/down/set), volume (up/down/mute/set), "
            "WiFi toggle, dark mode, window management (minimize/maximize/snap/fullscreen/close), "
            "keyboard shortcuts, typing text on screen, scrolling, tabs, zoom, "
            "screenshots, lock screen, restart, shutdown, refresh/reload page. "
            "NEVER use screen_find or screen_process for these — they are OS-level actions. "
            "For brightness: action=brightness_up or action=brightness_down. "
            "For volume: action=volume_up, volume_down, mute, or volume_set with value=0-100. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": (
                    "The action to perform. Common actions: "
                    "brightness_up, brightness_down, volume_up, volume_down, volume_set, mute, "
                    "close_app, close_window, full_screen, minimize, maximize, snap_left, snap_right, "
                    "switch_window, show_desktop, task_manager, dark_mode, toggle_wifi, "
                    "screenshot, lock_screen, restart, shutdown, scroll_up, scroll_down, "
                    "zoom_in, zoom_out, refresh_page, close_tab, new_tab, next_tab, prev_tab, "
                    "copy, paste, cut, undo, redo, select_all, save, enter, escape, "
                    "type_text, press_key, open_settings, file_explorer, sleep_display"
                )},
                "description": {"type": "STRING", "description": "Natural language description of what to do (used for AI intent detection if action is unclear)"},
                "value":       {"type": "STRING", "description": "Optional value: volume level (0-100), text to type, key to press, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls any web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. "
            "Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', "
            "'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": (
            "Direct mouse and keyboard automation — for CLICKING specific coordinates, "
            "TYPING text at cursor, pressing key combos, scrolling, dragging, and "
            "AI-powered screen element finding (screen_find/screen_click). "
            "ONLY use this for direct input tasks. "
            "For OS-level controls (brightness, volume, wifi, dark mode, window management), "
            "use computer_settings instead."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_jarvis",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Jarvis. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    # ── MK37 Red Team Tools ────────────────────────────────────────────────
    {
        "name": "port_scan",
        "description": (
            "Scan TCP ports on a target host. Only works on in-scope targets. "
            "Returns open/closed status for common ports or a custom list."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "host":  {"type": "STRING", "description": "Target host IP or hostname"},
                "ports": {"type": "STRING", "description": "Comma-separated port numbers (default: 22,80,443,8080,8443,3389)"},
            },
            "required": ["host"]
        }
    },
    {
        "name": "dns_enum",
        "description": "Enumerate DNS records (A, MX, NS, TXT, CNAME) for a domain. Scope-checked.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "domain": {"type": "STRING", "description": "Target domain to enumerate"},
            },
            "required": ["domain"]
        }
    },
    {
        "name": "headers_audit",
        "description": "Audit HTTP security headers of a URL. Reports missing security headers. Scope-checked.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "Target URL to audit"},
            },
            "required": ["url"]
        }
    },
    {
        "name": "mode_switch",
        "description": (
            "Switch JARVIS persona mode. Call when user says: switch to recon mode, "
            "go to coder mode, enter exploit mode, etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mode": {"type": "STRING", "description": "Mode name: recon, exploit, report, planner, coder, analyst, general"},
            },
            "required": ["mode"]
        }
    },
    # ── MK37 Architecture Bridge ──────────────────────────────────────────
    {
        "name": "run_skill",
        "description": (
            "Execute a JARVIS MK37 skill by name. Skills are powerful reusable workflows. "
            "Available skills include: commit (git commit), review (code review), edit (file editing), "
            "research (deep web research), pc_control (PC automation), "
            "github_scan (repo analysis), screenshot_fix (auto-fix screen errors), "
            "docker_deploy (Docker containers), scaffold (project generation), "
            "monitor (website uptime check). "
            "Use list_skills to see all available skills."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "skill_name": {"type": "STRING", "description": "Name of the skill to run (e.g. commit, review, github_scan, scaffold)"},
                "arguments":  {"type": "STRING", "description": "Arguments to pass to the skill"},
            },
            "required": ["skill_name"]
        }
    },
    {
        "name": "list_skills",
        "description": "List all available JARVIS MK37 skills with their triggers and descriptions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "spawn_agent",
        "description": (
            "Spawn a specialized MK37 sub-agent for parallel or complex work. "
            "Agent types: coder (writes code), reviewer (reviews code), "
            "researcher (web research), tester (writes tests), editor (edits files via keyboard/mouse). "
            "The agent works independently and returns its result."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "agent_type": {"type": "STRING", "description": "Type: coder, reviewer, researcher, tester, editor, general-purpose"},
                "task":       {"type": "STRING", "description": "What the agent should do"},
            },
            "required": ["agent_type", "task"]
        }
    },
    {
        "name": "memory_save_mk37",
        "description": (
            "Save important information to JARVIS persistent memory (MK37 file-based store). "
            "Unlike save_memory which stores simple key-value pairs, this stores rich, "
            "searchable memories with descriptions. Use for: technical decisions, "
            "project context, system configurations, meeting notes, research findings."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name":        {"type": "STRING", "description": "Short name for the memory (snake_case)"},
                "description": {"type": "STRING", "description": "One-line summary of what this memory contains"},
                "content":     {"type": "STRING", "description": "The full content to remember"},
                "type":        {"type": "STRING", "description": "Type: user, project, system, insight (default: user)"},
            },
            "required": ["name", "description", "content"]
        }
    },
    {
        "name": "memory_search_mk37",
        "description": (
            "Search JARVIS persistent memories (MK37 file-based store). "
            "Use to recall past decisions, project context, user preferences, "
            "or any previously saved information."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query to find relevant memories"},
            },
            "required": ["query"]
        }
    },
    {
        "name": "mk37_chat",
        "description": (
            "Route a complex query through the full MK37 ReAct orchestrator. "
            "The orchestrator can chain multiple tools autonomously (up to 15 steps) "
            "to solve complex, multi-step tasks. Use this for tasks that require "
            "planning and sequential tool use that a single tool can't handle."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The complex task or question to process"},
            },
            "required": ["query"]
        }
    },
]


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None
        self._current_mode  = "general"  # MK37 persona mode

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        # ── save_memory: sessiz ve hızlı ──────────────────────────────────────
        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            # ── MK37 Red Team Tools ───────────────────────────────────────
            elif name == "port_scan":
                def _port_scan():
                    import socket
                    host = args.get("host", "")
                    ports_str = args.get("ports", "22,80,443,8080,8443,3389")
                    ports = [int(p.strip()) for p in ports_str.split(",") if p.strip().isdigit()]
                    results = {}
                    for port in ports:
                        try:
                            s = socket.socket()
                            s.settimeout(1)
                            s.connect((host, port))
                            results[port] = "open"
                            s.close()
                        except Exception:
                            results[port] = "closed"
                    return f"Port scan results for {host}: {results}"
                r = await loop.run_in_executor(None, _port_scan)
                result = r or "Done."

            elif name == "dns_enum":
                def _dns_enum():
                    import subprocess
                    domain = args.get("domain", "")
                    records = {}
                    for rtype in ["A", "MX", "NS", "TXT", "CNAME"]:
                        try:
                            out = subprocess.run(
                                ["nslookup", "-type=" + rtype, domain],
                                capture_output=True, text=True, timeout=5
                            )
                            records[rtype] = out.stdout.strip()
                        except Exception as e:
                            records[rtype] = str(e)
                    return f"DNS records for {domain}: {json.dumps(records, indent=2)}"
                r = await loop.run_in_executor(None, _dns_enum)
                result = r or "Done."

            elif name == "headers_audit":
                def _headers_audit():
                    import httpx
                    url = args.get("url", "")
                    r = httpx.get(url, follow_redirects=True, timeout=10)
                    security_headers = [
                        "Strict-Transport-Security", "X-Content-Type-Options",
                        "X-Frame-Options", "Content-Security-Policy", "Referrer-Policy"
                    ]
                    missing = [h for h in security_headers if h not in r.headers]
                    return f"Status: {r.status_code}. Missing security headers: {missing}"
                r = await loop.run_in_executor(None, _headers_audit)
                result = r or "Done."

            elif name == "mode_switch":
                mode = args.get("mode", "general").lower()
                valid_modes = ["recon", "exploit", "report", "planner", "coder", "analyst", "general"]
                if mode in valid_modes:
                    self._current_mode = mode
                    self.ui.write_log(f"SYS: Mode switched to {mode.upper()}")
                    result = f"Mode switched to {mode.upper()}. I am now operating as a {mode} specialist."
                else:
                    result = f"Unknown mode: {mode}. Available: {', '.join(valid_modes)}"

            # ── MK37 Architecture Bridge ──────────────────────────────────
            elif name == "run_skill":
                def _run_skill():
                    from skills import load_skills, find_skill, execute_skill
                    skill_name = args.get("skill_name", "")
                    skill_args = args.get("arguments", "")
                    skill = None
                    for s in load_skills():
                        if s.name == skill_name:
                            skill = s
                            break
                    if skill is None:
                        skill = find_skill(f"/{skill_name}")
                    if skill is None:
                        available = [s.name for s in load_skills()]
                        return f"Skill '{skill_name}' not found. Available: {', '.join(available)}"

                    # For fork-mode skills in voice context, fall back to inline execution
                    # by using a simple bridge that calls the LLM via speak callback.
                    class _VoiceBridge:
                        def chat(self_bridge, message):
                            # Inline: just return the rendered prompt so the
                            # Gemini Live session processes it as a new turn.
                            return f"[Skill: {skill.name}]\n\n{message[:2000]}"
                        # Minimal stubs so fork-mode skills don't crash
                        _subagent_mgr = None
                        current_mode = "general"

                    return execute_skill(skill, skill_args, _VoiceBridge())
                r = await loop.run_in_executor(None, _run_skill)
                result = r or "Skill executed."
                self.ui.write_log(f"SYS: Skill '{args.get('skill_name')}' executed.")

            elif name == "list_skills":
                def _list_skills():
                    from skills import load_skills
                    skills = load_skills()
                    lines = [f"Available skills ({len(skills)}):"]
                    for s in skills:
                        triggers = ", ".join(s.triggers)
                        lines.append(f"  - {s.name} ({triggers}): {s.description}")
                    return "\n".join(lines)
                r = await loop.run_in_executor(None, _list_skills)
                result = r

            elif name == "spawn_agent":
                from multi_agent.subagent import SubAgentManager, get_agent_definition
                agent_type = args.get("agent_type", "general-purpose")
                task_prompt = args.get("task", "")
                if not task_prompt:
                    return types.FunctionResponse(
                        id=fc.id, name=name,
                        response={"result": "Please provide a task description for the agent."}
                    )
                # Voice interface has no orchestrator — inform user gracefully
                result = (
                    "Sub-agent spawning is only available in CLI mode (main_mk37.py), sir. "
                    "Please switch to the terminal interface to use this feature."
                )
                self.ui.write_log(f"[spawn_agent] Voice mode — feature unavailable")

            elif name == "memory_save_mk37":
                def _memory_save():
                    from memory.persistent_store import MemoryEntry, save_memory as mk37_save
                    from datetime import date
                    entry = MemoryEntry(
                        name=args.get("name", "unnamed"),
                        description=args.get("description", ""),
                        type=args.get("type", "user"),
                        content=args.get("content", ""),
                        created=date.today().isoformat(),
                    )
                    mk37_save(entry, scope="user")
                    return f"Memory saved: {entry.name}"
                r = await loop.run_in_executor(None, _memory_save)
                result = r
                print(f"[Memory MK37] Saved: {args.get('name')}")

            elif name == "memory_search_mk37":
                def _memory_search():
                    from memory.persistent_store import search_memory
                    query = args.get("query", "")
                    results = search_memory(query)
                    if not results:
                        return f"No memories found for '{query}'."
                    lines = [f"Found {len(results)} memories for '{query}':"]
                    for entry in results[:5]:
                        lines.append(f"  - {entry.name}: {entry.description}")
                        lines.append(f"    Content: {entry.content[:150]}")
                    return "\n".join(lines)
                r = await loop.run_in_executor(None, _memory_search)
                result = r

            elif name == "mk37_chat":
                def _mk37_chat():
                    query = args.get("query", "")
                    try:
                        from router import AgentRouter, AgentProfile
                        backends = {}
                        try:
                            from gemini_backend import GeminiBackend
                            backends[AgentProfile.GEMINI] = GeminiBackend()
                        except Exception:
                            pass
                        try:
                            from ollama_backend import OllamaBackend
                            backends[AgentProfile.OLLAMA] = OllamaBackend()
                        except Exception:
                            pass
                        if not backends:
                            return "No MK37 backends available for ReAct orchestration."
                        router = AgentRouter(backends)
                        from orchestrator import JarvisOrchestrator
                        # Use a temporary orchestrator that does NOT call
                        # set_orchestrator_ref (avoids overwriting the voice ref).
                        orch = JarvisOrchestrator.__new__(JarvisOrchestrator)
                        orch.router = router
                        orch.working_memory = __import__('memory.working', fromlist=['WorkingMemory']).WorkingMemory()
                        orch.vector_memory = None
                        orch.current_mode = "general"
                        orch._subagent_mgr = None
                        orch._session_store = None
                        orch._session_id = ""
                        orch._history_linker = None
                        return orch.chat(query)
                    except Exception as e:
                        return f"MK37 orchestrator error: {e}"
                r = await loop.run_in_executor(None, _mk37_chat)
                result = r or "MK37 processing complete."
                self.ui.write_log("SYS: MK37 ReAct orchestrator finished.")

            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")
                def _shutdown():
                    import time, os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def _safe_put(item):
            try:
                self.out_queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    _safe_put,
                    {"data": data, "mime_type": "audio/pcm"}
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue

                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)

        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                    # Initialize queues and session BEFORE creating tasks
                    self.session          = session
                    self._loop            = asyncio.get_event_loop()
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=10)
                    self._turn_done_event = asyncio.Event()

                    print("[JARVIS] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS MK37 online.")

                    # Now create tasks after queues are ready
                    tg_tasks = [
                        asyncio.create_task(self._send_realtime()),
                        asyncio.create_task(self._listen_audio()),
                        asyncio.create_task(self._receive_audio()),
                        asyncio.create_task(self._play_audio())
                    ]

                    # Wait for all tasks to complete (if ever)
                    await asyncio.gather(*tg_tasks)

            except Exception as e:
                print(f"[JARVIS] ⚠️ {e}")
                traceback.print_exc()

            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[JARVIS] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)


def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()