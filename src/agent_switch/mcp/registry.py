from __future__ import annotations

from dataclasses import replace
import re

from agent_switch.config.model import AgentConfig, ConfigError, RouteConfig, ToolSpec


def normalize_tool_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if slug.startswith("agent-"):
        slug = slug.removeprefix("agent-")
    if not slug:
        raise ConfigError("MCP id must contain at least one letter or number")
    return f"agent-{slug}"


def find_tool(config: AgentConfig, tool_id: str) -> ToolSpec:
    normalized = normalize_tool_id(tool_id)
    for tool in config.tools:
        if tool.id == normalized:
            return tool
    raise ConfigError(f"unknown MCP: {normalized}")


def put_tool(config: AgentConfig, tool: ToolSpec, *, require_new: bool = False) -> AgentConfig:
    normalized = normalize_tool_id(tool.id)
    normalized_tool = replace(tool, id=normalized)
    existing = {item.id: item for item in config.tools}
    if require_new and normalized in existing:
        raise ConfigError(f"MCP already exists: {normalized}")
    existing[normalized] = normalized_tool
    return replace(config, tools=tuple(existing[key] for key in sorted(existing)))


def set_tool_enabled(config: AgentConfig, tool_id: str, enabled: bool) -> AgentConfig:
    current = find_tool(config, tool_id)
    updated = put_tool(config, replace(current, enabled=enabled))
    if enabled:
        return updated
    routes = updated.routes
    return replace(
        updated,
        routes=RouteConfig(
            search_default="" if routes.search_default == current.id else routes.search_default,
            x_read_default="" if routes.x_read_default == current.id else routes.x_read_default,
            x_read_fallback="" if routes.x_read_fallback == current.id else routes.x_read_fallback,
        ),
    )


def remove_tool(config: AgentConfig, tool_id: str) -> AgentConfig:
    normalized = normalize_tool_id(tool_id)
    if normalized not in config.tool_ids():
        raise ConfigError(f"unknown MCP: {normalized}")
    routes = config.routes
    next_routes = RouteConfig(
        search_default="" if routes.search_default == normalized else routes.search_default,
        x_read_default="" if routes.x_read_default == normalized else routes.x_read_default,
        x_read_fallback="" if routes.x_read_fallback == normalized else routes.x_read_fallback,
    )
    return replace(config, tools=tuple(tool for tool in config.tools if tool.id != normalized), routes=next_routes)
