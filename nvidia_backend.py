# nvidia_backend.py
from openai import OpenAI  # NIM uses OpenAI-compatible API
import os
from config.models import get_model

class NvidiaBackend:
    def __init__(self, model=None):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ["NVIDIA_API_KEY"],
        )
        self.model = model or get_model("nvidia")

    def complete(self, messages: list, system: str = "") -> str:
        all_messages = [{"role": "system", "content": system}] + messages
        response = self.client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content
