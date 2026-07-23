from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


APP_NAMES = ("claude", "claude_desktop", "codex", "hermes")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
SENSITIVE_NAME_RE = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)", re.IGNORECASE)
SECRET_REFERENCE_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
SENSITIVE_ARG_FLAG_RE = re.compile(
    r"^--?(?:api[-_]?key|token|secret|password|passwd|credential|authorization|auth-token)(?:=|$)",
    re.IGNORECASE,
)
TOKEN_VALUE_RE = re.compile(
    r"(?ix)(sk-[A-Za-z0-9_\-]{8,}|xai-[A-Za-z0-9_\-]{8,}|tvly-[A-Za-z0-9_\-]{8,}|"
    r"AIza[A-Za-z0-9_\-]{12,}|[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"
)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ManagedApps:
    claude: bool = True
    claude_desktop: bool = True
    codex: bool = True
    hermes: bool = True

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "ManagedApps":
        if not value:
            return cls()
        known = {name: bool(value.get(name, getattr(cls(), name))) for name in APP_NAMES}
        return cls(**known)

    def enabled(self) -> tuple[str, ...]:
        return tuple(name for name in APP_NAMES if getattr(self, name))

    def to_dict(self) -> dict[str, bool]:
        return {name: getattr(self, name) for name in APP_NAMES}


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    command: str
    args: tuple[str, ...] = ()
    required_secrets: tuple[str, ...] = ()
    apps: ManagedApps = field(default_factory=ManagedApps)
    env: dict[str, str] = field(default_factory=dict)
    description: str | None = None
    enabled: bool = True

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ToolSpec":
        return cls(
            id=str(value["id"]),
            name=str(value.get("name") or value["id"]),
            command=str(value["command"]),
            args=tuple(str(item) for item in value.get("args", [])),
            required_secrets=tuple(str(item) for item in value.get("requiredSecrets", value.get("required_secrets", []))),
            apps=ManagedApps.from_mapping(value.get("apps")),
            env={str(k): str(v) for k, v in value.get("env", {}).items()},
            description=value.get("description"),
            enabled=bool(value.get("enabled", True)),
        )

    @property
    def wrapper_name(self) -> str:
        return f"mcp-{self.id.removeprefix('agent-')}"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "args": list(self.args),
            "requiredSecrets": list(self.required_secrets),
            "apps": self.apps.to_dict(),
            "envNames": sorted(self.env.keys()),
            "description": self.description,
            "enabled": self.enabled,
        }

    def to_config_dict(self) -> dict[str, Any]:
        payload = self.to_public_dict()
        payload.pop("envNames", None)
        payload["env"] = dict(sorted(self.env.items()))
        return payload


@dataclass(frozen=True)
class RouteConfig:
    search_default: str = ""
    x_read_default: str = ""
    x_read_fallback: str = ""

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "RouteConfig":
        if not value:
            return cls()
        return cls(
            search_default=str(value.get("searchDefault", value.get("search_default", cls.search_default))),
            x_read_default=str(value.get("xReadDefault", value.get("x_read_default", cls.x_read_default))),
            x_read_fallback=str(value.get("xReadFallback", value.get("x_read_fallback", cls.x_read_fallback))),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "searchDefault": self.search_default,
            "xReadDefault": self.x_read_default,
            "xReadFallback": self.x_read_fallback,
        }


@dataclass(frozen=True)
class AgentConfig:
    tools: tuple[ToolSpec, ...]
    routes: RouteConfig
    secret_file: Path

    def tool_ids(self) -> set[str]:
        return {tool.id for tool in self.tools}

    def tools_for_app(self, app: str) -> tuple[ToolSpec, ...]:
        if app not in APP_NAMES:
            raise ConfigError(f"unknown app: {app}")
        return tuple(tool for tool in self.tools if tool.enabled and getattr(tool.apps, app))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "tools": [tool.to_public_dict() for tool in self.tools],
            "routes": self.routes.to_dict(),
            "secretFile": str(self.secret_file),
        }

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "tools": [tool.to_config_dict() for tool in self.tools],
            "routes": self.routes.to_dict(),
            "secretFile": str(self.secret_file),
        }


