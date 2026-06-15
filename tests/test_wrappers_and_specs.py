from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.config.model import ToolSpec, default_config
from agent_switch.mcp.specs import desired_specs_for_app
from agent_switch.mcp.wrappers import render_wrapper, write_wrappers, wrapper_health
from agent_switch.paths import paths_for


class WrapperAndSpecTests(unittest.TestCase):
    def test_specs_reference_wrapper_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)
            specs = desired_specs_for_app(config, "claude", paths.wrapper_dir)
            rendered = json.dumps(specs)
            self.assertIn("mcp-xcrawl", rendered)
            self.assertNotIn("TAVILY_API_KEY", rendered)

    def test_wrapper_mentions_missing_secret_name_not_value(self) -> None:
        tool = ToolSpec(id="agent-test", name="Test", command="tool", required_secrets=("API_KEY",))
        script = render_wrapper(tool, Path("/tmp/secrets.env"))
        self.assertIn("API_KEY", script)
        self.assertNotIn("secret-value", script)

    def test_wrapper_without_required_secret_uses_empty_array(self) -> None:
        tool = ToolSpec(id="agent-open", name="Open", command="tool")
        script = render_wrapper(tool, Path("/tmp/secrets.env"))
        self.assertIn("required=()", script)

    def test_write_wrappers_sets_executable_bit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)
            write_wrappers(config, paths)
            health = wrapper_health(config, paths.wrapper_dir)
            self.assertTrue(all(item.ok() for item in health))


if __name__ == "__main__":
    unittest.main()
