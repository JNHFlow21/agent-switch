from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from agent_switch.ccswitch.db import CcSwitchDataError, CcSwitchDb, CcSwitchSchemaError
from agent_switch.config.model import ManagedApps


SCHEMA = """
CREATE TABLE mcp_servers (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, server_config TEXT NOT NULL,
  description TEXT, homepage TEXT, docs TEXT, tags TEXT NOT NULL DEFAULT '[]',
  enabled_claude BOOLEAN NOT NULL DEFAULT 0, enabled_codex BOOLEAN NOT NULL DEFAULT 0,
  enabled_gemini BOOLEAN NOT NULL DEFAULT 0, enabled_opencode BOOLEAN NOT NULL DEFAULT 0,
  enabled_hermes BOOLEAN NOT NULL DEFAULT 0
);
"""


def create_db(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO mcp_servers (id, name, server_config, tags) VALUES (?, ?, ?, ?)",
            ("playwright", "Playwright", json.dumps({"command": "playwright"}), "[]"),
        )


class CcSwitchDbTests(unittest.TestCase):
    def test_upsert_agent_row_preserves_non_agent_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "cc-switch.db"
            create_db(db_path)
            db = CcSwitchDb(db_path)
            db.upsert_agent_mcp_server(
                "agent-xcrawl",
                "Xcrawl",
                {"command": "/tmp/mcp-xcrawl", "args": []},
                ManagedApps(claude=True, codex=True, hermes=True),
            )
            rows = db.list_mcp_servers()
            self.assertIn("playwright", rows)
            self.assertEqual(rows["agent-xcrawl"].server_config["command"], "/tmp/mcp-xcrawl")
            self.assertTrue(rows["agent-xcrawl"].apps.claude)

    def test_missing_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bad.db"
            with closing(sqlite3.connect(db_path)) as conn, conn:
                conn.execute("CREATE TABLE mcp_servers (id TEXT)")
            with self.assertRaises(CcSwitchSchemaError):
                CcSwitchDb(db_path).list_mcp_servers()

    def test_bad_server_config_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "bad-json.db"
            create_db(db_path)
            with closing(sqlite3.connect(db_path)) as conn, conn:
                conn.execute("UPDATE mcp_servers SET server_config = ? WHERE id = ?", ("{bad", "playwright"))
            with self.assertRaises(CcSwitchDataError):
                CcSwitchDb(db_path).list_mcp_servers()


if __name__ == "__main__":
    unittest.main()