def default_tools() -> tuple[ToolSpec, ...]:
    # A public control plane must start neutral. Recommended MCPs belong in an
    # explicit catalog/import flow, never in every user's first configuration.
    return ()


def default_config(secret_file: Path) -> AgentConfig:
    config = AgentConfig(tools=default_tools(), routes=RouteConfig(), secret_file=secret_file)
    validate_config(config)
    return config


def validate_config(config: AgentConfig) -> None:
    seen: set[str] = set()
    for tool in config.tools:
        if not tool.id.startswith("agent-"):
            raise ConfigError(f"managed tool id must start with agent-: {tool.id}")
        if tool.id in seen:
            raise ConfigError(f"duplicate tool id: {tool.id}")
        seen.add(tool.id)
        if not tool.command:
            raise ConfigError(f"tool command is required: {tool.id}")
        if TOKEN_VALUE_RE.search(tool.command):
            raise ConfigError(f"credential-shaped value must not be embedded in MCP command: {tool.id}")
        invalid_secrets = sorted(name for name in tool.required_secrets if not SECRET_NAME_RE.fullmatch(name))
        if invalid_secrets:
            raise ConfigError(f"invalid required secret name(s) for {tool.id}: {', '.join(invalid_secrets)}")
        invalid_env = sorted(name for name in tool.env if not ENV_NAME_RE.fullmatch(name))
        if invalid_env:
            raise ConfigError(f"invalid MCP environment name(s) for {tool.id}: {', '.join(invalid_env)}")
        sensitive_env = sorted(name for name in tool.env if SENSITIVE_NAME_RE.search(name))
        if sensitive_env:
            raise ConfigError(
                f"sensitive MCP environment name(s) must use requiredSecrets for {tool.id}: "
                + ", ".join(sensitive_env)
            )
        secret_shaped_env = sorted(name for name, value in tool.env.items() if TOKEN_VALUE_RE.search(value))
        if secret_shaped_env:
            raise ConfigError(
                f"credential-shaped MCP environment value(s) must use requiredSecrets for {tool.id}: "
                + ", ".join(secret_shaped_env)
            )
        previous_arg = ""
        for index, argument in enumerate(tool.args):
            references = set(SECRET_REFERENCE_RE.findall(argument))
            undeclared = sorted(name for name in references if SENSITIVE_NAME_RE.search(name) and name not in tool.required_secrets)
            if undeclared:
                raise ConfigError(
                    f"MCP argument references undeclared secret name(s) for {tool.id}: {', '.join(undeclared)}"
                )
            assignment_secret = bool(SENSITIVE_ARG_FLAG_RE.match(argument) and "=" in argument and not references)
            follows_secret_flag = bool(SENSITIVE_ARG_FLAG_RE.match(previous_arg) and "=" not in previous_arg and not references)
            if TOKEN_VALUE_RE.search(argument) or assignment_secret or follows_secret_flag:
                raise ConfigError(
                    f"credential-shaped MCP argument {index + 1} must use a declared ${{SECRET_NAME}} placeholder: {tool.id}"
                )
            previous_arg = argument
        overlap = set(tool.required_secrets) & set(tool.env)
        if overlap:
            raise ConfigError(f"MCP env must not override required secret name(s): {', '.join(sorted(overlap))}")
    enabled_ids = {tool.id for tool in config.tools if tool.enabled}
    missing_routes = [
        route
        for route in (config.routes.search_default, config.routes.x_read_default, config.routes.x_read_fallback)
        if route and route not in enabled_ids
    ]
    if missing_routes:
        raise ConfigError(f"route references unknown or disabled tool id(s): {', '.join(sorted(missing_routes))}")
