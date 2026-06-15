from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentPaths:
    agent_home: Path
    config_file: Path
    secrets_file: Path
    wrapper_dir: Path
    backup_dir: Path
    state_db: Path
    ccswitch_db: Path
    claude_config: Path
    claude_desktop_config: Path
    codex_config: Path
    hermes_config: Path


def default_agent_home() -> Path:
    override = os.environ.get("AGENT_SWITCH_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "agent-switch"


def paths_for(agent_home: str | Path | None = None, user_home: str | Path | None = None) -> AgentPaths:
    home = Path(agent_home).expanduser() if agent_home else default_agent_home()
    user = Path(user_home).expanduser() if user_home else Path.home()
    return AgentPaths(
        agent_home=home,
        config_file=home / "config.json",
        secrets_file=home / "secrets.env",
        wrapper_dir=home / "mcp" / "bin",
        backup_dir=home / "backups",
        state_db=home / "state.sqlite3",
        ccswitch_db=user / ".cc-switch" / "cc-switch.db",
        claude_config=user / ".claude.json",
        claude_desktop_config=user
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json",
        codex_config=user / ".codex" / "config.toml",
        hermes_config=user / ".hermes" / "config.yaml",
    )


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except PermissionError:
        # The caller will surface write failures later; chmod can fail on mounted stores.
        pass

