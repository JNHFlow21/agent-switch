from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_switch.config.model import default_config
from agent_switch.paths import paths_for
from agent_switch.reconcile.apply import apply_reconcile
from agent_switch.reconcile.doctor import run_doctor


SCHEMA = """
CREATE TABLE mcp_servers (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, server_config TEXT NOT NULL,
  description TEXT, homepage TEXT, docs TEXT, tags TEXT NOT NULL DEFAULT '[]',
  enabled_claude BOOLEAN NOT NULL DEFAULT 0, enabled_codex BOOLEAN NOT NULL DEFAULT 0,
  enabled_gemini BOOLEAN NOT NULL DEFAULT 0, enabled_opencode BOOLEAN NOT NULL DEFAULT 0,
  enabled_hermes BOOLEAN NOT NULL DEFAULT 0
);
"""


class ReconcileFixtureHomeTests(unittest.TestCase):
    def test_reconcile_converges_and_second_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root / "agent", root / "user")
            paths.ccswitch_db.parent.mkdir(parents=True)
            with sqlite3.connect(paths.ccswitch_db) as conn:
                conn.executescript(SCHEMA)
                conn.execute(
                    "INSERT INTO mcp_servers (id, name, server_config, tags) VALUES (?, ?, ?, ?)",
                    ("playwright", "Playwright", json.dumps({"command": "pw"}), "[]"),
                )
            paths.claude_config.write_text(json.dumps({"mcpServers": {"playwright": {"command": "pw"}}}))
            paths.codex_config.parent.mkdir(parents=True)
            paths.codex_config.write_text('[mcp_servers.playwright]\ncommand = "pw"\n')
            paths.hermes_config.parent.mkdir(parents=True)
            paths.hermes_config.write_text('custom_providers: []\n')
            paths.claude_desktop_config.parent.mkdir(parents=True)
            paths.claude_desktop_config.write_text('{"deploymentMode":"3p-api"}')
            paths.secrets_file.parent.mkdir(parents=True)
            paths.secrets_file.write_text(
                "\n".join(
                    [
                        "TAVILY_API_KEY=sk-secret000000000000",
                        "XCRAWL_API_KEY=sk-secret000000000001",
                        "BIRDREAD_API_KEY=sk-secret000000000002",
                        "X_API_KEY=sk-secret000000000003",
                        "X_API_SECRET=sk-secret000000000004",
                        "X_ACCESS_TOKEN=sk-secret000000000005",
                        "X_ACCESS_TOKEN_SECRET=sk-secret000000000006",
                    ]
                )
            )

            config = default_config(paths.secrets_file)
            initial = run_doctor(config, paths)
            self.assertGreater(initial.drift_count, 0)

            summary, post = apply_reconcile(config, paths)
            self.assertGreater(summary.changed, 0)
            self.assertEqual(post.drift_count, 0)
            self.assertFalse(post.blocked)

            second_summary, second_post = apply_reconcile(config, paths)
            self.assertEqual(second_post.drift_count, 0)
            self.assertFalse(second_post.blocked)
            self.assertEqual(second_summary.changed, 0)
            self.assertEqual(second_summary.unchanged, 12)

            combined = "\n".join(
                [
                    paths.claude_config.read_text(),
                    paths.codex_config.read_text(),
                    paths.hermes_config.read_text(),
                    paths.claude_desktop_config.read_text(),
                    post.to_json(),
                ]
            )
            self.assertNotIn("sk-secret", combined)
            self.assertIn("playwright", paths.claude_config.read_text())


if __name__ == "__main__":
    unittest.main()
