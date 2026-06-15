from __future__ import annotations

import base64
import json
import unittest

from agent_switch.ccswitch.deeplink import DeepLinkError, mcp_tools_from_deeplink, parse_deeplink_url
from agent_switch.ccswitch.imports import preview_deeplink


def _b64(value: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


class DeepLinkTests(unittest.TestCase):
    def test_provider_deeplink_is_forwarded(self) -> None:
        request = parse_deeplink_url("ccswitch://v1/import?resource=provider&app=claude&name=test")
        self.assertEqual(request.resource, "provider")
        self.assertTrue(request.forward_to_ccswitch)

    def test_mcp_deeplink_normalizes_to_agent_tools(self) -> None:
        config = {
            "mcpServers": {
                "xcrawl": {
                    "command": "node",
                    "args": ["server.js"],
                    "env": {"XCRAWL_API_KEY": "secret-value"},
                }
            }
        }
        url = f"ccswitch://v1/import?resource=mcp&apps=claude,codex&config={_b64(config)}"
        request = parse_deeplink_url(url)
        tools = mcp_tools_from_deeplink(request)
        preview = preview_deeplink(url)
        self.assertEqual(tools[0].id, "agent-xcrawl")
        self.assertEqual(tools[0].required_secrets, ("XCRAWL_API_KEY",))
        self.assertFalse(request.forward_to_ccswitch)
        self.assertEqual(preview.imported_agent_ids, ("agent-xcrawl",))

    def test_unsupported_version_fails(self) -> None:
        with self.assertRaises(DeepLinkError):
            parse_deeplink_url("ccswitch://v2/import?resource=provider")


if __name__ == "__main__":
    unittest.main()

