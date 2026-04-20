# redteam/recon.py
# Uses only passive, publicly available data sources

import subprocess, socket, httpx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redteam.scope import ScopeEnforcer

class ReconEngine:
    def __init__(self, scope: "ScopeEnforcer"):
        self.scope = scope

    def _check(self, target: str):
        if not self.scope.is_authorized(target):
            raise PermissionError(f"Target {target} is out of scope")

    def whois(self, domain: str) -> str:
        self._check(domain)
        result = subprocess.run(["whois", domain],
                                capture_output=True, text=True, timeout=10)
        self.scope.audit_log("whois", domain, "ok")
        return result.stdout

    def dns_enum(self, domain: str) -> dict:
        self._check(domain)
        records = {}
        for rtype in ["A", "MX", "NS", "TXT", "CNAME"]:
            try:
                result = subprocess.run(
                    ["nslookup", "-type=" + rtype, domain],
                    capture_output=True, text=True, timeout=5
                )
                records[rtype] = result.stdout.strip().splitlines()
            except Exception as e:
                records[rtype] = [str(e)]
        self.scope.audit_log("dns_enum", domain, "ok")
        return records

    def port_scan(self, host: str, ports: list[int] = None) -> dict:
        self._check(host)
        ports = ports or [22, 80, 443, 8080, 8443, 3389]
        open_ports = {}
        for port in ports:
            try:
                s = socket.socket()
                s.settimeout(1)
                s.connect((host, port))
                open_ports[port] = "open"
                s.close()
            except Exception:
                open_ports[port] = "closed"
        self.scope.audit_log("port_scan", host, str(open_ports))
        return open_ports

    def headers_audit(self, url: str) -> dict:
        self._check(url.split("/")[2] if "://" in url else url)
        r = httpx.get(url, follow_redirects=True, timeout=10)
        missing_security_headers = [
            h for h in [
                "Strict-Transport-Security", "X-Content-Type-Options",
                "X-Frame-Options", "Content-Security-Policy",
                "Referrer-Policy"
            ]
            if h not in r.headers
        ]
        self.scope.audit_log("headers_audit", url, "ok")
        return {
            "status": r.status_code,
            "headers": dict(r.headers),
            "missing_security_headers": missing_security_headers,
        }
