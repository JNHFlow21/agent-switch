from __future__ import annotations

from dataclasses import dataclass

from .model import AgentConfig, ToolSpec
from .model import ConfigError


@dataclass(frozen=True)
class RouteSelection:
    purpose: str
    primary: ToolSpec
    fallback: ToolSpec | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "purpose": self.purpose,
            "primary": self.primary.id,
            "fallback": self.fallback.id if self.fallback else None,
        }


def select_search_tool(config: AgentConfig) -> RouteSelection:
    tools = {tool.id: tool for tool in config.tools}
    if not config.routes.search_default:
        raise ConfigError("no default search MCP is configured")
    return RouteSelection("search", tools[config.routes.search_default])


def select_x_reader(config: AgentConfig) -> RouteSelection:
    tools = {tool.id: tool for tool in config.tools}
    if not config.routes.x_read_default or not config.routes.x_read_fallback:
        raise ConfigError("no X reader route is configured")
    return RouteSelection("x-read", tools[config.routes.x_read_default], tools[config.routes.x_read_fallback])
