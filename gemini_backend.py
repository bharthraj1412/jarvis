# gemini_backend.py
"""Gemini backend using the modern google.genai SDK."""
from __future__ import annotations

import os
from google import genai
from config.models import get_model

class GeminiBackend:
    def __init__(self, model=None):
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")
        self.client = genai.Client(api_key=api_key)
        self.model = model or get_model("gemini")

    def complete(self, messages: list, system: str = "") -> str:
        # Build the contents list for the Gemini API
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        config = {}
        if system:
            config["system_instruction"] = system

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text
