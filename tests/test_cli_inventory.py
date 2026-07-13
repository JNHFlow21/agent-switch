from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from agent_switch.cli_inventory import _safe_version, cli_inventory


class CLIInventoryTests(unittest.TestCase):
    def test_reports_installed_path_and_first_version_line(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="codex-cli 1.2.3\nmore\n", stderr="")
        with patch("agent_switch.cli_inventory.shutil.which", side_effect=lambda command: "/bin/codex" if command == "codex" else None), patch(
            "agent_switch.cli_inventory.subprocess.run", return_value=completed
        ):
            items = {item.id: item for item in cli_inventory()}

        self.assertTrue(items["codex"].installed)
        self.assertEqual(items["codex"].path, "/bin/codex")
        self.assertEqual(items["codex"].version, "codex-cli 1.2.3")
        self.assertFalse(items["claude"].installed)
        self.assertIsNone(items["claude"].version)

    def test_version_failure_is_non_fatal(self) -> None:
        with patch("agent_switch.cli_inventory.subprocess.run", side_effect=subprocess.TimeoutExpired("tool", 3)):
            self.assertIsNone(_safe_version("/bin/tool", ("--version",)))


if __name__ == "__main__":
    unittest.main()
