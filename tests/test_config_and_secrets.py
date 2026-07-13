from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.config.loader import load_config
from agent_switch.config.model import ConfigError, default_config
from agent_switch.config.routes import select_search_tool, select_x_reader
from agent_switch.security.secrets import check_secrets


class ConfigAndSecretTests(unittest.TestCase):
    def test_default_config_contains_expected_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = default_config(Path(tmp) / "secrets.env")
            self.assertEqual(select_search_tool(config).primary.id, "agent-xcrawl")
            self.assertEqual(select_x_reader(config).primary.id, "agent-birdread")
            self.assertEqual(select_x_reader(config).fallback.id, "agent-xurl-fallback")
            self.assertIn("agent-tavily", config.tool_ids())

    def test_rejects_non_agent_id_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "tools": [
                            {
                                "id": "xcrawl",
                                "name": "Xcrawl",
                                "command": "xcrawl",
                            }
                        ]
                    }
                )
            )
            with self.assertRaises(ConfigError):
                load_config(path, Path(tmp) / "secrets.env")

    def test_secret_report_exposes_names_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            secret_file = Path(tmp) / "secrets.env"
            secret_file.write_text("TAVILY_API_KEY=sk-secret000000000000\nUNUSED_API_KEY=fixture-unused\n")
            config = default_config(secret_file)
            report = check_secrets(config)
            self.assertIn("TAVILY_API_KEY", report.present_names)
            self.assertIn("TAVILY_API_KEY", report.stored_names)
            self.assertIn("UNUSED_API_KEY", report.stored_names)
            self.assertNotIn("UNUSED_API_KEY", report.present_names)
            self.assertNotIn("sk-secret", json.dumps(report.to_dict()))
            self.assertIn("XCRAWL_API_KEY", report.missing)


if __name__ == "__main__":
    unittest.main()
