from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_switch.config.model import AgentConfig, ToolSpec


def wrapper_path_for(tool: ToolSpec, wrapper_dir: str | Path) -> Path:
    return Path(wrapper_dir) / tool.wrapper_name


def mcp_spec_for_tool(tool: ToolSpec, wrapper_dir: str | Path) -> dict[str, Any]:
    return {
        "command": str(wrapper_path_for(tool, wrapper_dir)),
        "args": [],
    }


def desired_specs_for_app(config: AgentConfig, app: str, wrapper_dir: str | Path) -> dict[str, dict[str, Any]]:
    return {tool.id: mcp_spec_for_tool(tool, wrapper_dir) for tool in config.tools_for_app(app)}

