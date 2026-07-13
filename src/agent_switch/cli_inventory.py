from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass


@dataclass(frozen=True)
class CLIInfo:
    id: str
    name: str
    command: str
    manager: str
    version_args: tuple[str, ...]
    installed: bool
    path: str | None
    version: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "manager": self.manager,
            "versionArgs": list(self.version_args),
            "installed": self.installed,
            "path": self.path,
            "version": self.version,
        }


CLI_TARGETS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("agent-switch", "Agent Switch", "agent-switch", "Agent Switch", ("--version",)),
    ("codex", "Codex", "codex", "npm / app", ("--version",)),
    ("claude", "Claude Code", "claude", "native installer", ("--version",)),
    ("hermes", "Hermes", "hermes", "installer", ("--version",)),
    ("lark-cli", "Lark CLI", "lark-cli", "npm", ("--version",)),
    ("gh", "GitHub CLI", "gh", "Homebrew", ("--version",)),
    ("getnote", "Getnote", "getnote", "installer", ("--version",)),
    ("firecrawl", "Firecrawl", "firecrawl", "npm", ("--version",)),
    ("uv", "uv", "uv", "standalone / Homebrew", ("--version",)),
    ("brew", "Homebrew", "brew", "Homebrew", ("--version",)),
    ("npm", "npm", "npm", "Node.js", ("--version",)),
    ("pipx", "pipx", "pipx", "Homebrew / pip", ("--version",)),
    ("bun", "Bun", "bun", "standalone", ("--version",)),
    ("rustup", "Rustup", "rustup", "standalone", ("--version",)),
    ("yt-dlp", "yt-dlp", "yt-dlp", "Homebrew / pipx", ("--version",)),
)


def _safe_version(path: str, version_args: tuple[str, ...]) -> str | None:
    try:
        result = subprocess.run(
            [path, *version_args],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = result.stdout if result.stdout.strip() else result.stderr
    first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
    if not first_line:
        return None
    return first_line[:240]


def _inspect_target(target: tuple[str, str, str, str, tuple[str, ...]]) -> CLIInfo:
    item_id, name, command, manager, version_args = target
    path = shutil.which(command)
    return CLIInfo(
        id=item_id,
        name=name,
        command=command,
        manager=manager,
        version_args=version_args,
        installed=path is not None,
        path=path,
        version=_safe_version(path, version_args) if path else None,
    )


def cli_inventory() -> list[CLIInfo]:
    with ThreadPoolExecutor(max_workers=min(8, len(CLI_TARGETS))) as executor:
        return list(executor.map(_inspect_target, CLI_TARGETS))
