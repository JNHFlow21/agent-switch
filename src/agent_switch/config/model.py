from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


APP_NAMES = ("claude", "claude_desktop", "codex", "hermes")


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
        }


@dataclass(frozen=True)
class RouteConfig:
    search_default: str = "agent-xcrawl"
    x_read_default: str = "agent-birdread"
    x_read_fallback: str = "agent-xurl-fallback"

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
        return tuple(tool for tool in self.tools if getattr(tool.apps, app))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "tools": [tool.to_public_dict() for tool in self.tools],
            "routes": self.routes.to_dict(),
            "secretFile": str(self.secret_file),
        }


def default_tools() -> tuple[ToolSpec, ...]:
    apps = ManagedApps()
    return (
        ToolSpec(
            id="agent-tavily",
            name="Tavily Search",
            command="npx",
            args=("-y", "tavily-mcp"),
            required_secrets=("TAVILY_API_KEY",),
            apps=apps,
            description="Search fallback when explicitly requested.",
        ),
        ToolSpec(
            id="agent-xcrawl",
            name="Xcrawl",
            command="npx",
            args=("-y", "xcrawl-mcp"),
            required_secrets=("XCRAWL_API_KEY",),
            apps=apps,
            description="Default public web research and scraping route.",
        ),
        ToolSpec(
            id="agent-birdread",
            name="Birdread",
            command="birdread-mcp",
            required_secrets=("BIRDREAD_API_KEY",),
            apps=apps,
            description="Default X/Twitter single-post reader.",
        ),
        ToolSpec(
            id="agent-xurl-fallback",
            name="Official X API fallback",
            command="xurl-mcp",
            required_secrets=("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"),
            apps=apps,
            description="Fallback X/Twitter reader route.",
        ),
    )


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
    missing_routes = [
        route
        for route in (config.routes.search_default, config.routes.x_read_default, config.routes.x_read_fallback)
        if route not in seen
    ]
    if missing_routes:
        raise ConfigError(f"route references unknown tool id(s): {', '.join(sorted(missing_routes))}")

