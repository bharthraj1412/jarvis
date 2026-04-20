# config/models.py
"""
Centralized model configuration for JARVIS MK37.

Priority order (highest wins):
  1. Environment variables  (JARVIS_MODEL_CLAUDE, JARVIS_MODEL_GEMINI, etc.)
  2. config/models.json     (edit once, applies everywhere)
  3. Hardcoded defaults     (safe fallbacks)

Usage:
    from config.models import get_model_config
    cfg = get_model_config()
    cfg["claude"]         # → "claude-sonnet-4-20250514"
    cfg["voice_live"]     # → "models/gemini-2.5-flash"
    cfg["default_backend"]# → "gemini"
"""

import os
import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent
_MODELS_JSON = _CONFIG_DIR / "models.json"

# ── Hardcoded defaults (safe fallbacks) ───────────────────────────────────────
_DEFAULTS = {
    "voice_live": "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "voice_name": "Charon",

    "claude":  "claude-sonnet-4-20250514",
    "gpt":     "gpt-4o",
    "gemini":  "gemini-2.5-flash",
    "ollama":  "llama3",
    "nvidia":  "meta/llama-3.1-70b-instruct",
    "mistral": "mistral-large-latest",

    "default_backend": "gemini",
}

# ── Env var mapping ───────────────────────────────────────────────────────────
_ENV_MAP = {
    "JARVIS_MODEL_CLAUDE":    "claude",
    "JARVIS_MODEL_GPT":       "gpt",
    "JARVIS_MODEL_GEMINI":    "gemini",
    "JARVIS_MODEL_OLLAMA":    "ollama",
    "JARVIS_MODEL_NVIDIA":    "nvidia",
    "JARVIS_MODEL_MISTRAL":   "mistral",
    "JARVIS_MODEL_VOICE":     "voice_live",
    "JARVIS_VOICE_NAME":      "voice_name",
    "JARVIS_DEFAULT_BACKEND": "default_backend",
}

_cache: dict | None = None


def get_model_config(force_reload: bool = False) -> dict:
    """
    Load model configuration with priority: env > models.json > defaults.
    Results are cached after first call unless force_reload=True.
    """
    global _cache
    if _cache is not None and not force_reload:
        return _cache.copy()

    # Start with defaults
    config = dict(_DEFAULTS)

    # Layer 2: models.json overrides
    if _MODELS_JSON.exists():
        try:
            with open(_MODELS_JSON, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            for key, value in json_data.items():
                if not key.startswith("_") and isinstance(value, str) and value.strip():
                    config[key] = value.strip()
        except Exception as e:
            print(f"[Config] Warning: Could not read models.json: {e}")

    # Layer 3: Environment variable overrides (highest priority)
    for env_key, config_key in _ENV_MAP.items():
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            config[config_key] = env_val

    # Also check OLLAMA_DEFAULT_MODEL for backward compatibility
    ollama_model = os.environ.get("OLLAMA_DEFAULT_MODEL", "").strip()
    if ollama_model:
        config["ollama"] = ollama_model

    _cache = config
    return config.copy()


def get_model(backend: str) -> str:
    """Shortcut: get the model name for a specific backend."""
    return get_model_config().get(backend, _DEFAULTS.get(backend, ""))


def print_config():
    """Print current model configuration for debugging."""
    cfg = get_model_config()
    print("=" * 50)
    print("  JARVIS MK37 — Model Configuration")
    print("=" * 50)
    for key, value in sorted(cfg.items()):
        source = "default"
        # Check if it came from env
        for env_key, config_key in _ENV_MAP.items():
            if config_key == key and os.environ.get(env_key, "").strip():
                source = f"env ({env_key})"
                break
        # Check if it came from models.json
        if source == "default" and _MODELS_JSON.exists():
            try:
                with open(_MODELS_JSON, "r", encoding="utf-8") as f:
                    if key in json.load(f):
                        source = "models.json"
            except Exception:
                pass
        print(f"  {key:20s} = {value:40s} [{source}]")
    print("=" * 50)
