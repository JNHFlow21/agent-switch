from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_switch.config.model import AgentConfig


@dataclass(frozen=True)
class SecretReport:
    path: Path
    exists: bool
    required: tuple[str, ...]
    missing: tuple[str, ...]
    present_names: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "required": list(self.required),
            "missing": list(self.missing),
            "presentNames": list(self.present_names),
        }


def read_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def check_secrets(config: AgentConfig) -> SecretReport:
    required = tuple(sorted({name for tool in config.tools for name in tool.required_secrets}))
    values = read_env_file(config.secret_file)
    missing = tuple(name for name in required if not values.get(name))
    present = tuple(sorted(name for name in required if values.get(name)))
    return SecretReport(
        path=config.secret_file,
        exists=config.secret_file.exists(),
        required=required,
        missing=missing,
        present_names=present,
    )

