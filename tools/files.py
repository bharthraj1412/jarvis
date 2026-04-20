# tools/files.py
from pathlib import Path

class FileManager:
    def __init__(self, workspace: str = "./workspace"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(exist_ok=True)

    def _safe(self, path: str) -> Path:
        p = (self.workspace / path).resolve()
        if not str(p).startswith(str(self.workspace.resolve())):
            raise PermissionError("Path escapes workspace")
        return p

    def read(self, path: str) -> str:
        return self._safe(path).read_text(encoding="utf-8")

    def write(self, path: str, content: str):
        p = self._safe(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list_dir(self, path: str = ".") -> list:
        return [str(f) for f in self._safe(path).iterdir()]

    def delete(self, path: str):
        self._safe(path).unlink()
