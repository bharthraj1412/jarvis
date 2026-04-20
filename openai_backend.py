# openai_backend.py
from __future__ import annotations

from openai import OpenAI
from config.models import get_model

class OpenAIBackend:
    def __init__(self, model=None):
        self.client = OpenAI()  # reads OPENAI_API_KEY from env
        self.model = model or get_model("gpt")

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        all_messages = [{"role": "system", "content": system}] + messages
        kwargs = {"model": self.model, "messages": all_messages}
        if tools:
            kwargs["tools"] = tools
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
