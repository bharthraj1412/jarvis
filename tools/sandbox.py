# tools/sandbox.py
"""
Code sandbox for JARVIS MK37.
Executes code in a subprocess with timeout protection.
Cross-platform: Windows, Linux, macOS.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import os
import platform

_OS = platform.system()


class CodeSandbox:
    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def run(self, code: str, lang: str = "python", timeout: int = 30) -> dict:
        if lang not in self.ALLOWED_LANGS:
            return {"error": f"Language '{lang}' not permitted. Allowed: {', '.join(sorted(self.ALLOWED_LANGS))}"}

        # bash and powershell availability checks
        if lang == "bash" and _OS == "Windows":
            # Try Git Bash or WSL, otherwise fall back to powershell hint
            pass  # still try — Git Bash may be installed
        if lang == "powershell" and _OS != "Windows":
            return {"error": "PowerShell is only available on Windows"}

        with tempfile.NamedTemporaryFile(
            suffix=self._ext(lang), mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            fname = f.name
        try:
            result = subprocess.run(
                self._cmd(lang, fname),
                capture_output=True, text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return {"stdout": result.stdout, "stderr": result.stderr,
                    "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"Execution timed out after {timeout}s"}
        except FileNotFoundError as e:
            return {"error": f"Runtime not found for '{lang}': {e}. Is it installed and on PATH?"}
        except Exception as e:
            return {"error": f"Execution error: {e}"}
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _ext(self, lang):
        return {
            "python": ".py",
            "javascript": ".js",
            "bash": ".sh",
            "powershell": ".ps1",
        }[lang]

    def _cmd(self, lang, f):
        return {
            "python": [sys.executable, f],       # always use the current Python
            "javascript": ["node", f],
            "bash": ["bash", f],
            "powershell": ["powershell", "-ExecutionPolicy", "Bypass", "-File", f],
        }[lang]
