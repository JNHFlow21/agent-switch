from __future__ import annotations

import unittest

from agent_switch.mcp.bird_server import build_server as build_bird_server
from agent_switch.mcp.simple_stdio import StdioMCPServer
from agent_switch.mcp.xcli_server import build_server as build_xcli_server


class LocalMCPServerTests(unittest.TestCase):
    def test_bird_server_lists_reader_tools(self) -> None:
        response = build_bird_server()._handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}  # type: ignore[index]
        self.assertIn("read_x_post", names)
        self.assertIn("read_x_thread", names)
        self.assertIn("search_x_posts", names)

    def test_xcli_server_lists_fallback_tools(self) -> None:
        response = build_xcli_server()._handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in response["result"]["tools"]}  # type: ignore[index]
        self.assertIn("x_api_get_post", names)
        self.assertIn("x_api_search_posts", names)

    def test_unknown_tool_returns_mcp_tool_error(self) -> None:
        server = StdioMCPServer(name="test", version="0", tools=[])
        response = server._handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "missing", "arguments": {}},
            }
        )
        self.assertEqual(response["error"]["code"], -32602)  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
