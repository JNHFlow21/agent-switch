from __future__ import annotations

import json
from typing import Any


AGENT_PREFIX = "agent-"


class RenderError(ValueError):
    pass


def without_agent_entries(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if not key.startswith(AGENT_PREFIX)}


def render_json_mcp_config(current_text: str, desired: dict[str, dict[str, Any]]) -> str:
    if current_text.strip():
        try:
            root = json.loads(current_text)
        except json.JSONDecodeError as exc:
            raise RenderError(f"malformed JSON config: {exc}") from exc
        if not isinstance(root, dict):
            raise RenderError("JSON config root must be an object")
    else:
        root = {}

    current_servers = root.get("mcpServers", {})
    if current_servers is None:
        current_servers = {}
    if not isinstance(current_servers, dict):
        raise RenderError("mcpServers must be an object")

    merged = without_agent_entries(current_servers)
    merged.update({key: desired[key] for key in sorted(desired)})
    root["mcpServers"] = merged
    return json.dumps(root, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if value is None:
        return '""'
    return json.dumps(value)

