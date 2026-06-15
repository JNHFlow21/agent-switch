from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsTests(unittest.TestCase):
    def test_docs_reference_current_commands_and_boundaries(self) -> None:
        readme = (ROOT / "README.md").read_text()
        compat = (ROOT / "docs" / "ccswitch-compat.md").read_text()
        recovery = (ROOT / "docs" / "recovery.md").read_text()
        self.assertIn("agent-switch doctor", readme)
        self.assertIn("agent-*", compat)
        self.assertIn("CC Switch", compat)
        self.assertIn("agent-switch reconcile", recovery)


if __name__ == "__main__":
    unittest.main()

