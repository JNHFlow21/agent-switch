from __future__ import annotations

import json
import tomllib
import unittest

from agent_switch.renderers.claude import render_claude_config
from agent_switch.renderers.claude_desktop import render_claude_desktop_config
from agent_switch.renderers.codex import render_codex_config
from agent_switch.renderers.hermes import render_hermes_config


DESIRED = {"agent-xcrawl": {"command": "/tmp/mcp-xcrawl", "args": []}}


class RendererTests(unittest.TestCase):
    def test_claude_preserves_non_agent_mcp(self) -> None:
        current = json.dumps({"mcpServers": {"playwright": {"command": "pw"}, "agent-old": {"command": "old"}}})
        rendered = render_claude_config(current, DESIRED)
        parsed = json.loads(rendered)
        self.assertIn("playwright", parsed["mcpServers"])
        self.assertNotIn("agent-old", parsed["mcpServers"])
        self.assertEqual(parsed["mcpServers"]["agent-xcrawl"]["command"], "/tmp/mcp-xcrawl")
        self.assertEqual(render_claude_config(rendered, DESIRED), rendered)

    def test_claude_desktop_preserves_provider_fields(self) -> None:
        current = json.dumps({"deploymentMode": "3p-api", "mcpServers": {}})
        rendered = render_claude_desktop_config(current, DESIRED)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["deploymentMode"], "3p-api")
        self.assertIn("agent-xcrawl", parsed["mcpServers"])

    def test_codex_updates_only_agent_tables(self) -> None:
        current = '[model]\nname = "gpt"\n\n[mcp_servers.playwright]\ncommand = "pw"\n'
        rendered = render_codex_config(current, DESIRED)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["model"]["name"], "gpt")
        self.assertEqual(parsed["mcp_servers"]["playwright"]["command"], "pw")
        self.assertEqual(parsed["mcp_servers"]["agent-xcrawl"]["command"], "/tmp/mcp-xcrawl")
        self.assertEqual(render_codex_config(rendered, DESIRED), rendered)

    def test_hermes_replaces_only_agent_entries(self) -> None:
        current = 'model: old\nmcp_servers:\n  # keep this note\n  tavily:\n    command: "tavily"\n  agent-old:\n    command: "old"\n'
        rendered = render_hermes_config(current, DESIRED)
        self.assertIn("model: old", rendered)
        self.assertIn("# keep this note", rendered)
        self.assertIn("tavily:", rendered)
        self.assertNotIn("agent-old", rendered)
        self.assertIn("agent-xcrawl:", rendered)
        self.assertEqual(render_hermes_config(rendered, DESIRED), rendered)


if __name__ == "__main__":
    unittest.main()
