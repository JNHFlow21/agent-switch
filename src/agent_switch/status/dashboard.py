from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from agent_switch.ccswitch.db import CcSwitchDb
from agent_switch.config.model import APP_NAMES, AgentConfig, ToolSpec
from agent_switch.mcp.wrappers import wrapper_health
from agent_switch.paths import AgentPaths
from agent_switch.reconcile.doctor import DoctorReport
from agent_switch.security.secrets import read_env_file


APP_LABELS = {
    "claude": "Claude Code",
    "claude_desktop": "Claude Desktop",
    "codex": "Codex",
    "hermes": "Hermes",
}


def _e(value: object) -> str:
    return html.escape(str(value))


def _badge(label: str, tone: str = "neutral") -> str:
    return f'<span class="badge {tone}">{_e(label)}</span>'


def _tool_enabled_apps(tool: ToolSpec) -> list[str]:
    if not tool.enabled:
        return []
    return [APP_LABELS[app] for app in APP_NAMES if getattr(tool.apps, app)]


def _route_roles(config: AgentConfig) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {tool.id: [] for tool in config.tools}
    if config.routes.search_default:
        roles.setdefault(config.routes.search_default, []).append("Search default")
    if config.routes.x_read_default:
        roles.setdefault(config.routes.x_read_default, []).append("X reader")
    if config.routes.x_read_fallback:
        roles.setdefault(config.routes.x_read_fallback, []).append("X fallback")
    return roles


def _secret_names(path: Path) -> list[str]:
    return sorted(read_env_file(path).keys())


def _target_state(report: DoctorReport, target: str) -> tuple[str, str]:
    if any(finding.target == target and finding.severity == "error" for finding in report.findings):
        return "Blocked", "bad"
    if any(change.target == target for change in report.changes):
        return "Drift", "warn"
    return "In sync", "good"


