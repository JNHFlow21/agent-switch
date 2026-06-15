from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from .deeplink import DeepLinkRequest, mcp_tools_from_deeplink, parse_deeplink_url


@dataclass(frozen=True)
class ImportPreview:
    request: DeepLinkRequest
    imported_agent_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = self.request.to_dict()
        data["importedAgentIds"] = list(self.imported_agent_ids)
        return data


def preview_deeplink(url: str) -> ImportPreview:
    request = parse_deeplink_url(url)
    return ImportPreview(request, tuple(tool.id for tool in mcp_tools_from_deeplink(request)))


def forward_to_ccswitch(url: str) -> None:
    request = parse_deeplink_url(url)
    if not request.forward_to_ccswitch:
        raise ValueError("MCP deep links should be normalized by Agent Switch instead of forwarded")
    subprocess.run(["open", url], check=True)

