from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agent_switch.atomic import WriteResult, write_if_changed
from agent_switch.paths import AgentPaths


MANAGED_START = "<!-- BEGIN AGENT SWITCH MANAGED INSTRUCTIONS -->"
MANAGED_END = "<!-- END AGENT SWITCH MANAGED INSTRUCTIONS -->"


@dataclass(frozen=True)
class InstructionTargets:
    codex: Path
    claude: Path
    hermes: Path
    claude_global: Path
    hermes_soul: Path


def _skill_paths(paths: AgentPaths) -> tuple[Path, Path]:
    user_home = paths.codex_config.parent.parent
    skill_hub = Path(os.environ.get("SKILL_HUB_HOME", user_home / "AgentWorkspace" / "skill-hub"))
    return skill_hub.expanduser().resolve(), (user_home / ".agents" / "skills").resolve()


def _core_policy(paths: AgentPaths) -> str:
    skill_hub, global_skills = _skill_paths(paths)
    skillctl = skill_hub / "scripts" / "skillctl"
    return f"""# Agent Switch Runtime Policy

Agent Switch is the source of truth for local agent tools, MCP wrappers, and tool secrets on this machine. Skill Hub is the source of truth for local Skill source checkouts, version locks, and project activation profiles.

Secret and MCP rules:
- Store API keys, tokens, and MCP credentials only in `{paths.secrets_file}`.
- Do not write secrets into project `.env` files, README files, native app configs, chat transcripts, shell history, or logs.
- Pipe a secret-producing command into `agent-switch secret set --stdin NAME`, or use `agent-switch secret set --fd N NAME`; never pass the value as a command argument.
- Use `agent-switch secret get --fd N NAME` only with an inherited non-TTY descriptor that is not routed to stdout or stderr.
- Use `agent-switch secret list` to inspect available secret names without revealing values.
- Use `agent-switch doctor` before changing MCP/tool configuration.
- Use `agent-switch reconcile` to regenerate native app MCP configuration.
- Treat `{paths.config_file}` as the central tool and route configuration.
- Generated MCP entries and wrappers must stay in the `agent-*` namespace.
- If a requested provider or tool needs a new secret, add only the secret name to config and write the value through Agent Switch.
- Never print or paste secret values back to the user unless the user explicitly asks for a local-only diagnostic and redaction is impossible.

Skill Hub rules:
- Treat `{skill_hub}` as the optional local Skill control plane when it exists.
- Use `{skillctl} status` to inspect Skill source and profile state.
- Use `{skillctl} audit` for safe MCP / secret-name / Skill inventory reports; reports must list secret names only, never values.
- A downloaded Skill is dormant by default. It must not become callable until the user explicitly enables it for a project profile or the `global` profile.
- Use `{skillctl} profile-enable PROFILE SKILL --source SOURCE --path PATH` and `profile-disable PROFILE SKILL` to change per-project Skill activation.
- Use `{skillctl} sync PROFILE --prune` to activate project-local Skills through `.agents/skills` plus Codex / Claude / Hermes bridge directories and remove stale generated symlinks.
- Only when the user explicitly requests global activation, use `{skillctl} global-sync-official --prune` to refresh the global OpenAI official Skill baseline plus explicit `profiles/global.json` entries.
- Keep third-party Skills in one checkout under Skill Hub `vendor/` and lock their commit or tag before syncing projects.
- Keep self-authored Skills in Git-managed Skill Hub `own/` worktrees or dedicated GitHub repositories.
- Treat `{global_skills}` as generated activation output, not as the warehouse. Do not copy dormant Skills there manually.
- Do not run broad global installs such as `skills add ... -g --all` unless the user explicitly asks for global installation; prefer project profiles and symlinks.
- If non-profile global Skills exist unexpectedly, use `{skillctl} global-sync-official --prune` to restore the managed baseline before continuing.
- Never store credentials in Skill files, Skill references, Skill scripts, registry files, lock files, or audit reports.
"""


def codex_instructions(paths: AgentPaths) -> str:
    return _core_policy(paths) + """
Codex-specific rule:
- This file is loaded from `model_instructions_file`; every new Codex session should follow it.
"""


def claude_instructions(paths: AgentPaths) -> str:
    return _core_policy(paths) + """
Claude-specific rule:
- Keep global Claude Code behavior aligned with Agent Switch. If project-local `CLAUDE.md` files conflict on secret storage, the Agent Switch secret path wins.
"""


def hermes_instructions(paths: AgentPaths) -> str:
    return _core_policy(paths) + """
Hermes-specific rule:
- Hermes provider switching may be handled elsewhere, but MCP credentials and tool secrets remain managed by Agent Switch.
"""


def managed_block(body: str) -> str:
    return f"{MANAGED_START}\n{body.rstrip()}\n{MANAGED_END}\n"


def merge_managed_block(current_text: str, body: str) -> str:
    block = managed_block(body)
    start = current_text.find(MANAGED_START)
    end = current_text.find(MANAGED_END)
    if start != -1 and end != -1 and end > start:
        end += len(MANAGED_END)
        prefix = current_text[:start].rstrip()
        merged = (prefix + "\n\n" if prefix else "") + block + current_text[end:].lstrip("\n")
        return merged.rstrip() + "\n"
    base = current_text.rstrip()
    if not base:
        return block
    return base + "\n\n" + block


def desired_instruction_targets(paths: AgentPaths) -> InstructionTargets:
    return InstructionTargets(
        codex=paths.codex_instructions,
        claude=paths.claude_instructions,
        hermes=paths.hermes_instructions,
        claude_global=paths.claude_global_instructions,
        hermes_soul=paths.hermes_soul,
    )


def write_instructions(paths: AgentPaths, apps: set[str] | None = None) -> list[WriteResult]:
    selected = apps or set()
    targets = desired_instruction_targets(paths)
    results: list[WriteResult] = []
    if "codex" in selected:
        results.append(write_if_changed(targets.codex, codex_instructions(paths), mode=0o600, backup_dir=paths.backup_dir))
    if "claude" in selected:
        results.append(write_if_changed(targets.claude, claude_instructions(paths), mode=0o600, backup_dir=paths.backup_dir))
    if "hermes" in selected:
        results.append(write_if_changed(targets.hermes, hermes_instructions(paths), mode=0o600, backup_dir=paths.backup_dir))

    if "claude" in selected:
        claude_current = targets.claude_global.read_text(encoding="utf-8") if targets.claude_global.exists() else ""
        results.append(
            write_if_changed(
                targets.claude_global,
                merge_managed_block(claude_current, claude_instructions(paths)),
                backup_dir=paths.backup_dir,
            )
        )

    if "hermes" in selected:
        hermes_current = targets.hermes_soul.read_text(encoding="utf-8") if targets.hermes_soul.exists() else ""
        results.append(
            write_if_changed(
                targets.hermes_soul,
                merge_managed_block(hermes_current, hermes_instructions(paths)),
                mode=0o600,
                backup_dir=paths.backup_dir,
            )
        )
    return results
