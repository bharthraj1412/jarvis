# memory/working.py

class WorkingMemory:
    def __init__(self, max_tokens: int = 100_000):
        self.history: list[dict] = []
        self.max_tokens = max_tokens

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._trim()

    def _trim(self):
        # Rough token estimate: 1 token ~ 4 chars
        while sum(len(m["content"]) for m in self.history) / 4 > self.max_tokens:
            self.history.pop(0)

    def get(self) -> list[dict]:
        return self.history
