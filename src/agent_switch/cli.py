from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_switch.atomic import write_if_changed
from agent_switch.ccswitch.imports import preview_deeplink
from agent_switch.config.loader import load_config, render_default_config
from agent_switch.paths import paths_for
from agent_switch.reconcile.apply import apply_reconcile
from agent_switch.reconcile.doctor import run_doctor
from agent_switch.status.dashboard import render_dashboard
from agent_switch.status.report import human_report


def _load(args: argparse.Namespace):
    paths = paths_for(args.home, args.user_home)
    config_file = Path(args.config) if args.config else paths.config_file
    config = load_config(config_file, paths.secrets_file)
    return paths, config


def cmd_doctor(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    report = run_doctor(config, paths, include_ccswitch=not args.no_ccswitch)
    sys.stdout.write(report.to_json() if args.json else human_report(report))
    return 1 if report.blocked and args.strict else 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    if args.dry_run:
        report = run_doctor(config, paths, include_ccswitch=not args.no_ccswitch)
        sys.stdout.write(report.to_json() if args.json else human_report(report))
        return 0
    summary, report = apply_reconcile(config, paths, include_ccswitch=not args.no_ccswitch)
    payload = {"summary": summary.to_dict(), "post": report.to_dict()}
    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"changed={summary.changed} unchanged={summary.unchanged} blocked={summary.blocked}\n")
        sys.stdout.write(human_report(report))
    return 1 if report.blocked else 0


def cmd_preview(args: argparse.Namespace) -> int:
    preview = preview_deeplink(args.url)
    if args.json:
        sys.stdout.write(json.dumps(preview.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    else:
        request = preview.request
        sys.stdout.write(f"{request.resource} {request.version}; forward={request.forward_to_ccswitch}\n")
        if preview.imported_agent_ids:
            sys.stdout.write("agent ids: " + ", ".join(preview.imported_agent_ids) + "\n")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    report = run_doctor(config, paths, include_ccswitch=not args.no_ccswitch)
    output = Path(args.output)
    dashboard = render_dashboard(report, config, paths, include_ccswitch=not args.no_ccswitch)
    result = write_if_changed(output, dashboard, backup_dir=paths.backup_dir)
    sys.stdout.write(str(result.path) + "\n")
    return 0


def cmd_write_default_config(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    result = write_if_changed(paths.config_file, render_default_config(config), backup_dir=paths.backup_dir)
    sys.stdout.write(f"{'wrote' if result.changed else 'unchanged'} {result.path}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-switch")
    parser.add_argument("--home", help="Agent Switch home directory")
    parser.add_argument("--user-home", help="Target user home for native app configs")
    parser.add_argument("--config", help="Central config JSON path")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--strict", action="store_true")
    doctor.add_argument("--no-ccswitch", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.add_argument("--strict", action="store_true")
    status.add_argument("--no-ccswitch", action="store_true")
    status.set_defaults(func=cmd_doctor)

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--json", action="store_true")
    reconcile.add_argument("--dry-run", action="store_true")
    reconcile.add_argument("--no-ccswitch", action="store_true")
    reconcile.set_defaults(func=cmd_reconcile)

    preview = sub.add_parser("preview")
    preview.add_argument("url")
    preview.add_argument("--json", action="store_true")
    preview.set_defaults(func=cmd_preview)

    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--output", required=True)
    dashboard.add_argument("--no-ccswitch", action="store_true")
    dashboard.set_defaults(func=cmd_dashboard)

    defaults = sub.add_parser("write-default-config")
    defaults.set_defaults(func=cmd_write_default_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
        sys.stderr.write(f"agent-switch: {exc}\n")
        return 2
