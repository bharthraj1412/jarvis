# router.py
from __future__ import annotations
"""
Agent router — selects the best LLM backend for each task based on keywords.
Falls back gracefully if a preferred backend is unavailable.
Default backend is read from config/models.json or JARVIS_DEFAULT_BACKEND env var.
"""
from enum import Enum


class AgentProfile(Enum):
    CLAUDE   = "claude"
    GPT      = "gpt"
    GEMINI   = "gemini"
    OLLAMA   = "ollama"
    NVIDIA   = "nvidia"
    MISTRAL  = "mistral"

ROUTING_RULES = {
    # Task keyword -> preferred backend
    "code":          AgentProfile.CLAUDE,
    "security":      AgentProfile.CLAUDE,
    "creative":      AgentProfile.GPT,
    "search":        AgentProfile.GEMINI,
    "local_private": AgentProfile.OLLAMA,
    "long_context":  AgentProfile.GEMINI,
    "gpu_inference": AgentProfile.NVIDIA,
    "fast_inference": AgentProfile.MISTRAL,
    "multilingual":  AgentProfile.MISTRAL,
}

# Map string -> enum for config
_PROFILE_MAP = {p.value: p for p in AgentProfile}


def _get_configured_default() -> AgentProfile:
    """Read default_backend from config system."""
    try:
        from config.models import get_model_config
        cfg = get_model_config()
        default_str = cfg.get("default_backend", "gemini").lower()
        return _PROFILE_MAP.get(default_str, AgentProfile.GEMINI)
    except Exception:
        return AgentProfile.GEMINI


class AgentRouter:
    def __init__(self, backends: dict):
        self.backends = backends
        # Read default from config (env > models.json > hardcoded)
        configured = _get_configured_default()
        # Only use it if the backend is actually loaded
        if configured in backends:
            self.default = configured
        elif backends:
            self.default = list(backends.keys())[0]
        else:
            self.default = AgentProfile.GEMINI

    def route(self, task_keywords: list[str]) -> AgentProfile:
        """Route to the best available backend for the given keywords."""
        for kw in task_keywords:
            if kw in ROUTING_RULES:
                preferred = ROUTING_RULES[kw]
                # Only route there if the backend is actually loaded
                if preferred in self.backends:
                    return preferred
        return self.default

    def run(self, profile: AgentProfile, messages: list, system: str = "") -> str:
        """Run a completion on the given backend profile."""
        if profile not in self.backends:
            raise RuntimeError(
                f"Backend '{profile.value}' is not available. "
                f"Active backends: {', '.join(p.value for p in self.backends)}"
            )
        backend = self.backends[profile]
        return backend.complete(messages, system)
