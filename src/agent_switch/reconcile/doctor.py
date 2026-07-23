from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agent_switch.ccswitch.db import CcSwitchDataError, CcSwitchDb, CcSwitchSchemaError
from agent_switch.config.model import AgentConfig
from agent_switch.instructions import (
    claude_instructions,
    codex_instructions,
    hermes_instructions,
    merge_managed_block,
)
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
from agent_switch.targets import detected_apps


Renderer = Callable[[str, dict[str, dict[str, object]]], str]


def _unpinned_npx_package(command: str, args: tuple[str, ...]) -> str | None:
    if Path(command).name not in {"npx", "npx.cmd"}:
        return None
    package = next((arg for arg in args if not arg.startswith("-")), None)
    if package is None:
        return None
    if package.startswith("@"):
        return package if "@" not in package[1:] else None
    return package if "@" not in package else None


def _ccswitch_apps_match(observed, desired) -> bool:
    return (
        observed.claude == desired.claude
        and observed.codex == desired.codex
        and observed.hermes == desired.hermes
    )


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


def _check_text_target(target: str, path: Path, desired: str, changes: list[PlanChange]) -> None:
    current = _read_text(path)
    if desired != current:
        action = "create" if not path.exists() else "update"
        changes.append(PlanChange(target, path, action, f"{target} managed instructions differ"))


def run_doctor(config: AgentConfig, paths: AgentPaths, *, include_ccswitch: bool = True) -> DoctorReport:
    findings: list[DoctorFinding] = []
    changes: list[PlanChange] = []
    active_apps = detected_apps(paths)

    secret_report = check_secrets(config)
    if secret_report.missing:
        findings.append(
            DoctorFinding(
                "warning",
                "secrets",
                "missing required secret name(s): " + ", ".join(secret_report.missing),
            )
        )

    for tool in config.tools:
        unpinned = _unpinned_npx_package(tool.command, tool.args)
        if unpinned:
            findings.append(
                DoctorFinding(
                    "warning",
                    tool.id,
                    f"npx package is not version-pinned: {unpinned}",
                )
            )

    for item in wrapper_health(config, paths.wrapper_dir):
        if not item.ok():
            changes.append(PlanChange("wrappers", item.path, "write", f"wrapper for {item.tool_id} is missing or not executable"))
    desired_wrapper_paths = {
        paths.wrapper_dir / tool.wrapper_name for tool in config.tools if tool.enabled
    }
    if paths.wrapper_dir.exists():
        for stale in sorted(paths.wrapper_dir.glob("mcp-*")):
            if stale.is_file() and stale not in desired_wrapper_paths:
                changes.append(PlanChange("wrappers", stale, "delete", "stale or disabled MCP wrapper"))

    if "codex" in active_apps:
        _check_text_target("instructions.codex", paths.codex_instructions, codex_instructions(paths), changes)
    if "claude" in active_apps:
        _check_text_target("instructions.claude", paths.claude_instructions, claude_instructions(paths), changes)
        _check_text_target(
            "instructions.claude_global",
            paths.claude_global_instructions,
            merge_managed_block(_read_text(paths.claude_global_instructions), claude_instructions(paths)),
            changes,
        )
    if "hermes" in active_apps:
        _check_text_target("instructions.hermes", paths.hermes_instructions, hermes_instructions(paths), changes)
        _check_text_target(
            "instructions.hermes_soul",
            paths.hermes_soul,
            merge_managed_block(_read_text(paths.hermes_soul), hermes_instructions(paths)),
            changes,
        )

    target_specs = {
        "claude": (paths.claude_config, render_claude_config),
        "claude_desktop": (paths.claude_desktop_config, render_claude_desktop_config),
        "codex": (paths.codex_config, lambda text, desired: render_codex_config(text, desired, paths.codex_instructions)),
        "hermes": (paths.hermes_config, render_hermes_config),
    }
    for app, (path, renderer) in target_specs.items():
        if app not in active_apps:
            continue
        _check_target(app, path, renderer, desired_specs_for_app(config, app, paths.wrapper_dir), findings, changes)

    if include_ccswitch:
        db = CcSwitchDb(paths.ccswitch_db)
        if paths.ccswitch_db.exists():
            try:
                rows = db.list_mcp_servers()
                enabled_ids = {
                    tool.id
                    for tool in config.tools
                    if tool.enabled and (tool.apps.claude or tool.apps.codex or tool.apps.hermes)
                }
                for server_id in sorted(row_id for row_id in rows if row_id.startswith("agent-") and row_id not in enabled_ids):
                    changes.append(PlanChange("ccswitch", paths.ccswitch_db, "delete", f"remove stale MCP row {server_id}"))
                for tool in config.tools:
                    if not tool.enabled:
                        continue
                    if not (tool.apps.claude or tool.apps.codex or tool.apps.hermes):
                        continue
                    desired = mcp_spec_for_tool(tool, paths.wrapper_dir)
                    row = rows.get(tool.id)
                    if row is None or row.server_config != desired or not _ccswitch_apps_match(row.apps, tool.apps):
                        changes.append(PlanChange("ccswitch", paths.ccswitch_db, "upsert", f"mirror MCP row {tool.id}"))
            except (CcSwitchDataError, CcSwitchSchemaError, OSError) as exc:
                findings.append(DoctorFinding("error", "ccswitch", str(exc)))
        else:
            findings.append(DoctorFinding("info", "ccswitch", "CC Switch database not found; skipping database mirror"))

    return DoctorReport(tuple(findings), tuple(changes), secret_report)
