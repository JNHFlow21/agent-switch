from __future__ import annotations

import unittest
from pathlib import Path

from agent_switch.instructions import claude_instructions, codex_instructions, hermes_instructions, managed_block, merge_managed_block
from agent_switch.paths import paths_for


class SkillHubInstructionTests(unittest.TestCase):
    def test_managed_block_is_idempotent_when_it_is_the_entire_file(self) -> None:
        block = managed_block("managed body")
        self.assertEqual(merge_managed_block(block, "managed body"), block)

    def test_all_agent_instructions_include_skill_hub_policy(self) -> None:
        paths = paths_for(agent_home=Path('/tmp/agent-switch'), user_home=Path('/tmp/user'))
        for body in (codex_instructions(paths), claude_instructions(paths), hermes_instructions(paths)):
            self.assertIn('Skill Hub is the source of truth', body)
            self.assertIn('/Users/USER/AgentWorkspace/skill-hub/scripts/skillctl status', body)
            self.assertIn('profile-enable PROFILE SKILL', body)
            self.assertIn('sync PROFILE --prune', body)
            self.assertIn('global-sync-official --prune', body)
            self.assertIn('plus explicit `profiles/global.json` entries', body)
            self.assertIn('explicit non-OpenAI profile entries', body)
            self.assertIn('Do not run broad global installs', body)
            self.assertIn('Never store credentials in Skill files', body)


if __name__ == '__main__':
    unittest.main()
