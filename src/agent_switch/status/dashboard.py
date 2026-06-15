from __future__ import annotations

import html

from agent_switch.reconcile.doctor import DoctorReport


def render_dashboard(report: DoctorReport) -> str:
    rows = "\n".join(
        f"<tr><td>{html.escape(change.target)}</td><td>{html.escape(change.action)}</td>"
        f"<td>{html.escape(str(change.path or ''))}</td><td>{html.escape(change.detail)}</td></tr>"
        for change in report.changes
    )
    findings = "\n".join(
        f"<li><strong>{html.escape(finding.severity)}</strong> {html.escape(finding.target)}: "
        f"{html.escape(finding.message)}</li>"
        for finding in report.findings
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Agent Switch Status</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
    .state {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Agent Switch Status</h1>
  <p class="state">{'Blocked' if report.blocked else 'Ready'} · drift changes: {report.drift_count}</p>
  <h2>Findings</h2>
  <ul>{findings or '<li>None</li>'}</ul>
  <h2>Planned Changes</h2>
  <table><thead><tr><th>Target</th><th>Action</th><th>Path</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>
</body>
</html>
"""

