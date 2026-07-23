from __future__ import annotations

import re
import unittest
from pathlib import Path

from agent_switch import __version__


ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_release_versions_are_consistent(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text()
        project = (ROOT / "macos-app" / "AgentSwitch" / "AgentSwitch.xcodeproj" / "project.pbxproj").read_text()
        version_file = (ROOT / "VERSION").read_text().strip()
        pyproject_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        xcode_versions = set(re.findall(r"MARKETING_VERSION = ([^;]+);", project))

        self.assertIsNotNone(pyproject_version)
        self.assertEqual(version_file, __version__)
        self.assertEqual(pyproject_version.group(1), __version__)
        self.assertEqual(xcode_versions, {__version__})


if __name__ == "__main__":
    unittest.main()
