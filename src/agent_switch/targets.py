from __future__ import annotations

from pathlib import Path
import shutil

from agent_switch.paths import AgentPaths


def _real_user_command(paths: AgentPaths, command: str) -> bool:
    target_user_home = paths.codex_config.parent.parent.resolve()
    return target_user_home == Path.home().resolve() and shutil.which(command) is not None


def detected_apps(paths: AgentPaths) -> set[str]:
    user_home = paths.codex_config.parent.parent
    detected: set[str] = set()
    if paths.codex_config.parent.exists() or paths.codex_config.exists() or _real_user_command(paths, "codex"):
        detected.add("codex")
    if paths.claude_global_instructions.parent.exists() or paths.claude_config.exists() or _real_user_command(paths, "claude"):
        detected.add("claude")
    if (
        paths.hermes_config.parent.exists()
        or paths.hermes_config.exists()
        or paths.hermes_soul.exists()
        or _real_user_command(paths, "hermes")
    ):
        detected.add("hermes")
    if (
        paths.claude_desktop_config.exists()
        or (user_home / "Applications" / "Claude.app").exists()
        or (target_is_real_user(paths) and Path("/Applications/Claude.app").exists())
    ):
        detected.add("claude_desktop")
    return detected


def target_is_real_user(paths: AgentPaths) -> bool:
    return paths.codex_config.parent.parent.resolve() == Path.home().resolve()
