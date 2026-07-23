from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import tomllib
from typing import Any, Iterable

from agent_switch.atomic import WriteResult, write_if_changed
from agent_switch.config.model import AgentConfig, ConfigError, ManagedApps, ToolSpec, validate_config
from agent_switch.mcp.registry import normalize_tool_id, put_tool
from agent_switch.paths import AgentPaths
from agent_switch.renderers.hermes import _entry_key, _find_mcp_section, _split_yaml_entries
from agent_switch.security.redaction import TOKEN_VALUE_RE


SENSITIVE_NAME_RE = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)", re.IGNORECASE)
SECRET_REFERENCE_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
SENSITIVE_ARG_FLAG_RE = re.compile(
    r"^--?(?:api[-_]?key|token|secret|password|passwd|credential|authorization|auth-token)(?:=|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NativeMcp:
    app: str
    source_id: str
    command: str
    args: tuple[str, ...]
    env: dict[str, str]
    required_secrets: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkippedNativeMcp:
    app: str
    source_id: str
    reason: str

    def to_public_dict(self) -> dict[str, str]:
        return {"app": self.app, "id": self.source_id, "reason": self.reason}


@dataclass(frozen=True)
class NativeMcpDiscovery:
    mcps: tuple[NativeMcp, ...]
    skipped: tuple[SkippedNativeMcp, ...]


@dataclass(frozen=True)
class ImportPlan:
    config: AgentConfig
    secrets: dict[str, str]
    imported: tuple[str, ...]
    merged: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "imported": list(self.imported),
            "merged": list(self.merged),
            "secretNames": sorted(self.secrets),
        }


def _derived_arg_secret_name(server_id: str, index: int) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", server_id.upper()).strip("_") or "MCP"
    return f"MCP_{slug}_SECRET_ARG_{index + 1}"


def _sanitize_args(server_id: str, raw_args: list[object]) -> tuple[tuple[str, ...], dict[str, str], tuple[str, ...]]:
    args = [str(item) for item in raw_args]
    values: dict[str, str] = {}
    required: set[str] = set()
    rendered: list[str] = []
    previous = ""
    for index, arg in enumerate(args):
        references = set(SECRET_REFERENCE_RE.findall(arg))
        required.update(name for name in references if SENSITIVE_NAME_RE.search(name))
        sensitive_assignment = SENSITIVE_ARG_FLAG_RE.match(arg)
        sensitive_after_flag = bool(SENSITIVE_ARG_FLAG_RE.match(previous) and "=" not in previous)
        sensitive_header = previous in {"--header", "-H"} and bool(SENSITIVE_NAME_RE.search(arg))
        literal_credential = bool(TOKEN_VALUE_RE.search(arg))
        needs_migration = not references and (sensitive_after_flag or sensitive_header or literal_credential)
        if sensitive_assignment and "=" in arg and not references:
            prefix, secret_value = arg.split("=", 1)
            if secret_value:
                name = _derived_arg_secret_name(server_id, index)
                values[name] = secret_value
                required.add(name)
                rendered.append(f"{prefix}=${{{name}}}")
                previous = arg
                continue
        if needs_migration:
            name = _derived_arg_secret_name(server_id, index)
            values[name] = arg
            required.add(name)
            rendered.append(f"${{{name}}}")
        else:
            rendered.append(arg)
        previous = arg
    return tuple(rendered), values, tuple(sorted(required))


def _spec_from_mapping(app: str, server_id: str, value: Any) -> NativeMcp:
    if not isinstance(value, dict):
        raise ConfigError(f"{app} MCP {server_id} must be an object")
    command = value.get("command")
    if not isinstance(command, str) or not command:
        raise ConfigError(f"{app} MCP {server_id} has no command")
    raw_args = value.get("args", [])
    raw_env = value.get("env", {})
    if not isinstance(raw_args, list) or not all(isinstance(item, (str, int, float, bool)) for item in raw_args):
        raise ConfigError(f"{app} MCP {server_id} args must be a list")
    if not isinstance(raw_env, dict):
        raise ConfigError(f"{app} MCP {server_id} env must be an object")
    args, arg_secrets, referenced_secrets = _sanitize_args(server_id, raw_args)
    environment = {str(name): str(secret) for name, secret in raw_env.items()}
    for name, secret in arg_secrets.items():
        if name in environment and environment[name] != secret:
            raise ConfigError(f"{app} MCP {server_id} has a derived argument secret conflict")
        environment[name] = secret
    return NativeMcp(
        app=app,
        source_id=server_id,
        command=command,
        args=args,
        env=environment,
        required_secrets=referenced_secrets,
    )


def _scan_spec(app: str, server_id: str, value: Any) -> tuple[NativeMcp | None, SkippedNativeMcp | None]:
    if isinstance(value, dict) and not value.get("command") and value.get("url"):
        raw_transport = str(value.get("type") or "remote").lower()
        transport = raw_transport if raw_transport in {"http", "sse", "streamable-http"} else "remote"
        return None, SkippedNativeMcp(
            app=app,
            source_id=server_id,
            reason=f"{transport} transport requires the remote MCP adapter",
        )
    return _spec_from_mapping(app, server_id, value), None


