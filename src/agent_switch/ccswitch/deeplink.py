from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote_plus, urlparse

from agent_switch.config.model import ManagedApps, ToolSpec


class DeepLinkError(ValueError):
    pass


@dataclass(frozen=True)
class DeepLinkRequest:
    url: str
    version: str
    resource: str
    query: dict[str, str]
    decoded_config: dict[str, Any] | None = None

    @property
    def forward_to_ccswitch(self) -> bool:
        return self.resource != "mcp"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "resource": self.resource,
            "forwardToCcSwitch": self.forward_to_ccswitch,
            "queryKeys": sorted(self.query.keys()),
            "mcpServerIds": sorted((self.decoded_config or {}).get("mcpServers", {}).keys()),
        }


def _decode_b64_json(value: str) -> dict[str, Any]:
    normalized = value.replace(" ", "+")
    normalized += "=" * (-len(normalized) % 4)
    try:
        data = base64.urlsafe_b64decode(normalized.encode("utf-8"))
        parsed = json.loads(data.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - normalize user-facing compatibility errors.
        raise DeepLinkError(f"invalid base64 JSON config: {exc}") from exc
    if not isinstance(parsed, dict):
        raise DeepLinkError("decoded config must be a JSON object")
    return parsed


def parse_deeplink_url(url: str) -> DeepLinkRequest:
    parsed = urlparse(url)
    if parsed.scheme != "ccswitch":
        raise DeepLinkError("URL must use ccswitch:// scheme")
    query = {key: unquote_plus(values[-1]) for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
    segments = [segment for segment in parsed.path.split("/") if segment]
    version = query.get("version")
    resource = query.get("resource")
    if parsed.netloc.startswith("v"):
        version = version or parsed.netloc
    elif parsed.netloc and parsed.netloc not in {"import"}:
        resource = resource or parsed.netloc
    if segments and segments[0].startswith("v"):
        version = version or segments[0]
    for segment in segments:
        if segment in {"provider", "mcp", "prompt", "skill"}:
            resource = resource or segment
    version = version or "v1"
    resource = resource or query.get("type")
    if version != "v1":
        raise DeepLinkError(f"unsupported CC Switch deep link version: {version}")
    if resource not in {"provider", "mcp", "prompt", "skill"}:
        raise DeepLinkError(f"unsupported CC Switch resource: {resource}")
    decoded = None
    if resource == "mcp":
        if "config" not in query:
            raise DeepLinkError("MCP deep link missing config parameter")
        decoded = _decode_b64_json(query["config"])
        if not isinstance(decoded.get("mcpServers"), dict):
            raise DeepLinkError("MCP config must contain mcpServers object")
    return DeepLinkRequest(url=url, version=version, resource=resource, query=query, decoded_config=decoded)


def _agent_id(source_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", source_id.strip()).strip("-").lower()
    if not normalized:
        normalized = "imported"
    return normalized if normalized.startswith("agent-") else f"agent-{normalized}"


def mcp_tools_from_deeplink(request: DeepLinkRequest) -> tuple[ToolSpec, ...]:
    if request.resource != "mcp" or not request.decoded_config:
        return ()
    tools: list[ToolSpec] = []
    for source_id, spec in sorted(request.decoded_config["mcpServers"].items()):
        if not isinstance(spec, dict):
            raise DeepLinkError(f"MCP server spec must be object: {source_id}")
        env = spec.get("env") if isinstance(spec.get("env"), dict) else {}
        required = tuple(sorted(str(key) for key in env.keys()))
        tools.append(
            ToolSpec(
                id=_agent_id(source_id),
                name=str(spec.get("name") or source_id),
                command=str(spec.get("command") or ""),
                args=tuple(str(item) for item in spec.get("args", [])),
                required_secrets=required,
                apps=ManagedApps(),
                description="Imported from CC Switch MCP deep link.",
            )
        )
    return tuple(tools)

