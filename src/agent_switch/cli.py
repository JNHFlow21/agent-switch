from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import re
from pathlib import Path
from typing import BinaryIO

from agent_switch.atomic import write_if_changed
from agent_switch import __version__
from agent_switch.agents import agent_statuses
from agent_switch.ccswitch.imports import preview_deeplink
from agent_switch.cli_inventory import cli_inventory
from agent_switch.config.loader import load_config, render_default_config
from agent_switch.config.model import ManagedApps, ToolSpec
from agent_switch.config.store import update_config
from agent_switch.mcp.registry import find_tool, normalize_tool_id, put_tool, remove_tool, set_tool_enabled
from agent_switch.mcp.imports import SENSITIVE_NAME_RE, adopt_native_mcps, discover_native_mcps, plan_import
from agent_switch.paths import ensure_private_dir, paths_for
from agent_switch.reconcile.apply import apply_reconcile
from agent_switch.reconcile.doctor import run_doctor
from agent_switch.security.secrets import (
    MAX_SECRET_BYTES,
    delete_secret,
    get_secret,
    list_secret_names,
    read_env_file,
    set_secret,
    validate_secret,
)
from agent_switch.skill_inventory import load_skill_report, update_git_skill_sources
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
    strict_failure = report.blocked or report.drift_count > 0 or bool(report.secret_report.missing)
    return 1 if args.strict and strict_failure else 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    if args.dry_run:
        report = run_doctor(config, paths, include_ccswitch=not args.no_ccswitch)
        sys.stdout.write(report.to_json() if args.json else human_report(report))
        return 1 if report.blocked else 0
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
    ensure_private_dir(paths.agent_home)
    result = write_if_changed(paths.config_file, render_default_config(config), backup_dir=paths.backup_dir)
    sys.stdout.write(f"{'wrote' if result.changed else 'unchanged'} {result.path}\n")
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    statuses = agent_statuses(config, paths)
    if args.json:
        sys.stdout.write(json.dumps({"agents": [item.to_dict() for item in statuses]}, ensure_ascii=False, indent=2) + "\n")
    else:
        for item in statuses:
            state = "not-detected"
            if item.detected:
                state = "managed" if item.in_sync else "needs-sync" if item.managed else "unmanaged"
            sys.stdout.write(f"{item.id}: {state}\n")
    return 0


def cmd_clis(args: argparse.Namespace) -> int:
    items = cli_inventory()
    if args.json:
        sys.stdout.write(json.dumps({"clis": [item.to_dict() for item in items]}, ensure_ascii=False, indent=2) + "\n")
    else:
        for item in items:
            state = item.version or item.path or "not-installed"
            sys.stdout.write(f"{item.id}: {state}\n")
    return 0


def cmd_skills_list(args: argparse.Namespace) -> int:
    report = load_skill_report()
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        for item in report.skills:
            sys.stdout.write(f"{item.name}: {item.status} ({item.source})\n")
    return 0


