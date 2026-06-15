from __future__ import annotations

import json
import re
from typing import Any

from .common import AGENT_PREFIX


TOP_LEVEL_RE = re.compile(r"^[A-Za-z0-9_\\-]+:")


def _find_mcp_section(lines: list[str]) -> tuple[int, int] | None:
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == "mcp_servers:" and not line.startswith((" ", "\t")):
            start = idx
            break
    if start is None:
        return None
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        line = lines[idx]
        if line and not line.startswith((" ", "\t")) and TOP_LEVEL_RE.match(line):
            end = idx
            break
    return start, end


def _split_yaml_entries(section_lines: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in section_lines:
        if re.match(r"^  [^:\s][^:]*:\s*$", line):
            if current:
                chunks.append(current)
            current = [line]
        elif current:
            current.append(line)
        else:
            chunks.append([line])
    if current:
        chunks.append(current)
    return chunks


def _entry_key(chunk: list[str]) -> str | None:
    if not re.match(r"^  [^:\s][^:]*:\s*$", chunk[0]):
        return None
    return chunk[0].strip().split(":", 1)[0].strip("'\"")


def _render_agent_yaml(desired: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for server_id in sorted(desired):
        spec = desired[server_id]
        lines.append(f"  {server_id}:")
        for key in sorted(spec):
            value = spec[key]
            if isinstance(value, list):
                if value:
                    lines.append(f"    {key}:")
                    lines.extend(f"      - {json.dumps(item)}" for item in value)
                else:
                    lines.append(f"    {key}: []")
            else:
                lines.append(f"    {key}: {json.dumps(value)}")
    return lines


def render_hermes_config(current_text: str, desired: dict[str, dict[str, Any]]) -> str:
    lines = current_text.splitlines()
    section = _find_mcp_section(lines)
    desired_lines = _render_agent_yaml(desired)
    if section is None:
        base = lines[:]
        if base and base[-1].strip():
            base.append("")
        base.append("mcp_servers:")
        base.extend(desired_lines)
        return "\n".join(base).rstrip() + "\n"

    start, end = section
    section_body = lines[start + 1 : end]
    preserved: list[str] = []
    for chunk in _split_yaml_entries(section_body):
        key = _entry_key(chunk)
        if key is None or not key.startswith(AGENT_PREFIX):
            preserved.extend(chunk)
    next_section = ["mcp_servers:"] + preserved + desired_lines
    new_lines = lines[:start] + next_section + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"
