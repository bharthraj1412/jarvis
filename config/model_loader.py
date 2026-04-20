# config/model_loader.py
"""
Central model configuration loader for JARVIS MK37.
Reads config/models.json and provides defaults if it doesn't exist.
"""

import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent
_MODELS_FILE = _CONFIG_DIR / "models.json"

DEFAULTS = {
    "voice_live": "models/gemini-2.5-flash",
    "voice_name": "Charon",
    "claude": "claude-sonnet-4-20250514",
    "gpt": "gpt-4o",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3",
    "nvidia": "meta/llama-3.1-70b-instruct",
    "default_backend": "claude",
}


def load_models() -> dict:
    """
    Load model configuration from config/models.json.
    Creates the file with defaults if it doesn't exist.
    """
    if not _MODELS_FILE.exists():
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _MODELS_FILE.write_text(
            json.dumps(DEFAULTS, indent=4),
            encoding="utf-8",
        )
        print(f"[CONFIG] Created default models.json at {_MODELS_FILE}")
        return DEFAULTS.copy()

    try:
        data = json.loads(_MODELS_FILE.read_text(encoding="utf-8"))
        # Merge with defaults so new keys are always present
        merged = {**DEFAULTS, **data}
        return merged
    except Exception as e:
        print(f"[CONFIG] Error reading models.json: {e} — using defaults")
        return DEFAULTS.copy()


def save_models(models: dict):
    """Save updated model configuration back to disk."""
    # Remove internal comment keys
    clean = {k: v for k, v in models.items() if not k.startswith("_")}
    clean["_comment"] = "Edit this file to change models. JARVIS reads it on every boot."
    _MODELS_FILE.write_text(
        json.dumps(clean, indent=4),
        encoding="utf-8",
    )


# Module-level convenience: load once on import
MODELS = load_models()
