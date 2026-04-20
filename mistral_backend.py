# mistral_backend.py
import os
from openai import OpenAI
from config.models import get_model

class MistralBackend:
    def __init__(self, model=None):
        api_key = os.environ.get("MISTRAL_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1") if api_key else None
        self.model = model or get_model("mistral") or "mistral-large-latest"

    def complete(self, messages: list, system: str = "", tools: list = None) -> str:
        if not self.client:
            return "Mistral API key not configured."
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "messages": full_messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def stream(self, messages: list, system: str = ""):
        if not self.client:
            yield "Mistral API key not configured."
            return
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        stream_res = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            stream=True
        )
        for chunk in stream_res:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
