from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsTests(unittest.TestCase):
    def test_docs_reference_current_commands_and_boundaries(self) -> None:
        readme = (ROOT / "README.md").read_text()
        compat = (ROOT / "docs" / "ccswitch-compat.md").read_text()
        recovery = (ROOT / "docs" / "recovery.md").read_text()
        secrets = (ROOT / "docs" / "secrets-and-wrappers.md").read_text()
        instructions = (ROOT / "src" / "agent_switch" / "instructions.py").read_text()
        self.assertIn("agent-switch doctor", readme)
        self.assertIn("agent-*", compat)
        self.assertIn("CC Switch", compat)
        self.assertIn("agent-switch reconcile", recovery)
        self.assertIn("secret set --stdin", secrets)
        self.assertIn("secret set --fd", secrets)
        self.assertIn("secret get --fd", secrets)
        self.assertIn("secret delete", secrets)
        self.assertIn("without a system authentication dialog", secrets)
        self.assertNotIn("device-owner authentication", secrets)
        self.assertIn("agent_switch clis --json", readme)
        self.assertIn("agent_switch skills --json", readme)
        self.assertIn("agent-switch agents --json", recovery)
        self.assertIn("secret set --stdin", instructions)
        self.assertIn("secret get --fd", instructions)
        self.assertNotIn("secret set NAME VALUE` to add", instructions)


if __name__ == "__main__":
    unittest.main()
