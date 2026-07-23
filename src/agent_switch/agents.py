from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tomllib

from agent_switch.config.model import AgentConfig
from agent_switch.instructions import MANAGED_END, MANAGED_START
from agent_switch.paths import AgentPaths
from agent_switch.reconcile.doctor import run_doctor
from agent_switch.targets import detected_apps


def _command_detected(paths: AgentPaths, command: str) -> bool:
    target_user_home = paths.codex_config.parent.parent.resolve()
    return target_user_home == Path.home().resolve() and shutil.which(command) is not None


@dataclass(frozen=True)
class AgentStatus:
    id: str
    name: str
    detected: bool
    managed: bool
    in_sync: bool
    config_path: Path
    instruction_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "detected": self.detected,
            "managed": self.managed,
            "inSync": self.in_sync,
            "configPath": str(self.config_path),
            "instructionPath": str(self.instruction_path),
        }


def _contains_managed_block(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return MANAGED_START in text and MANAGED_END in text


def _codex_managed(paths: AgentPaths) -> bool:
    if not paths.codex_config.exists():
        return False
    try:
        data = tomllib.loads(paths.codex_config.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return data.get("model_instructions_file") == str(paths.codex_instructions)


def agent_statuses(config: AgentConfig, paths: AgentPaths) -> tuple[AgentStatus, ...]:
    report = run_doctor(config, paths, include_ccswitch=False)
    drift_targets = {change.target for change in report.changes}
    detected_targets = detected_apps(paths)
    definitions = (
        (
            "codex",
            "Codex",
            "codex" in detected_targets,
            _codex_managed(paths),
            paths.codex_config,
            paths.codex_instructions,
            {"codex", "instructions.codex"},
        ),
        (
            "claude",
            "Claude Code",
            "claude" in detected_targets,
            _contains_managed_block(paths.claude_global_instructions),
            paths.claude_config,
            paths.claude_global_instructions,
            {"claude", "instructions.claude", "instructions.claude_global"},
        ),
        (
            "hermes",
            "Hermes",
            "hermes" in detected_targets,
            _contains_managed_block(paths.hermes_soul),
            paths.hermes_config,
            paths.hermes_soul,
            {"hermes", "instructions.hermes", "instructions.hermes_soul"},
        ),
    )
    return tuple(
        AgentStatus(
            id=agent_id,
            name=name,
            detected=detected,
            managed=managed,
            in_sync=detected and managed and not bool(drift_targets & relevant_targets),
            config_path=config_path,
            instruction_path=instruction_path,
        )
        for agent_id, name, detected, managed, config_path, instruction_path, relevant_targets in definitions
    )