def cmd_skills_update(args: argparse.Namespace) -> int:
    output = update_git_skill_sources()
    if args.json:
        report = load_skill_report()
        sys.stdout.write(json.dumps({"updated": True, "message": output, "report": report.to_dict()}, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(output + ("\n" if output else ""))
    return 0


def _config_path(args: argparse.Namespace, paths) -> Path:
    return Path(args.config).expanduser() if args.config else paths.config_file


def _json_or_line(args: argparse.Namespace, payload: dict[str, object], line: str) -> None:
    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(line + "\n")


def cmd_mcp_list(args: argparse.Namespace) -> int:
    _paths, config = _load(args)
    tools = [tool.to_public_dict() for tool in config.tools]
    if args.json:
        sys.stdout.write(json.dumps({"mcps": tools}, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    else:
        for tool in config.tools:
            state = "enabled" if tool.enabled else "disabled"
            apps = ",".join(name for name, enabled in tool.apps.to_dict().items() if enabled) or "none"
            sys.stdout.write(f"{tool.id}: {state} [{apps}] {tool.command} {' '.join(tool.args)}\n")
    return 0


def _parse_env(entries: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"--env must use NAME=VALUE: {entry}")
        name, value = entry.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"invalid environment name: {name}")
        if SENSITIVE_NAME_RE.search(name):
            raise ValueError(f"sensitive environment name must be declared with --secret, not --env: {name}")
        result[name] = value
    return result


def _apps_from_names(names: list[str] | None) -> ManagedApps:
    selected = set(names or ("claude", "claude_desktop", "codex", "hermes"))
    return ManagedApps(
        claude="claude" in selected,
        claude_desktop="claude_desktop" in selected,
        codex="codex" in selected,
        hermes="hermes" in selected,
    )


def _tool_from_args(args: argparse.Namespace) -> ToolSpec:
    return ToolSpec(
        id=normalize_tool_id(args.id),
        name=args.name or normalize_tool_id(args.id).removeprefix("agent-"),
        command=args.command,
        args=tuple(args.arg or ()),
        required_secrets=tuple(sorted(set(args.secret or ()))),
        apps=_apps_from_names(args.app),
        env=_parse_env(args.env or []),
        description=args.description,
        enabled=not args.disabled,
    )


def _store_mcp(args: argparse.Namespace, *, require_new: bool) -> int:
    paths, _config = _load(args)
    tool = _tool_from_args(args)
    updated, result = update_config(
        _config_path(args, paths),
        paths.secrets_file,
        paths.backup_dir,
        lambda config: put_tool(config, tool, require_new=require_new),
    )
    stored = find_tool(updated, tool.id)
    _json_or_line(
        args,
        {"changed": result.changed, "mcp": stored.to_public_dict()},
        f"{'added' if require_new else 'saved'} {stored.id}",
    )
    return 0


def cmd_mcp_add(args: argparse.Namespace) -> int:
    return _store_mcp(args, require_new=True)


def cmd_mcp_set(args: argparse.Namespace) -> int:
    return _store_mcp(args, require_new=False)


def cmd_mcp_remove(args: argparse.Namespace) -> int:
    paths, _config = _load(args)
    normalized = normalize_tool_id(args.id)
    _updated, result = update_config(
        _config_path(args, paths),
        paths.secrets_file,
        paths.backup_dir,
        lambda config: remove_tool(config, normalized),
    )
    _json_or_line(args, {"changed": result.changed, "id": normalized}, f"removed {normalized}")
    return 0


def _toggle_mcp(args: argparse.Namespace, enabled: bool) -> int:
    paths, _config = _load(args)
    normalized = normalize_tool_id(args.id)
    updated, result = update_config(
        _config_path(args, paths),
        paths.secrets_file,
        paths.backup_dir,
        lambda config: set_tool_enabled(config, normalized, enabled),
    )
    tool = find_tool(updated, normalized)
    state = "enabled" if enabled else "disabled"
    _json_or_line(args, {"changed": result.changed, "mcp": tool.to_public_dict()}, f"{state} {normalized}")
    return 0


def cmd_mcp_enable(args: argparse.Namespace) -> int:
    return _toggle_mcp(args, True)


def cmd_mcp_disable(args: argparse.Namespace) -> int:
    return _toggle_mcp(args, False)


def cmd_mcp_import(args: argparse.Namespace) -> int:
    paths, config = _load(args)
    apps = args.app or ["claude", "claude_desktop", "codex", "hermes"]
    discovery = discover_native_mcps(paths, apps)
    native = discovery.mcps
    preview = plan_import(config, native)
    discovery_payload = {
        "discovered": len(native) + len(discovery.skipped),
        "supported": len(native),
        "skipped": [item.to_public_dict() for item in discovery.skipped],
    }
    if args.dry_run:
        payload = {"dryRun": True, **discovery_payload, **preview.to_public_dict()}
        _json_or_line(
            args,
            payload,
            f"would import {len(preview.imported)} MCP(s), merge {len(preview.merged)}, "
            f"and leave {len(discovery.skipped)} unsupported MCP(s) untouched",
        )
        return 0

    # Validate the complete import before moving any inline values into the
    # central store. Output and errors expose secret names only.
    stored = read_env_file(paths.secrets_file)
    conflicts = sorted(name for name, value in preview.secrets.items() if name in stored and stored[name] != value)
    if conflicts:
        raise ValueError("import would overwrite existing secret name(s): " + ", ".join(conflicts))
    for name, value in preview.secrets.items():
        validate_secret(name, value)
    for name, value in preview.secrets.items():
        set_secret(paths.secrets_file, name, value)
    updated, result = update_config(
        _config_path(args, paths),
        paths.secrets_file,
        paths.backup_dir,
        lambda current: plan_import(current, native).config,
    )
    adopted = ()
    sync_summary = None
    if args.adopt:
        preflight = run_doctor(updated, paths, include_ccswitch=not args.no_ccswitch)
        if preflight.blocked:
            raise RuntimeError("MCPs were imported but adoption is blocked; no source entry was removed")
        adopted = adopt_native_mcps(paths, native)
        sync_summary, post = apply_reconcile(updated, paths, include_ccswitch=not args.no_ccswitch)
        if post.blocked:
            raise RuntimeError("MCPs were imported but reconciliation is blocked; run agent-switch doctor")
    payload = {
        "changed": result.changed,
        **discovery_payload,
        **preview.to_public_dict(),
        "adoptedSourceFiles": len(adopted),
        "reconcile": sync_summary.to_dict() if sync_summary else None,
        "note": "source entries were backed up and replaced by managed projections" if args.adopt else "source entries are preserved until --adopt is explicitly requested",
    }
    _json_or_line(
        args,
        payload,
        f"imported {len(preview.imported)} MCP(s), merged {len(preview.merged)}, "
        f"stored {len(preview.secrets)} secret name(s), and left {len(discovery.skipped)} unsupported MCP(s) untouched",
    )
    return 0


def _read_secret_stream(stream: BinaryIO, source: str) -> str:
    if stream.isatty():
        raise ValueError(f"refusing to read a secret from TTY {source}; use a pipe or inherited file descriptor")

    limit = MAX_SECRET_BYTES + 3  # One overflow byte plus an optional CRLF.
    chunks: list[bytes] = []
    remaining = limit
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    raw = b"".join(chunks)
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith(b"\n"):
        raw = raw[:-1]
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("secret input must be valid UTF-8") from exc


def _read_secret_fd(fd: int) -> str:
    if fd < 3:
        raise ValueError("--fd must identify an inherited read descriptor numbered 3 or higher")
    try:
        duplicate = os.dup(fd)
    except OSError as exc:
        raise ValueError(f"unable to duplicate secret input fd {fd}: {exc.strerror or 'unavailable'}") from None
    try:
        with os.fdopen(duplicate, "rb") as stream:
            return _read_secret_stream(stream, f"fd {fd}")
    except OSError as exc:
        raise ValueError(f"unable to read secret input fd {fd}: {exc.strerror or 'unavailable'}") from None


def _secret_value_from_args(args: argparse.Namespace) -> str:
    if args.value is not None:
        raise ValueError("positional secret values are not supported; use --stdin NAME or --fd N NAME")
    source_count = int(args.read_stdin) + int(args.fd is not None)
    if source_count != 1:
        raise ValueError("choose exactly one secret source: --stdin or --fd N")
    if args.read_stdin:
        stream = getattr(sys.stdin, "buffer", None)
        if stream is None:
            raise ValueError("binary stdin is unavailable; use an inherited file descriptor")
        return _read_secret_stream(stream, "stdin")
    return _read_secret_fd(args.fd)


def cmd_secret_set(args: argparse.Namespace) -> int:
    value = _secret_value_from_args(args)
    paths, _config = _load(args)
    set_secret(paths.secrets_file, args.name, value)
    sys.stdout.write(f"set {args.name} in {paths.secrets_file}\n")
    return 0


def _same_output_target(left_fd: int, right_fd: int) -> bool:
    try:
        left = os.fstat(left_fd)
        right = os.fstat(right_fd)
    except OSError:
        return False
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
        left.st_rdev,
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
        right.st_rdev,
    )


def _duplicate_secret_output_fd(fd: int) -> int:
    if fd < 3:
        raise ValueError("--fd must identify an inherited write descriptor numbered 3 or higher")
    try:
        duplicate = os.dup(fd)
    except OSError as exc:
        raise ValueError(f"unable to duplicate secret output fd {fd}: {exc.strerror or 'unavailable'}") from None
    if os.isatty(duplicate):
        os.close(duplicate)
        raise ValueError(f"refusing to write a secret to TTY fd {fd}")
    for standard_fd in (1, 2):
        if _same_output_target(duplicate, standard_fd):
            os.close(duplicate)
            raise ValueError(f"refusing to write a secret through stdout or stderr alias fd {fd}")
    return duplicate


def _write_all(fd: int, data: bytes) -> None:
    remaining = memoryview(data)
    while remaining:
        written = os.write(fd, remaining)
        if written <= 0:
            raise OSError("secret output fd made no write progress")
        remaining = remaining[written:]


def cmd_secret_get(args: argparse.Namespace) -> int:
    output_fd = _duplicate_secret_output_fd(args.fd)
    try:
        paths, _config = _load(args)
        value = get_secret(paths.secrets_file, args.name)
        _write_all(output_fd, value.encode("utf-8", errors="strict"))
    finally:
        os.close(output_fd)
    return 0


def cmd_secret_list(args: argparse.Namespace) -> int:
    paths, _config = _load(args)
    names = list_secret_names(paths.secrets_file)
    if args.json:
        sys.stdout.write(json.dumps({"path": str(paths.secrets_file), "names": list(names)}, ensure_ascii=False, indent=2) + "\n")
    else:
        for name in names:
            sys.stdout.write(name + "\n")
    return 0


def cmd_secret_delete(args: argparse.Namespace) -> int:
    paths, _config = _load(args)
    delete_secret(paths.secrets_file, args.name)
    sys.stdout.write(f"deleted {args.name} from {paths.secrets_file}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-switch")
    parser.add_argument("--version", action="version", version=f"agent-switch {__version__}")
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

    agents = sub.add_parser("agents")
    agents.add_argument("--json", action="store_true")
    agents.set_defaults(func=cmd_agents)

    clis = sub.add_parser("clis")
    clis.add_argument("--json", action="store_true")
    clis.set_defaults(func=cmd_clis)

    skills = sub.add_parser("skills")
    skills_sub = skills.add_subparsers(dest="skills_command")
    skills.add_argument("--json", action="store_true")
    skills.set_defaults(func=cmd_skills_list)
    skills_list = skills_sub.add_parser("list")
    skills_list.add_argument("--json", action="store_true")
    skills_list.set_defaults(func=cmd_skills_list)
    skills_update = skills_sub.add_parser("update")
    skills_update.add_argument("--json", action="store_true")
    skills_update.set_defaults(func=cmd_skills_update)

    mcp = sub.add_parser("mcp", help="manage the central MCP registry")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_list = mcp_sub.add_parser("list")
    mcp_list.add_argument("--json", action="store_true")
    mcp_list.set_defaults(func=cmd_mcp_list)

    def add_tool_arguments(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("id", help="MCP id; agent- is added automatically")
        command_parser.add_argument("--name")
        command_parser.add_argument("--command", required=True)
        command_parser.add_argument("--arg", action="append", default=[])
        command_parser.add_argument("--secret", action="append", default=[])
        command_parser.add_argument("--env", action="append", default=[], help="non-secret NAME=VALUE environment entry")
        command_parser.add_argument(
            "--app",
            action="append",
            choices=("claude", "claude_desktop", "codex", "hermes"),
            help="target app; repeat as needed (defaults to all)",
        )
        command_parser.add_argument("--description")
        command_parser.add_argument("--disabled", action="store_true")
        command_parser.add_argument("--json", action="store_true")

    mcp_add = mcp_sub.add_parser("add")
    add_tool_arguments(mcp_add)
    mcp_add.set_defaults(func=cmd_mcp_add)
    mcp_set = mcp_sub.add_parser("set")
    add_tool_arguments(mcp_set)
    mcp_set.set_defaults(func=cmd_mcp_set)
    mcp_remove = mcp_sub.add_parser("remove")
    mcp_remove.add_argument("id")
    mcp_remove.add_argument("--json", action="store_true")
    mcp_remove.set_defaults(func=cmd_mcp_remove)
    mcp_import = mcp_sub.add_parser("import", help="import MCPs from installed agent configs")
    mcp_import.add_argument(
        "--app",
        action="append",
        choices=("claude", "claude_desktop", "codex", "hermes"),
        help="source app; repeat as needed (defaults to all)",
    )
    mcp_import.add_argument("--dry-run", action="store_true")
    mcp_import.add_argument("--adopt", action="store_true", help="back up source configs, remove imported entries, and reconcile managed projections")
    mcp_import.add_argument("--no-ccswitch", action="store_true")
    mcp_import.add_argument("--json", action="store_true")
    mcp_import.set_defaults(func=cmd_mcp_import)
    for name, handler in (("enable", cmd_mcp_enable), ("disable", cmd_mcp_disable)):
        toggle = mcp_sub.add_parser(name)
        toggle.add_argument("id")
        toggle.add_argument("--json", action="store_true")
        toggle.set_defaults(func=handler)

    secret = sub.add_parser("secret")
    secret_sub = secret.add_subparsers(dest="secret_command", required=True)
    secret_set = secret_sub.add_parser("set")
    source = secret_set.add_mutually_exclusive_group()
    source.add_argument("--stdin", dest="read_stdin", action="store_true", help="read the secret from standard input")
    source.add_argument("--fd", type=int, help="read the secret from an inherited descriptor numbered 3 or higher")
    secret_set.add_argument("name")
    secret_set.add_argument("value", nargs="?", help=argparse.SUPPRESS)
    secret_set.set_defaults(func=cmd_secret_set)
    secret_get = secret_sub.add_parser("get")
    secret_get.add_argument("--fd", type=int, required=True, help="write the secret to an inherited descriptor")
    secret_get.add_argument("name")
    secret_get.set_defaults(func=cmd_secret_get)
    secret_list = secret_sub.add_parser("list")
    secret_list.add_argument("--json", action="store_true")
    secret_list.set_defaults(func=cmd_secret_list)
    secret_delete = secret_sub.add_parser("delete")
    secret_delete.add_argument("name")
    secret_delete.set_defaults(func=cmd_secret_delete)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
        sys.stderr.write(f"agent-switch: {exc}\n")
        return 2
