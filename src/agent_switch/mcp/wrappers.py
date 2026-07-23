from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent_switch.atomic import WriteResult, write_if_changed
from agent_switch.config.model import AgentConfig, ToolSpec
from agent_switch.mcp.specs import wrapper_path_for
from agent_switch.mcp.templates import render_wrapper_script
from agent_switch.paths import AgentPaths, ensure_private_dir


@dataclass(frozen=True)
class WrapperHealth:
    tool_id: str
    path: Path
    exists: bool
    executable: bool

    def ok(self) -> bool:
        return self.exists and self.executable

    def to_dict(self) -> dict[str, object]:
        return {
            "toolId": self.tool_id,
            "path": str(self.path),
            "exists": self.exists,
            "executable": self.executable,
        }


def render_wrapper(tool: ToolSpec, secret_file: Path) -> str:
    return render_wrapper_script(tool, str(secret_file))


def write_wrappers(config: AgentConfig, paths: AgentPaths) -> list[WriteResult]:
    results: list[WriteResult] = []
    ensure_private_dir(paths.agent_home)
    ensure_private_dir(paths.wrapper_dir)
    enabled_tools = tuple(tool for tool in config.tools if tool.enabled)
    desired_paths = {wrapper_path_for(tool, paths.wrapper_dir) for tool in enabled_tools}
    for tool in enabled_tools:
        result = write_if_changed(
            wrapper_path_for(tool, paths.wrapper_dir),
            render_wrapper(tool, config.secret_file),
            mode=0o755,
            backup_dir=paths.backup_dir,
        )
        results.append(result)
    for stale in sorted(paths.wrapper_dir.glob("mcp-*")):
        if stale not in desired_paths and stale.is_file():
            stale.unlink()
            results.append(WriteResult(stale, True, None, ""))
    return results


def wrapper_health(config: AgentConfig, wrapper_dir: Path) -> list[WrapperHealth]:
    health: list[WrapperHealth] = []
    for tool in config.tools:
        if not tool.enabled:
            continue
        path = wrapper_path_for(tool, wrapper_dir)
        health.append(WrapperHealth(tool.id, path, path.exists(), os.access(path, os.X_OK)))
    return health
