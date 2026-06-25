from __future__ import annotations

import unittest
from pathlib import Path

from agent_switch.instructions import claude_instructions, codex_instructions, hermes_instructions
from agent_switch.paths import paths_for


class SkillHubInstructionTests(unittest.TestCase):
    def test_all_agent_instructions_include_skill_hub_policy(self) -> None:
        paths = paths_for(agent_home=Path('/tmp/agent-switch'), user_home=Path('/tmp/user'))
        for body in (codex_instructions(paths), claude_instructions(paths), hermes_instructions(paths)):
            self.assertIn('Skill Hub is the source of truth', body)
            self.assertIn('/Users/USER/AgentWorkspace/skill-hub/scripts/skillctl status', body)
            self.assertIn('Do not run broad global installs', body)
            self.assertIn('Never store credentials in Skill files', body)


if __name__ == '__main__':
    unittest.main()
