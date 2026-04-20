# ollama_backend.py
import os
import requests
from config.models import get_model

class OllamaBackend:
    def __init__(self, model=None, host=None):
        self.model = model or get_model("ollama")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def complete(self, messages: list, system: str = "") -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
        }
        r = requests.post(f"{self.host}/api/chat", json=payload)
        return r.json()["message"]["content"]
