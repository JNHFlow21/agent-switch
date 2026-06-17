from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_json_runs_against_fixture_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--home", str(Path(tmp) / "agent"), "--user-home", str(Path(tmp) / "user"), "doctor", "--json", "--no-ccswitch"])
            self.assertEqual(code, 0)

    def test_preview_json_classifies_mcp(self) -> None:
        payload = {"mcpServers": {"xcrawl": {"command": "node", "env": {"XCRAWL_API_KEY": "secret"}}}}
        config = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["preview", f"ccswitch://v1/import?resource=mcp&config={config}", "--json"])
        self.assertEqual(code, 0)

    def test_secret_set_and_list_do_not_print_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--home", str(Path(tmp) / "agent"), "--user-home", str(Path(tmp) / "user"), "secret", "set", "EXAMPLE_API_KEY", "secret-value"])
            self.assertEqual(code, 0)
            self.assertNotIn("secret-value", stdout.getvalue())

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--home", str(Path(tmp) / "agent"), "--user-home", str(Path(tmp) / "user"), "secret", "list"])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue().strip(), "EXAMPLE_API_KEY")


if __name__ == "__main__":
    unittest.main()