def _json_mcp_discovery(path: Path, app: str) -> NativeMcpDiscovery:
    if not path.exists():
        return NativeMcpDiscovery((), ())
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid {app} JSON at {path}: {exc}") from exc
    servers = root.get("mcpServers", {}) if isinstance(root, dict) else {}
    if not isinstance(servers, dict):
        raise ConfigError(f"{app} mcpServers must be an object")
    mcps: list[NativeMcp] = []
    skipped: list[SkippedNativeMcp] = []
    for server_id, spec in servers.items():
        source_id = str(server_id)
        if source_id.startswith("agent-"):
            continue
        native, unsupported = _scan_spec(app, source_id, spec)
        if native is not None:
            mcps.append(native)
        if unsupported is not None:
            skipped.append(unsupported)
    return NativeMcpDiscovery(tuple(mcps), tuple(skipped))


def _codex_mcp_discovery(path: Path) -> NativeMcpDiscovery:
    if not path.exists():
        return NativeMcpDiscovery((), ())
    try:
        root = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid codex TOML at {path}: {exc}") from exc
    servers = root.get("mcp_servers", {}) if isinstance(root, dict) else {}
    if not isinstance(servers, dict):
        raise ConfigError("codex mcp_servers must be a table")
    mcps: list[NativeMcp] = []
    skipped: list[SkippedNativeMcp] = []
    for server_id, spec in servers.items():
        source_id = str(server_id)
        if source_id.startswith("agent-"):
            continue
        native, unsupported = _scan_spec("codex", source_id, spec)
        if native is not None:
            mcps.append(native)
        if unsupported is not None:
            skipped.append(unsupported)
    return NativeMcpDiscovery(tuple(mcps), tuple(skipped))


def _yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "[]":
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip("'\"")


