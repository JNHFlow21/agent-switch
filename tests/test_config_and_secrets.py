from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.config.loader import load_config, render_default_config
from dataclasses import replace

from agent_switch.config.model import ConfigError, ToolSpec, default_config, validate_config
from agent_switch.config.routes import select_search_tool, select_x_reader
from agent_switch.security.secrets import check_secrets


class ConfigAndSecretTests(unittest.TestCase):
    def test_rejects_invalid_or_sensitive_environment_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            secret_file = Path(tmp) / "secrets.env"
            for tool, message in (
                (
                    ToolSpec(id="agent-bad", name="Bad", command="bad", required_secrets=("lowercase",)),
                    "invalid required secret",
                ),
                (
                    ToolSpec(id="agent-bad", name="Bad", command="bad", env={"API_TOKEN": "inline"}),
                    "must use requiredSecrets",
                ),
                (
                    ToolSpec(id="agent-bad", name="Bad", command="bad", env={"BAD-NAME": "value"}),
                    "invalid MCP environment",
                ),
                (
                    ToolSpec(id="agent-bad", name="Bad", command="bad", args=("--token", "literal-value")),
                    "must use a declared",
                ),
            ):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ConfigError, message):
                        validate_config(replace(default_config(secret_file), tools=(tool,)))

    def test_default_config_is_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = default_config(Path(tmp) / "secrets.env")
            self.assertEqual(config.tools, ())
            self.assertEqual(config.routes.search_default, "")
            with self.assertRaisesRegex(ConfigError, "no default search"):
                select_search_tool(config)
            with self.assertRaisesRegex(ConfigError, "no X reader"):
                select_x_reader(config)

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
            config = replace(
                default_config(secret_file),
                tools=(ToolSpec(id="agent-tavily", name="Tavily", command="tool", required_secrets=("TAVILY_API_KEY", "XCRAWL_API_KEY")),),
            )
            report = check_secrets(config)
            self.assertIn("TAVILY_API_KEY", report.present_names)
            self.assertIn("TAVILY_API_KEY", report.stored_names)
            self.assertIn("UNUSED_API_KEY", report.stored_names)
            self.assertNotIn("UNUSED_API_KEY", report.present_names)
            self.assertNotIn("sk-secret", json.dumps(report.to_dict()))
            self.assertIn("XCRAWL_API_KEY", report.missing)

    def test_non_secret_environment_round_trips_but_public_view_lists_names_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = replace(
                default_config(Path(tmp) / "secrets.env"),
                tools=(ToolSpec(id="agent-demo", name="Demo", command="demo", env={"LOG_LEVEL": "debug"}),),
            )
            path.write_text(render_default_config(config))

            loaded = load_config(path, Path(tmp) / "secrets.env")

            self.assertEqual(loaded.tools[0].env, {"LOG_LEVEL": "debug"})
            self.assertNotIn("debug", json.dumps(loaded.to_public_dict()))
            self.assertIn("LOG_LEVEL", loaded.tools[0].to_public_dict()["envNames"])


if __name__ == "__main__":
    unittest.main()
