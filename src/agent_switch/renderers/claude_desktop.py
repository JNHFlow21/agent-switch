from __future__ import annotations

from .common import render_json_mcp_config


def render_claude_desktop_config(current_text: str, desired: dict[str, dict[str, object]]) -> str:
    return render_json_mcp_config(current_text, desired)

