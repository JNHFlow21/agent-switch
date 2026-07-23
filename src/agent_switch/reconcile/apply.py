from __future__ import annotations

from agent_switch.atomic import write_if_changed
from agent_switch.ccswitch.db import CcSwitchDb
from agent_switch.config.model import AgentConfig
from agent_switch.instructions import write_instructions
from agent_switch.mcp.specs import desired_specs_for_app, mcp_spec_for_tool
from agent_switch.mcp.wrappers import write_wrappers
from agent_switch.paths import AgentPaths
from agent_switch.reconcile.doctor import DoctorReport, run_doctor
from agent_switch.reconcile.state import ApplySummary
from agent_switch.renderers.claude import render_claude_config
from agent_switch.renderers.claude_desktop import render_claude_desktop_config
from agent_switch.renderers.codex import render_codex_config
from agent_switch.renderers.hermes import render_hermes_config
from agent_switch.targets import detected_apps


def _ccswitch_apps_match(observed, desired) -> bool:
    return (
        observed.claude == desired.claude
        and observed.codex == desired.codex
        and observed.hermes == desired.hermes
    )


def _read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def apply_reconcile(config: AgentConfig, paths: AgentPaths, *, include_ccswitch: bool = True) -> tuple[ApplySummary, DoctorReport]:
    pre = run_doctor(config, paths, include_ccswitch=include_ccswitch)
    if pre.blocked:
        return ApplySummary(changed=0, unchanged=0, blocked=1), pre

    changed = 0
    unchanged = 0
    active_apps = detected_apps(paths)
    for result in write_instructions(paths, active_apps):
        changed += int(result.changed)
        unchanged += int(not result.changed)

    for result in write_wrappers(config, paths):
        changed += int(result.changed)
        unchanged += int(not result.changed)

    targets = (
        ("claude", paths.claude_config, render_claude_config),
        ("claude_desktop", paths.claude_desktop_config, render_claude_desktop_config),
        ("codex", paths.codex_config, lambda text, desired: render_codex_config(text, desired, paths.codex_instructions)),
        ("hermes", paths.hermes_config, render_hermes_config),
    )
    for app, path, renderer in targets:
        if app not in active_apps:
            continue
        desired = desired_specs_for_app(config, app, paths.wrapper_dir)
        rendered = renderer(_read(path), desired)
        result = write_if_changed(path, rendered, backup_dir=paths.backup_dir)
        changed += int(result.changed)
        unchanged += int(not result.changed)

    if include_ccswitch and paths.ccswitch_db.exists():
        db = CcSwitchDb(paths.ccswitch_db)
        rows = db.list_mcp_servers()
        enabled_ids = {
            tool.id
            for tool in config.tools
            if tool.enabled and (tool.apps.claude or tool.apps.codex or tool.apps.hermes)
        }
        for server_id in sorted(row_id for row_id in rows if row_id.startswith("agent-") and row_id not in enabled_ids):
            db.delete_agent_mcp_server(server_id)
            changed += 1
        for tool in config.tools:
            if not tool.enabled:
                continue
            if not (tool.apps.claude or tool.apps.codex or tool.apps.hermes):
                continue
            desired = mcp_spec_for_tool(tool, paths.wrapper_dir)
            row = rows.get(tool.id)
            if row is None or row.server_config != desired or not _ccswitch_apps_match(row.apps, tool.apps):
                db.upsert_agent_mcp_server(tool.id, tool.name, desired, tool.apps)
                changed += 1
            else:
                unchanged += 1

    post = run_doctor(config, paths, include_ccswitch=include_ccswitch)
    return ApplySummary(changed=changed, unchanged=unchanged), post
