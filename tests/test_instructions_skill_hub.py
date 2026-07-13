from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_switch.instructions import (
    claude_instructions,
    codex_instructions,
    hermes_instructions,
    managed_block,
    merge_managed_block,
)
from agent_switch.paths import paths_for


class SkillHubInstructionTests(unittest.TestCase):
    def test_managed_block_is_idempotent_when_it_is_the_entire_file(self) -> None:
        block = managed_block("managed body")
        self.assertEqual(merge_managed_block(block, "managed body"), block)

    def test_all_agent_instructions_include_skill_hub_policy(self) -> None:
        paths = paths_for(agent_home=Path('/tmp/agent-switch'), user_home=Path('/tmp/user'))
        with patch.dict(os.environ, {}, clear=True):
            for body in (codex_instructions(paths), claude_instructions(paths), hermes_instructions(paths)):
                self.assertIn('Skill Hub is the source of truth', body)
                self.assertIn('/tmp/user/AgentWorkspace/skill-hub/scripts/skillctl status', body)
                self.assertIn('A downloaded Skill is dormant by default', body)
                self.assertIn('profile-enable PROFILE SKILL', body)
                self.assertIn('sync PROFILE --prune', body)
                self.assertIn('global-sync-official --prune', body)
                self.assertIn('explicit `profiles/global.json` entries', body)
                self.assertIn('/tmp/user/.agents/skills', body)
                self.assertIn('Do not run broad global installs', body)
                self.assertIn('Never store credentials in Skill files', body)

    def test_skill_hub_path_can_be_overridden(self) -> None:
        paths = paths_for(agent_home=Path('/tmp/agent-switch'), user_home=Path('/tmp/user'))
        with patch.dict(os.environ, {'SKILL_HUB_HOME': '/tmp/custom-skill-hub'}):
            self.assertIn('/tmp/custom-skill-hub/scripts/skillctl status', codex_instructions(paths))


if __name__ == '__main__':
    unittest.main()
