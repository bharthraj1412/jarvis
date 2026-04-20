# redteam/report.py
# Generates professional pentest reports as markdown or PDF

from datetime import datetime

REPORT_TEMPLATE = """
# Penetration Test Report

**Client:** {client}
**Engagement ID:** {engagement_id}
**Date:** {date}
**Prepared by:** JARVIS MK37 / {operator}

---

## Executive Summary

{executive_summary}

---

## Scope

**In-scope targets:**
{scope_targets}

---

## Findings

{findings}

---

## Remediation Recommendations

{recommendations}

---

## Appendix: Tool Output

{appendix}
"""

def generate_report(data: dict) -> str:
    findings_md = ""
    for i, f in enumerate(data.get("findings", []), 1):
        findings_md += f"""
### Finding {i}: {f['title']}

- **Severity:** {f['severity']}
- **CVSS:** {f.get('cvss', 'N/A')}
- **Description:** {f['description']}
- **Evidence:** {f.get('evidence', 'N/A')}
- **Recommendation:** {f['recommendation']}
"""
    return REPORT_TEMPLATE.format(
        client=data.get("client", "CONFIDENTIAL"),
        engagement_id=data.get("engagement_id", "N/A"),
        date=datetime.now().strftime("%Y-%m-%d"),
        operator=data.get("operator", "Unknown"),
        executive_summary=data.get("executive_summary", ""),
        scope_targets="\n".join(data.get("scope_targets", [])),
        findings=findings_md,
        recommendations=data.get("recommendations", ""),
        appendix=data.get("appendix", ""),
    )
