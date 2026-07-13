from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_switch.skill_inventory import load_skill_report, update_git_skill_sources


class SkillInventoryTests(unittest.TestCase):
    def make_hub(self, root: Path) -> Path:
        hub = root / "skill-hub"
        (hub / "config").mkdir(parents=True)
        (hub / "profiles").mkdir()
        (hub / "vendor" / "remote" / "skills" / "dormant").mkdir(parents=True)
        (hub / "vendor" / "remote" / "skills" / "active").mkdir(parents=True)
        (hub / "vendor" / "remote" / "skills" / "dormant" / "SKILL.md").write_text("# dormant\n")
        (hub / "vendor" / "remote" / "skills" / "active" / "SKILL.md").write_text("# active\n")
        registry = {
            "sources": {
                "remote": {
                    "type": "git",
                    "url": "https://example.invalid/skills.git",
                    "ref": "main",
                    "checkout": "vendor/remote",
                    "skillPath": "skills",
                }
            }
        }
        (hub / "config" / "registry.json").write_text(json.dumps(registry))
        (hub / "skills.lock.json").write_text(
            json.dumps({"sources": {"remote": {"shortRevision": "abc1234", "updatedAt": "2026-07-12T00:00:00Z"}}})
        )
        (hub / "profiles" / "project-a.json").write_text(
            json.dumps({"project": "/tmp/project-a", "skills": [{"name": "active", "source": "remote", "path": "active"}]})
        )
        (hub / "profiles" / "global.json").write_text(
            json.dumps({"project": "/tmp/global", "skills": [{"name": "missing", "source": "remote", "path": "missing"}]})
        )
        return hub

    def test_distinguishes_dormant_project_global_and_missing_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = load_skill_report(self.make_hub(Path(tmp)))
            items = {item.name: item for item in report.skills}

        self.assertEqual(items["dormant"].status, "dormant")
        self.assertEqual(items["active"].status, "project")
        self.assertEqual(items["active"].profiles, ("project-a",))
        self.assertEqual(items["missing"].status, "missing")
        self.assertTrue(items["missing"].global_active)
        self.assertFalse(items["missing"].exists)
        self.assertEqual(report.sources[0].revision, "abc1234")

    def test_update_runs_skillctl_only_when_explicitly_called(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.make_hub(Path(tmp))
            script = hub / "scripts" / "skillctl"
            script.parent.mkdir()
            script.write_text("#!/bin/sh\nprintf 'updated %s %s %s' \"$1\" \"$2\" \"$3\"\n")
            script.chmod(0o755)

            output = update_git_skill_sources(hub)

        self.assertIn("--hub", output)
        self.assertIn("fetch", output)


if __name__ == "__main__":
    unittest.main()