def _tool_rows(config: AgentConfig, paths: AgentPaths, report: DoctorReport) -> str:
    health = {item.tool_id: item for item in wrapper_health(config, paths.wrapper_dir)}
    roles = _route_roles(config)
    present = set(report.secret_report.present_names)
    missing = set(report.secret_report.missing)
    rows: list[str] = []
    for tool in config.tools:
        active_apps = _tool_enabled_apps(tool)
        enabled = bool(active_apps)
        wrapper = health.get(tool.id)
        if wrapper and wrapper.ok():
            wrapper_cell = _badge("Executable", "good")
        elif wrapper and wrapper.exists:
            wrapper_cell = _badge("Not executable", "warn")
        else:
            wrapper_cell = _badge("Missing", "bad" if enabled else "neutral")

        required = list(tool.required_secrets)
        missing_required = [name for name in required if name in missing]
        if not required:
            secret_cell = _badge("No required secret", "neutral")
        elif missing_required:
            secret_cell = _badge(f"Missing {len(missing_required)}", "bad")
        elif all(name in present for name in required):
            secret_cell = _badge(f"Present {len(required)}", "good")
        else:
            secret_cell = _badge("Unverified", "warn")

        rows.append(
            "<tr>"
            f"<td><strong>{_e(tool.name)}</strong><span class=\"muted block\">{_e(tool.id)}</span></td>"
            f"<td>{' '.join(_badge(role, 'route') for role in roles.get(tool.id, [])) or _badge('Tool', 'neutral')}</td>"
            f"<td>{' '.join(_badge(app, 'app') for app in active_apps) or _badge('Reserved', 'neutral')}</td>"
            f"<td>{secret_cell}<span class=\"muted block\">{_e(', '.join(required) if required else 'none')}</span></td>"
            f"<td>{wrapper_cell}<span class=\"muted block\">{_e(wrapper.path if wrapper else paths.wrapper_dir / tool.wrapper_name)}</span></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _app_rows(config: AgentConfig, paths: AgentPaths, report: DoctorReport, include_ccswitch: bool) -> str:
    target_paths = {
        "claude": paths.claude_config,
        "claude_desktop": paths.claude_desktop_config,
        "codex": paths.codex_config,
        "hermes": paths.hermes_config,
    }
    rows: list[str] = []
    for app in APP_NAMES:
        state, tone = _target_state(report, app)
        tools = [tool.id for tool in config.tools_for_app(app)]
        tool_details = ", ".join(_e(tool) for tool in tools) if tools else '<span class="muted">none</span>'
        rows.append(
            "<tr>"
            f"<td><strong>{_e(APP_LABELS[app])}</strong><span class=\"muted block\">{_e(target_paths[app])}</span></td>"
            f"<td>{_badge(state, tone)}</td>"
            f"<td>{tool_details}</td>"
            "</tr>"
        )

    if include_ccswitch:
        state, tone = _target_state(report, "ccswitch")
        mirror_tools = [tool.id for tool in config.tools if tool.apps.claude or tool.apps.codex or tool.apps.hermes]
        details = ", ".join(_e(tool) for tool in mirror_tools)
        try:
            if paths.ccswitch_db.exists():
                rows_in_db = CcSwitchDb(paths.ccswitch_db).list_mcp_servers()
                mirrored = [tool for tool in mirror_tools if tool in rows_in_db]
                details = ", ".join(_e(tool) for tool in mirrored) if mirrored else '<span class="muted">none</span>'
        except Exception:
            pass
        rows.append(
            "<tr>"
            f"<td><strong>CC Switch DB mirror</strong><span class=\"muted block\">{_e(paths.ccswitch_db)}</span></td>"
            f"<td>{_badge(state, tone)}</td>"
            f"<td>{details}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _findings(report: DoctorReport) -> str:
    if not report.findings:
        return '<div class="empty">No findings. All managed resources are healthy.</div>'
    return "\n".join(
        f'<div class="finding">{_badge(finding.severity, "bad" if finding.severity == "error" else "warn")}'
        f'<strong>{_e(finding.target)}</strong><span>{_e(finding.message)}</span></div>'
        for finding in report.findings
    )


def _changes(report: DoctorReport) -> str:
    if not report.changes:
        return '<div class="empty">No planned changes. Running reconcile now would be a no-op.</div>'
    rows = "\n".join(
        "<tr>"
        f"<td>{_e(change.target)}</td><td>{_e(change.action)}</td>"
        f"<td>{_e(change.path or '')}</td><td>{_e(change.detail)}</td>"
        "</tr>"
        for change in report.changes
    )
    return f"<table><thead><tr><th>Target</th><th>Action</th><th>Path</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>"


def render_dashboard(
    report: DoctorReport,
    config: AgentConfig,
    paths: AgentPaths,
    *,
    include_ccswitch: bool = True,
) -> str:
    active_tools = [tool for tool in config.tools if _tool_enabled_apps(tool)]
    stored_names = _secret_names(config.secret_file)
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    blocked_text = "Blocked" if report.blocked else "Ready"
    blocked_tone = "bad" if report.blocked else "good"
    covered_labels = [label for app, label in APP_LABELS.items() if config.tools_for_app(app)]
    if include_ccswitch and paths.ccswitch_db.exists():
        covered_labels.append("CC Switch")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Switch Status</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #667085;
      --line: #e4e7ec;
      --green: #087443;
      --green-bg: #e8f7ee;
      --amber: #b54708;
      --amber-bg: #fff3df;
      --red: #b42318;
      --red-bg: #fee4e2;
      --blue: #344ac1;
      --blue-bg: #eef2ff;
      --slate-bg: #f2f4f7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }}
    header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 22px;
    }}
    h1 {{ margin: 0; font-size: 30px; line-height: 1.15; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    .muted {{ color: var(--muted); }}
    .block {{ display: block; margin-top: 3px; overflow-wrap: anywhere; }}
    .topline {{ margin-top: 8px; color: var(--muted); }}
    .grid {{ display: grid; gap: 14px; }}
    .summary {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 16px; }}
    .two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    section, .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    section {{ padding: 18px; }}
    .metric {{ padding: 16px; min-height: 92px; }}
    .metric .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .metric .value {{ display: block; margin-top: 8px; font-size: 26px; font-weight: 750; line-height: 1.1; }}
    .metric .note {{ display: block; margin-top: 7px; color: var(--muted); }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 12px 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      margin: 0 5px 5px 0;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }}
    .good {{ color: var(--green); background: var(--green-bg); }}
    .warn {{ color: var(--amber); background: var(--amber-bg); }}
    .bad {{ color: var(--red); background: var(--red-bg); }}
    .route {{ color: var(--blue); background: var(--blue-bg); }}
    .app {{ color: #374151; background: #edf7f6; }}
    .neutral {{ color: #475467; background: var(--slate-bg); }}
    .empty {{
      border: 1px dashed var(--line);
      background: #fbfcfe;
      border-radius: 8px;
      padding: 14px;
      color: var(--muted);
    }}
    .finding {{ display: flex; gap: 8px; align-items: center; padding: 8px 0; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 0; }}
    code {{
      background: #f2f4f7;
      border: 1px solid #eaecf0;
      border-radius: 6px;
      padding: 2px 5px;
      font-size: 12px;
    }}
    @media (max-width: 860px) {{
      main {{ padding: 20px 14px 36px; }}
      header {{ display: block; }}
      .summary, .two {{ grid-template-columns: 1fr; }}
      table {{ table-layout: auto; }}
      th:nth-child(5), td:nth-child(5) {{ display: none; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Agent Switch Status</h1>
      <p class="topline">Generated { _e(generated_at) } · secrets and token-bearing URLs are never rendered.</p>
    </div>
    <div>{_badge(blocked_text, blocked_tone)} {_badge(f"{report.drift_count} drift changes", "good" if report.drift_count == 0 else "warn")}</div>
  </header>

  <div class="grid summary">
    <div class="metric"><span class="label">Runtime State</span><span class="value">{_e(blocked_text)}</span><span class="note">{_e('No drift detected' if report.drift_count == 0 else 'Review planned changes')}</span></div>
    <div class="metric"><span class="label">Active MCP Tools</span><span class="value">{len(active_tools)}</span><span class="note">{_e(', '.join(tool.id for tool in active_tools) or 'none')}</span></div>
    <div class="metric"><span class="label">Covered Targets</span><span class="value">{len(covered_labels)}</span><span class="note">{_e(', '.join(covered_labels) or 'none')}</span></div>
    <div class="metric"><span class="label">Stored Secret Names</span><span class="value">{len(stored_names)}</span><span class="note">{_e(config.secret_file)}</span></div>
  </div>

  <div class="grid two">
    <section>
      <h2>Access Routes</h2>
      <p>{_badge('Search default', 'route')} <strong>{_e(config.routes.search_default or 'Not configured')}</strong></p>
      <p>{_badge('X reader', 'route')} <strong>{_e(config.routes.x_read_default or 'Not configured')}</strong> <span class="muted">fallback</span> <strong>{_e(config.routes.x_read_fallback or 'Not configured')}</strong></p>
    </section>
    <section>
      <h2>Secrets Inventory</h2>
      <div class="chips">{' '.join(_badge(name, 'neutral') for name in stored_names) or _badge('No secrets file', 'bad')}</div>
    </section>
  </div>

  <section style="margin-top: 14px;">
    <h2>Managed MCP Tools</h2>
    <table>
      <thead><tr><th>Tool</th><th>Role</th><th>Targets</th><th>Secrets</th><th>Wrapper</th></tr></thead>
      <tbody>{_tool_rows(config, paths, report)}</tbody>
    </table>
  </section>

  <section style="margin-top: 14px;">
    <h2>Target Coverage</h2>
    <table>
      <thead><tr><th>Target</th><th>Status</th><th>Managed Entries</th></tr></thead>
      <tbody>{_app_rows(config, paths, report, include_ccswitch)}</tbody>
    </table>
  </section>

  <div class="grid two" style="margin-top: 14px;">
    <section>
      <h2>Findings</h2>
      {_findings(report)}
    </section>
    <section>
      <h2>Planned Changes</h2>
      {_changes(report)}
    </section>
  </div>
</main>
</body>
</html>
"""
