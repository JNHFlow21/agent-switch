from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent_switch.atomic import WriteResult, write_if_changed
from agent_switch.config.model import AgentConfig, ToolSpec
from agent_switch.mcp.specs import wrapper_path_for
from agent_switch.mcp.templates import render_wrapper_script
from agent_switch.paths import AgentPaths


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
    paths.wrapper_dir.mkdir(parents=True, exist_ok=True)
    for tool in config.tools:
        result = write_if_changed(
            wrapper_path_for(tool, paths.wrapper_dir),
            render_wrapper(tool, config.secret_file),
            mode=0o755,
            backup_dir=paths.backup_dir,
        )
        results.append(result)
    return results


def wrapper_health(config: AgentConfig, wrapper_dir: Path) -> list[WrapperHealth]:
    health: list[WrapperHealth] = []
    for tool in config.tools:
        path = wrapper_path_for(tool, wrapper_dir)
        health.append(WrapperHealth(tool.id, path, path.exists(), os.access(path, os.X_OK)))
    return health

