from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_switch.agents import _command_detected, agent_statuses
from agent_switch.config.model import default_config
from agent_switch.paths import paths_for
from agent_switch.reconcile.apply import apply_reconcile


class AgentStatusTests(unittest.TestCase):
    def test_command_detection_is_limited_to_the_real_user_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch("agent_switch.agents.shutil.which", return_value="/usr/local/bin/codex"):
            real_paths = paths_for(Path(tmp) / "agent", Path.home())
            fixture_paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            self.assertTrue(_command_detected(real_paths, "codex"))
            self.assertFalse(_command_detected(fixture_paths, "codex"))

    def test_reports_supported_agents_without_creating_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)

            statuses = agent_statuses(config, paths)

            self.assertEqual([item.id for item in statuses], ["codex", "claude", "hermes"])
            self.assertTrue(all(not item.detected for item in statuses))
            self.assertTrue(all(not item.managed for item in statuses))
            self.assertFalse(paths.codex_config.exists())

    def test_detected_agent_moves_from_unmanaged_to_managed_after_reconcile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            paths.codex_config.parent.mkdir(parents=True)
            paths.codex_config.write_text('model = "demo"\n')
            paths.claude_global_instructions.parent.mkdir(parents=True)
            paths.claude_global_instructions.write_text("# user claude instructions\n")
            paths.hermes_soul.parent.mkdir(parents=True)
            paths.hermes_soul.write_text("# user hermes soul\n")
            config = default_config(paths.secrets_file)

            before = {item.id: item for item in agent_statuses(config, paths)}
            self.assertTrue(all(item.detected for item in before.values()))
            self.assertTrue(all(not item.managed for item in before.values()))

            _summary, post = apply_reconcile(config, paths, include_ccswitch=False)
            self.assertFalse(post.blocked)
            after = {item.id: item for item in agent_statuses(config, paths)}
            self.assertTrue(all(item.managed for item in after.values()))
            self.assertTrue(all(item.in_sync for item in after.values()))
            self.assertIn("# user claude instructions", paths.claude_global_instructions.read_text())
            self.assertIn("# user hermes soul", paths.hermes_soul.read_text())

            payload = json.dumps([item.to_dict() for item in after.values()])
            self.assertNotIn("secret", payload.lower())


if __name__ == "__main__":
    unittest.main()
