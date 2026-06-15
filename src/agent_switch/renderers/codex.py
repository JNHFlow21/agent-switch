from __future__ import annotations

import re
import tomllib
from typing import Any

from .common import AGENT_PREFIX, RenderError, toml_value


AGENT_SUBTABLE_RE = re.compile(r"(?ms)^\[mcp_servers\.\"?agent-[^\]\"]+\"?\]\s*\n.*?(?=^\[|\Z)")


def _strip_agent_inline_entries(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_mcp_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_mcp_table = stripped == "[mcp_servers]"
        if in_mcp_table and stripped.startswith(AGENT_PREFIX) and "=" in stripped:
            continue
        out.append(line)
    return "\n".join(out).rstrip() + ("\n" if out else "")


def render_codex_config(current_text: str, desired: dict[str, dict[str, Any]]) -> str:
    if current_text.strip():
        try:
            tomllib.loads(current_text)
        except tomllib.TOMLDecodeError as exc:
            raise RenderError(f"malformed TOML config: {exc}") from exc

    text = AGENT_SUBTABLE_RE.sub("", current_text)
    text = _strip_agent_inline_entries(text)
    chunks = [text.rstrip()] if text.strip() else []
    for server_id in sorted(desired):
        spec = desired[server_id]
        lines = [f"[mcp_servers.{server_id}]"]
        for key in sorted(spec):
            lines.append(f"{key} = {toml_value(spec[key])}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunk for chunk in chunks if chunk).rstrip() + "\n"

