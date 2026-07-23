from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agent_switch.config.model import ToolSpec, default_config
from agent_switch.mcp.specs import desired_specs_for_app
from agent_switch.mcp.wrappers import render_wrapper, write_wrappers, wrapper_health
from agent_switch.paths import paths_for


class WrapperAndSpecTests(unittest.TestCase):
    def test_specs_reference_wrapper_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = replace(
                default_config(paths.secrets_file),
                tools=(ToolSpec(id="agent-xcrawl", name="Xcrawl", command="xcrawl", required_secrets=("XCRAWL_API_KEY",)),),
            )
            specs = desired_specs_for_app(config, "claude", paths.wrapper_dir)
            rendered = json.dumps(specs)
            self.assertIn("mcp-xcrawl", rendered)
            self.assertNotIn("TAVILY_API_KEY", rendered)

    def test_wrapper_mentions_missing_secret_name_not_value(self) -> None:
        tool = ToolSpec(id="agent-test", name="Test", command="tool", required_secrets=("API_KEY",))
        script = render_wrapper(tool, Path("/tmp/secrets.env"))
        self.assertIn("API_KEY", script)
        self.assertNotIn("secret-value", script)

    def test_wrapper_without_required_secret_uses_empty_required_list(self) -> None:
        tool = ToolSpec(id="agent-open", name="Open", command="tool")
        script = render_wrapper(tool, Path("/tmp/secrets.env"))
        self.assertIn("REQUIRED = tuple([])", script)
        self.assertNotIn("source ", script)

    def test_wrapper_without_required_secret_runs_under_nounset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "wrapper"
            tool = ToolSpec(id="agent-open", name="Open", command="printf", args=("ok",))
            script_path.write_text(render_wrapper(tool, Path(tmp) / "missing.env"))
            script_path.chmod(0o755)

            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "ok")

    def test_write_wrappers_sets_executable_bit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)
            write_wrappers(config, paths)
            health = wrapper_health(config, paths.wrapper_dir)
            self.assertTrue(all(item.ok() for item in health))

    def test_wrapper_grants_only_declared_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secrets = root / "secrets.env"
            secrets.write_text("ALLOWED_API_KEY=allowed\nUNRELATED_TOKEN=blocked\n")
            probe = (
                "import os; print(int('ALLOWED_API_KEY' in os.environ), "
                "int('UNRELATED_TOKEN' in os.environ), int('INHERITED_SECRET' in os.environ), "
                "int(os.environ.get('SAFE_FLAG') == 'yes'))"
            )
            tool = ToolSpec(
                id="agent-isolated",
                name="Isolated",
                command=sys.executable,
                args=("-c", probe),
                required_secrets=("ALLOWED_API_KEY",),
            )
            wrapper = root / "wrapper"
            wrapper.write_text(render_wrapper(tool, secrets))
            wrapper.chmod(0o755)

            result = subprocess.run(
                [str(wrapper)],
                capture_output=True,
                text=True,
                env={**os.environ, "INHERITED_SECRET": "blocked", "SAFE_FLAG": "yes"},
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "1 0 0 1")

    def test_wrapper_expands_declared_secret_placeholders_in_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secrets = root / "secrets.env"
            secrets.write_text("CLI_TOKEN=argument-value\n")
            tool = ToolSpec(
                id="agent-argument",
                name="Argument",
                command=sys.executable,
                args=("-c", "import sys; print(sys.argv[1])", "${CLI_TOKEN}"),
                required_secrets=("CLI_TOKEN",),
            )
            wrapper = root / "wrapper"
            wrapper.write_text(render_wrapper(tool, secrets))
            wrapper.chmod(0o755)

            result = subprocess.run([str(wrapper)], capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "argument-value")
            self.assertNotIn("argument-value", wrapper.read_text())


if __name__ == "__main__":
    unittest.main()
