from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_switch.config.model import default_config
from agent_switch.paths import paths_for
from agent_switch.reconcile.doctor import DoctorReport
from agent_switch.reconcile.planner import PlanChange
from agent_switch.security.secrets import SecretReport
from agent_switch.status.dashboard import render_dashboard


class DashboardTests(unittest.TestCase):
    def test_dashboard_renders_state_when_no_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            paths.secrets_file.parent.mkdir(parents=True)
            paths.secrets_file.write_text("TAVILY_API_KEY=secret-value\n")
            config = default_config(paths.secrets_file)
            report = DoctorReport(
                findings=(),
                changes=(),
                secret_report=SecretReport(
                    path=paths.secrets_file,
                    exists=True,
                    required=("TAVILY_API_KEY",),
                    missing=(),
                    present_names=("TAVILY_API_KEY",),
                ),
            )
            html = render_dashboard(report, config, paths, include_ccswitch=False)

            self.assertIn("Managed MCP Tools", html)
            self.assertIn("Target Coverage", html)
            self.assertIn("Not configured", html)
            self.assertIn("Active MCP Tools</span><span class=\"value\">0", html)
            self.assertIn("No planned changes", html)
            self.assertIn("TAVILY_API_KEY", html)
            self.assertNotIn("secret-value", html)

    def test_dashboard_renders_planned_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp) / "agent", Path(tmp) / "user")
            config = default_config(paths.secrets_file)
            report = DoctorReport(
                findings=(),
                changes=(PlanChange("claude", paths.claude_config, "update", "drift"),),
                secret_report=SecretReport(paths.secrets_file, False, (), (), ()),
            )
            html = render_dashboard(report, config, paths, include_ccswitch=False)

            self.assertIn("claude", html)
            self.assertIn("drift", html)


if __name__ == "__main__":
    unittest.main()
