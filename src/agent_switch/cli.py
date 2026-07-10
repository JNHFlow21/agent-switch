from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import BinaryIO

from agent_switch.atomic import write_if_changed
from agent_switch.ccswitch.imports import preview_deeplink
from agent_switch.config.loader import load_config, render_default_config
from agent_switch.paths import paths_for
from agent_switch.reconcile.apply import apply_reconcile
from agent_switch.reconcile.doctor import run_doctor
from agent_switch.security.secrets import MAX_SECRET_BYTES, get_secret, list_secret_names, set_secret
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
    has_legacy_value = args.value is not None
    source_count = int(has_legacy_value) + int(args.read_stdin) + int(args.fd is not None)
    if source_count != 1:
        raise ValueError("choose exactly one secret source: positional VALUE, --stdin, or --fd N")

    if has_legacy_value:
        sys.stderr.write(
            "agent-switch: warning: positional secret VALUE is deprecated and will be removed after 0.1.3; "
            "use --stdin NAME or --fd N NAME\n"
        )
        return args.value
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary.
        sys.stderr.write(f"agent-switch: {exc}\n")
        return 2
