# core/compat.py
"""
Backward-compatible shim layer for JARVIS MK37.

Re-exports any renamed or moved symbols so existing skills/,
agents/, and markdown configuration files continue working
even after internal refactors.

Usage:
    from core.compat import *
"""
from __future__ import annotations

# ── Re-export core orchestration symbols ──────────────────────────────────
try:
    from orchestrator import JarvisOrchestrator
except ImportError:
    JarvisOrchestrator = None  # type: ignore[assignment,misc]

try:
    from router import AgentRouter, AgentProfile, ROUTING_RULES
except ImportError:
    AgentRouter = None  # type: ignore[assignment,misc]
    AgentProfile = None  # type: ignore[assignment,misc]
    ROUTING_RULES = {}

# ── Re-export memory symbols ─────────────────────────────────────────────
try:
    from memory.working import WorkingMemory
except ImportError:
    WorkingMemory = None  # type: ignore[assignment,misc]

try:
    from memory.persistent_store import (
        MemoryEntry,
        save_memory,
        delete_memory,
        load_entries,
        load_index,
        search_memory,
    )
except ImportError:
    MemoryEntry = None  # type: ignore[assignment,misc]
    save_memory = None  # type: ignore[assignment]
    delete_memory = None  # type: ignore[assignment]
    load_entries = None  # type: ignore[assignment]
    load_index = None  # type: ignore[assignment]
    search_memory = None  # type: ignore[assignment]

try:
    from memory.vector_store import VectorMemory
except ImportError:
    VectorMemory = None  # type: ignore[assignment,misc]

try:
    from memory.consolidator import consolidate_session
except ImportError:
    consolidate_session = None  # type: ignore[assignment]

try:
    from memory.memory_context import get_memory_context, find_relevant_memories
except ImportError:
    get_memory_context = None  # type: ignore[assignment]
    find_relevant_memories = None  # type: ignore[assignment]

# ── Re-export tool symbols ───────────────────────────────────────────────
try:
    from tools.registry import (
        TOOL_SCHEMAS,
        get_tool_prompt_block,
        parse_tool_call,
        execute_tool,
    )
except ImportError:
    TOOL_SCHEMAS = []
    get_tool_prompt_block = None  # type: ignore[assignment]
    parse_tool_call = None  # type: ignore[assignment]
    execute_tool = None  # type: ignore[assignment]

try:
    from tools.sandbox import CodeSandbox
except ImportError:
    CodeSandbox = None  # type: ignore[assignment,misc]

try:
    from tools.files import FileManager
except ImportError:
    FileManager = None  # type: ignore[assignment,misc]

# ── Re-export skills symbols ─────────────────────────────────────────────
try:
    from skills.loader import SkillDef, load_skills, find_skill, substitute_arguments
except ImportError:
    SkillDef = None  # type: ignore[assignment,misc]
    load_skills = None  # type: ignore[assignment]
    find_skill = None  # type: ignore[assignment]
    substitute_arguments = None  # type: ignore[assignment]

try:
    from skills.executor import execute_skill
except ImportError:
    execute_skill = None  # type: ignore[assignment]

# ── Re-export multi-agent symbols ────────────────────────────────────────
try:
    from multi_agent.subagent import (
        AgentDefinition,
        SubAgentTask,
        SubAgentManager,
        load_agent_definitions,
        get_agent_definition,
    )
except ImportError:
    AgentDefinition = None  # type: ignore[assignment,misc]
    SubAgentTask = None  # type: ignore[assignment,misc]
    SubAgentManager = None  # type: ignore[assignment,misc]
    load_agent_definitions = None  # type: ignore[assignment]
    get_agent_definition = None  # type: ignore[assignment]

# ── Re-export permissions ────────────────────────────────────────────────
try:
    from permissions import PERMISSIONS, PermissionPolicy, PermissionMode
except ImportError:
    PERMISSIONS = None  # type: ignore[assignment]
    PermissionPolicy = None  # type: ignore[assignment,misc]
    PermissionMode = None  # type: ignore[assignment,misc]

# ── Re-export history (new in MK37.1) ────────────────────────────────────
try:
    from history.session_store import SessionStore
except ImportError:
    SessionStore = None  # type: ignore[assignment,misc]

try:
    from history.audit_writer import write_audit
except ImportError:
    write_audit = None  # type: ignore[assignment]

# ── Re-export backends ───────────────────────────────────────────────────
try:
    from gemini_backend import GeminiBackend
except ImportError:
    GeminiBackend = None  # type: ignore[assignment,misc]

try:
    from anthropic_backend import ClaudeBackend
except ImportError:
    ClaudeBackend = None  # type: ignore[assignment,misc]

try:
    from openai_backend import OpenAIBackend
except ImportError:
    OpenAIBackend = None  # type: ignore[assignment,misc]

try:
    from ollama_backend import OllamaBackend
except ImportError:
    OllamaBackend = None  # type: ignore[assignment,misc]

try:
    from nvidia_backend import NvidiaBackend
except ImportError:
    NvidiaBackend = None  # type: ignore[assignment,misc]

try:
    from mistral_backend import MistralBackend
except ImportError:
    MistralBackend = None  # type: ignore[assignment,misc]

# ── Re-export config ─────────────────────────────────────────────────────
try:
    from config.models import get_model, get_model_config
except ImportError:
    get_model = None  # type: ignore[assignment]
    get_model_config = None  # type: ignore[assignment]


__all__ = [
    # Core
    "JarvisOrchestrator", "AgentRouter", "AgentProfile", "ROUTING_RULES",
    # Memory
    "WorkingMemory", "VectorMemory", "MemoryEntry",
    "save_memory", "delete_memory", "load_entries", "load_index", "search_memory",
    "consolidate_session", "get_memory_context", "find_relevant_memories",
    # Tools
    "TOOL_SCHEMAS", "get_tool_prompt_block", "parse_tool_call", "execute_tool",
    "CodeSandbox", "FileManager",
    # Skills
    "SkillDef", "load_skills", "find_skill", "substitute_arguments", "execute_skill",
    # Agents
    "AgentDefinition", "SubAgentTask", "SubAgentManager",
    "load_agent_definitions", "get_agent_definition",
    # Permissions
    "PERMISSIONS", "PermissionPolicy", "PermissionMode",
    # History
    "SessionStore", "write_audit",
    # Backends
    "GeminiBackend", "ClaudeBackend", "OpenAIBackend",
    "OllamaBackend", "NvidiaBackend", "MistralBackend",
    # Config
    "get_model", "get_model_config",
]
