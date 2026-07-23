from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.config.model import default_config
from agent_switch.mcp.imports import adopt_native_mcps, load_native_mcps, plan_import
from agent_switch.paths import paths_for
from agent_switch.reconcile.apply import apply_reconcile
from agent_switch.reconcile.doctor import run_doctor
from tests.test_cli import run_cli


class McpRegistryTests(unittest.TestCase):
    def test_clean_home_is_neutral_and_reconcile_writes_no_agent_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)

            report = run_doctor(config, paths, include_ccswitch=False)
            summary, post = apply_reconcile(config, paths, include_ccswitch=False)

            self.assertEqual(report.drift_count, 0)
            self.assertEqual(summary.changed, 0)
            self.assertEqual(post.drift_count, 0)
            self.assertFalse(paths.codex_config.exists())
            self.assertFalse(paths.claude_config.exists())
            self.assertFalse(paths.hermes_config.exists())

    def test_import_merges_targets_and_moves_secret_values_out_of_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root / "agent", root / "user")
            paths.claude_config.parent.mkdir(parents=True)
            paths.claude_config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "filesystem": {
                                "command": "npx",
                                "args": [
                                    "-y",
                                    "@modelcontextprotocol/server-filesystem@1.2.3",
                                    "--api-key",
                                    "fixture-opaque-argument",
                                ],
                                "env": {"FILESYSTEM_TOKEN": "fixture-private", "LOG_LEVEL": "info"},
                            }
                        }
                    }
                )
            )
            paths.codex_config.parent.mkdir(parents=True)
            paths.codex_config.write_text(
                '[mcp_servers.filesystem]\ncommand = "npx"\n'
                'args = ["-y", "@modelcontextprotocol/server-filesystem@1.2.3", "--api-key", "fixture-opaque-argument"]\n'
            )
            paths.hermes_config.parent.mkdir(parents=True)
            paths.hermes_config.write_text(
                'mcp_servers:\n  notes:\n    command: "notes-mcp"\n    args: []\n    env:\n      NOTES_API_KEY: "fixture-notes"\n'
            )

            native = load_native_mcps(paths)
            plan = plan_import(default_config(paths.secrets_file), native)
            filesystem = next(tool for tool in plan.config.tools if tool.id == "agent-filesystem")

            self.assertEqual({"claude", "codex"}, {name for name, enabled in filesystem.apps.to_dict().items() if enabled})
            self.assertEqual(
                filesystem.required_secrets,
                ("FILESYSTEM_TOKEN", "MCP_FILESYSTEM_SECRET_ARG_4"),
            )
            self.assertEqual(filesystem.args[-1], "${MCP_FILESYSTEM_SECRET_ARG_4}")
            self.assertEqual(filesystem.env, {"LOG_LEVEL": "info"})
            self.assertEqual(
                sorted(plan.secrets),
                ["FILESYSTEM_TOKEN", "MCP_FILESYSTEM_SECRET_ARG_4", "NOTES_API_KEY"],
            )
            self.assertNotIn("fixture-private", json.dumps(plan.config.to_public_dict()))
            self.assertNotIn("fixture-opaque-argument", json.dumps(plan.config.to_public_dict()))

            adopted = adopt_native_mcps(paths, native)
            self.assertEqual(len(adopted), 3)
            self.assertNotIn("filesystem", paths.claude_config.read_text())
            self.assertNotIn("filesystem", paths.codex_config.read_text())
            self.assertNotIn("notes", paths.hermes_config.read_text())
            self.assertTrue(any(paths.backup_dir.iterdir()))

    def test_cli_crud_and_import_never_print_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "agent"
            user = root / "user"
            common = ["--home", str(home), "--user-home", str(user)]
            added = run_cli(
                [
                    *common,
                    "mcp",
                    "add",
                    "demo",
                    "--name",
                    "Demo",
                    "--command",
                    "demo-mcp",
                    "--secret",
                    "DEMO_API_KEY",
                    "--app",
                    "codex",
                    "--json",
                ]
            )
            self.assertEqual(added.returncode, 0, added.stderr.decode(errors="replace"))
            config = json.loads((home / "config.json").read_text())
            self.assertEqual(config["tools"][0]["id"], "agent-demo")

            claude_config = user / ".claude.json"
            claude_config.parent.mkdir(parents=True, exist_ok=True)
            claude_config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "remote": {"command": "remote-mcp", "env": {"REMOTE_TOKEN": "fixture-never-print"}},
                            "cloud": {
                                "type": "http",
                                "url": "https://example.invalid/mcp",
                                "headers": {"Authorization": "fixture-http-secret"},
                            },
                        }
                    }
                )
            )
            imported = run_cli([*common, "mcp", "import", "--app", "claude", "--json"])
            self.assertEqual(imported.returncode, 0, imported.stderr.decode(errors="replace"))
            self.assertNotIn(b"fixture-never-print", imported.stdout + imported.stderr)
            self.assertNotIn(b"fixture-http-secret", imported.stdout + imported.stderr)
            payload = json.loads(imported.stdout)
            self.assertEqual(payload["supported"], 1)
            self.assertEqual(payload["skipped"][0]["id"], "cloud")
            self.assertIn("REMOTE_TOKEN", (home / "secrets.env").read_text())
            self.assertIn("cloud", claude_config.read_text())

            disabled = run_cli([*common, "mcp", "disable", "demo", "--json"])
            self.assertEqual(disabled.returncode, 0)
            removed = run_cli([*common, "mcp", "remove", "demo", "--json"])
            self.assertEqual(removed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
