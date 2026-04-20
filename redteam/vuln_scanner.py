# redteam/vuln_scanner.py
# Wraps standard authorized tools: nmap, nikto, nuclei

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redteam.scope import ScopeEnforcer

class VulnScanner:
    def __init__(self, scope: "ScopeEnforcer"):
        self.scope = scope

    def _check(self, target: str):
        if not self.scope.is_authorized(target):
            raise PermissionError(f"Out of scope: {target}")

    def nmap_service_scan(self, host: str) -> str:
        self._check(host)
        result = subprocess.run(
            ["nmap", "-sV", "-O", "--open", host],
            capture_output=True, text=True, timeout=120
        )
        self.scope.audit_log("nmap_service_scan", host, "ok")
        return result.stdout

    def nuclei_scan(self, target: str, templates: str = "cves/") -> str:
        self._check(target)
        result = subprocess.run(
            ["nuclei", "-u", target, "-t", templates, "-silent"],
            capture_output=True, text=True, timeout=300
        )
        self.scope.audit_log("nuclei_scan", target, "ok")
        return result.stdout
