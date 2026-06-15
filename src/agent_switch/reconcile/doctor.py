from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agent_switch.ccswitch.db import CcSwitchDataError, CcSwitchDb, CcSwitchSchemaError
from agent_switch.config.model import AgentConfig
from agent_switch.mcp.specs import desired_specs_for_app, mcp_spec_for_tool
from agent_switch.mcp.wrappers import wrapper_health
from agent_switch.paths import AgentPaths
from agent_switch.reconcile.planner import PlanChange
from agent_switch.renderers.claude import render_claude_config
from agent_switch.renderers.claude_desktop import render_claude_desktop_config
from agent_switch.renderers.codex import render_codex_config
from agent_switch.renderers.common import RenderError
from agent_switch.renderers.hermes import render_hermes_config
from agent_switch.security.redaction import redact_mapping, redact_text
from agent_switch.security.secrets import SecretReport, check_secrets


Renderer = Callable[[str, dict[str, dict[str, object]]], str]


@dataclass(frozen=True)
class DoctorFinding:
    severity: str
    target: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "target": self.target, "message": redact_text(self.message)}


@dataclass(frozen=True)
class DoctorReport:
    findings: tuple[DoctorFinding, ...]
    changes: tuple[PlanChange, ...]
    secret_report: SecretReport

    @property
    def drift_count(self) -> int:
        return len(self.changes)

    @property
    def blocked(self) -> bool:
        return any(finding.severity == "error" for finding in self.findings)

    def to_dict(self) -> dict[str, object]:
        return redact_mapping(
            {
                "blocked": self.blocked,
                "driftCount": self.drift_count,
                "findings": [finding.to_dict() for finding in self.findings],
                "changes": [change.to_dict() for change in self.changes],
                "secrets": self.secret_report.to_dict(),
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _check_target(
    target: str,
    path: Path,
    renderer: Renderer,
    desired: dict[str, dict[str, object]],
    findings: list[DoctorFinding],
    changes: list[PlanChange],
) -> None:
    current = _read_text(path)
    try:
        rendered = renderer(current, desired)
    except RenderError as exc:
        findings.append(DoctorFinding("error", target, str(exc)))
        return
    if rendered != current:
        action = "create" if not path.exists() else "update"
        changes.append(PlanChange(target, path, action, f"{target} agent-owned MCP projection differs"))


def run_doctor(config: AgentConfig, paths: AgentPaths, *, include_ccswitch: bool = True) -> DoctorReport:
    findings: list[DoctorFinding] = []
    changes: list[PlanChange] = []

    secret_report = check_secrets(config)
    if secret_report.missing:
        findings.append(
            DoctorFinding(
                "warning",
                "secrets",
                "missing required secret name(s): " + ", ".join(secret_report.missing),
            )
        )

    for item in wrapper_health(config, paths.wrapper_dir):
        if not item.ok():
            changes.append(PlanChange("wrappers", item.path, "write", f"wrapper for {item.tool_id} is missing or not executable"))

    target_specs = {
        "claude": (paths.claude_config, render_claude_config),
        "claude_desktop": (paths.claude_desktop_config, render_claude_desktop_config),
        "codex": (paths.codex_config, render_codex_config),
        "hermes": (paths.hermes_config, render_hermes_config),
    }
    for app, (path, renderer) in target_specs.items():
        _check_target(app, path, renderer, desired_specs_for_app(config, app, paths.wrapper_dir), findings, changes)

    if include_ccswitch:
        db = CcSwitchDb(paths.ccswitch_db)
        if paths.ccswitch_db.exists():
            try:
                rows = db.list_mcp_servers()
                for tool in config.tools:
                    desired = mcp_spec_for_tool(tool, paths.wrapper_dir)
                    row = rows.get(tool.id)
                    if row is None or row.server_config != desired or row.apps != tool.apps:
                        changes.append(PlanChange("ccswitch", paths.ccswitch_db, "upsert", f"mirror MCP row {tool.id}"))
            except (CcSwitchDataError, CcSwitchSchemaError, OSError) as exc:
                findings.append(DoctorFinding("error", "ccswitch", str(exc)))
        else:
            findings.append(DoctorFinding("info", "ccswitch", "CC Switch database not found; skipping database mirror"))

    return DoctorReport(tuple(findings), tuple(changes), secret_report)