def _hermes_chunk_spec(chunk: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    index = 1
    while index < len(chunk):
        line = chunk[index]
        match = re.match(r"^    ([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if not match:
            index += 1
            continue
        key, raw_value = match.group(1), match.group(2) or ""
        if raw_value:
            result[key] = _yaml_scalar(raw_value)
            index += 1
            continue
        if key == "args":
            values: list[str] = []
            index += 1
            while index < len(chunk) and (item := re.match(r"^      -\s*(.*)$", chunk[index])):
                values.append(str(_yaml_scalar(item.group(1))))
                index += 1
            result[key] = values
            continue
        if key == "env":
            values_dict: dict[str, str] = {}
            index += 1
            while index < len(chunk) and (item := re.match(r"^      ([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", chunk[index])):
                values_dict[item.group(1)] = str(_yaml_scalar(item.group(2)))
                index += 1
            result[key] = values_dict
            continue
        index += 1
    return result


def _hermes_mcp_discovery(path: Path) -> NativeMcpDiscovery:
    if not path.exists():
        return NativeMcpDiscovery((), ())
    lines = path.read_text(encoding="utf-8").splitlines()
    section = _find_mcp_section(lines)
    if section is None:
        return NativeMcpDiscovery((), ())
    start, end = section
    items: list[NativeMcp] = []
    skipped: list[SkippedNativeMcp] = []
    for chunk in _split_yaml_entries(lines[start + 1 : end]):
        server_id = _entry_key(chunk)
        if server_id is None or server_id.startswith("agent-"):
            continue
        native, unsupported = _scan_spec("hermes", server_id, _hermes_chunk_spec(chunk))
        if native is not None:
            items.append(native)
        if unsupported is not None:
            skipped.append(unsupported)
    return NativeMcpDiscovery(tuple(items), tuple(skipped))


def discover_native_mcps(paths: AgentPaths, apps: Iterable[str] | None = None) -> NativeMcpDiscovery:
    selected = set(apps or ("claude", "claude_desktop", "codex", "hermes"))
    scans: list[NativeMcpDiscovery] = []
    if "claude" in selected:
        scans.append(_json_mcp_discovery(paths.claude_config, "claude"))
    if "claude_desktop" in selected:
        scans.append(_json_mcp_discovery(paths.claude_desktop_config, "claude_desktop"))
    if "codex" in selected:
        scans.append(_codex_mcp_discovery(paths.codex_config))
    if "hermes" in selected:
        scans.append(_hermes_mcp_discovery(paths.hermes_config))
    return NativeMcpDiscovery(
        tuple(mcp for scan in scans for mcp in scan.mcps),
        tuple(item for scan in scans for item in scan.skipped),
    )


def load_native_mcps(paths: AgentPaths, apps: Iterable[str] | None = None) -> tuple[NativeMcp, ...]:
    return discover_native_mcps(paths, apps).mcps


def _apps_with(apps: ManagedApps, app: str) -> ManagedApps:
    values = apps.to_dict()
    values[app] = True
    return ManagedApps(**values)


def plan_import(config: AgentConfig, native_mcps: Iterable[NativeMcp]) -> ImportPlan:
    updated = config
    secret_values: dict[str, str] = {}
    imported: list[str] = []
    merged: list[str] = []
    for native in native_mcps:
        tool_id = normalize_tool_id(native.source_id)
        private_env = {
            name: value
            for name, value in native.env.items()
            if SENSITIVE_NAME_RE.search(name) or TOKEN_VALUE_RE.search(value)
        }
        public_env = {name: value for name, value in native.env.items() if name not in private_env}
        for name, value in private_env.items():
            if name in secret_values and secret_values[name] != value:
                raise ConfigError(f"conflicting values found for secret name {name}")
            secret_values[name] = value
        apps = ManagedApps(claude=False, claude_desktop=False, codex=False, hermes=False)
        candidate = ToolSpec(
            id=tool_id,
            name=native.source_id,
            command=native.command,
            args=native.args,
            required_secrets=tuple(sorted(set(private_env) | set(native.required_secrets))),
            apps=_apps_with(apps, native.app),
            env=public_env,
            description=f"Imported from {native.app}",
        )
        existing = next((tool for tool in updated.tools if tool.id == tool_id), None)
        if existing is None:
            updated = put_tool(updated, candidate, require_new=True)
            imported.append(tool_id)
            continue
        public_conflicts = {
            name
            for name, value in candidate.env.items()
            if name in existing.env and existing.env[name] != value
        }
        compatible = existing.command == candidate.command and existing.args == candidate.args and not public_conflicts
        if not compatible:
            raise ConfigError(f"MCP import conflict for {tool_id}; commands or environments differ between sources")
        updated = put_tool(
            updated,
            replace(
                existing,
                apps=_apps_with(existing.apps, native.app),
                env={**existing.env, **candidate.env},
                required_secrets=tuple(sorted(set(existing.required_secrets) | set(candidate.required_secrets))),
            ),
        )
        merged.append(tool_id)
    validate_config(updated)
    return ImportPlan(updated, secret_values, tuple(sorted(set(imported))), tuple(sorted(set(merged))))


def _remove_json_entries(path: Path, ids: set[str], backup_dir: Path) -> WriteResult | None:
    if not path.exists() or not ids:
        return None
    root = json.loads(path.read_text(encoding="utf-8"))
    servers = root.get("mcpServers") if isinstance(root, dict) else None
    if not isinstance(servers, dict):
        return None
    changed = False
    for server_id in ids:
        changed = servers.pop(server_id, None) is not None or changed
    if not changed:
        return None
    return write_if_changed(path, json.dumps(root, ensure_ascii=False, indent=2, sort_keys=True) + "\n", backup_dir=backup_dir)


def _remove_codex_entries(path: Path, ids: set[str], backup_dir: Path) -> WriteResult | None:
    if not path.exists() or not ids:
        return None
    original = path.read_text(encoding="utf-8")
    rendered = original
    for server_id in ids:
        quoted = re.escape(server_id)
        subtable = re.compile(
            rf'(?ms)^\[mcp_servers\.(?:"{quoted}"|{quoted})\]\s*\n.*?(?=^\[|\Z)'
        )
        rendered = subtable.sub("", rendered)
        lines = rendered.splitlines()
        in_mcp_table = False
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_mcp_table = stripped == "[mcp_servers]"
            if in_mcp_table and re.match(rf'^(?:"{quoted}"|{quoted})\s*=', stripped):
                continue
            kept.append(line)
        rendered = "\n".join(kept).rstrip() + ("\n" if kept else "")
    if rendered == original:
        return None
    try:
        tomllib.loads(rendered)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"refusing to adopt Codex MCP because cleanup would produce invalid TOML: {exc}") from exc
    return write_if_changed(path, rendered, backup_dir=backup_dir)


def _remove_hermes_entries(path: Path, ids: set[str], backup_dir: Path) -> WriteResult | None:
    if not path.exists() or not ids:
        return None
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    section = _find_mcp_section(lines)
    if section is None:
        return None
    start, end = section
    preserved: list[str] = []
    for chunk in _split_yaml_entries(lines[start + 1 : end]):
        if _entry_key(chunk) not in ids:
            preserved.extend(chunk)
    rendered = "\n".join(lines[: start + 1] + preserved + lines[end:]).rstrip() + "\n"
    if rendered == original:
        return None
    return write_if_changed(path, rendered, backup_dir=backup_dir)


def adopt_native_mcps(paths: AgentPaths, native_mcps: Iterable[NativeMcp]) -> tuple[WriteResult, ...]:
    ids_by_app: dict[str, set[str]] = {}
    for native in native_mcps:
        ids_by_app.setdefault(native.app, set()).add(native.source_id)
    results = [
        _remove_json_entries(paths.claude_config, ids_by_app.get("claude", set()), paths.backup_dir),
        _remove_json_entries(
            paths.claude_desktop_config,
            ids_by_app.get("claude_desktop", set()),
            paths.backup_dir,
        ),
        _remove_codex_entries(paths.codex_config, ids_by_app.get("codex", set()), paths.backup_dir),
        _remove_hermes_entries(paths.hermes_config, ids_by_app.get("hermes", set()), paths.backup_dir),
    ]
    return tuple(result for result in results if result is not None)
