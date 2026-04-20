# anthropic_backend.py
from __future__ import annotations

import anthropic
from config.models import get_model

class ClaudeBackend:
    def __init__(self, model=None):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = model or get_model("claude")

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": 8096,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def stream(self, messages: list, system: str = ""):
        with self.client.messages.stream(
            model=self.model,
            max_tokens=8096,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
