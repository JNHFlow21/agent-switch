from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from agent_switch.config.model import AgentConfig

SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


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


def _quote_env_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@%+=,\-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    return f'"{escaped}"'


def _line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0].strip()
    return key if SECRET_NAME_RE.fullmatch(key) else None


def set_secret(path: str | Path, name: str, value: str) -> None:
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid secret name: {name}")
    secret_path = Path(path)
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    lines = secret_path.read_text(encoding="utf-8").splitlines() if secret_path.exists() else []
    rendered = f"{name}={_quote_env_value(value)}"
    replaced = False
    output: list[str] = []
    for line in lines:
        if _line_key(line) == name:
            output.append(rendered)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        if output and output[-1].strip():
            output.append("")
        output.append(rendered)
    secret_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    try:
        secret_path.chmod(0o600)
    except PermissionError:
        pass


def list_secret_names(path: str | Path) -> tuple[str, ...]:
    values = read_env_file(path)
    return tuple(sorted(name for name, value in values.items() if value))


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
