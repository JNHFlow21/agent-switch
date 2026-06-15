from __future__ import annotations

from agent_switch.reconcile.doctor import DoctorReport


def human_report(report: DoctorReport) -> str:
    lines = [
        f"Agent Switch status: {'blocked' if report.blocked else 'ok'}",
        f"Drift changes: {report.drift_count}",
        f"Missing secrets: {', '.join(report.secret_report.missing) if report.secret_report.missing else 'none'}",
    ]
    for finding in report.findings:
        lines.append(f"- {finding.severity}: {finding.target}: {finding.message}")
    for change in report.changes:
        path = f" {change.path}" if change.path else ""
        lines.append(f"- change: {change.target}:{path} {change.action} {change.detail}")
    return "\n".join(lines) + "\n"

