# redteam/scope.py
from __future__ import annotations

import json
import os
from pathlib import Path
from ipaddress import ip_network, ip_address

class ScopeEnforcer:
    def __init__(self, scope_file: str):
        with open(scope_file, encoding="utf-8") as f:
            self.scope = json.load(f)
        # Expected keys: client, engagement_id, allowed_ips, allowed_domains,
        #                excluded_ips, start_date, end_date, rules_of_engagement

    def is_authorized(self, target: str) -> bool:
        for cidr in self.scope.get("allowed_ips", []):
            try:
                if ip_address(target) in ip_network(cidr, strict=False):
                    return True
            except ValueError:
                pass
        for domain in self.scope.get("allowed_domains", []):
            if target == domain or target.endswith(f".{domain}"):
                return True
        return False

    def audit_log(self, action: str, target: str, result: str):
        entry = {"action": action, "target": target, "result": result}
        log_path = Path.home() / ".jarvis" / "audit.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
