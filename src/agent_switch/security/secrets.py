from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re
from typing import Iterator

from agent_switch.atomic import write_if_changed
from agent_switch.config.model import AgentConfig

SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
MAX_SECRET_BYTES = 64 * 1024


@dataclass(frozen=True)
class SecretReport:
    path: Path
    exists: bool
    required: tuple[str, ...]
    missing: tuple[str, ...]
    present_names: tuple[str, ...]
    stored_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "exists": self.exists,
            "required": list(self.required),
            "missing": list(self.missing),
            "presentNames": list(self.present_names),
            "storedNames": list(self.stored_names),
        }


def _decode_double_quoted_value(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\" and index + 1 < len(value) and value[index + 1] in {'\\', '"', "$", "`"}:
            output.append(value[index + 1])
            index += 2
            continue
        output.append(character)
        index += 1
    return "".join(output)


def _decode_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if value.startswith(("'", '"')):
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("malformed quoted secret value")
        if value[0] == "'":
            return value[1:-1]
        return _decode_double_quoted_value(value[1:-1])
    return value


def _read_env_file_unlocked(env_path: Path) -> dict[str, str]:
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
        value = _decode_env_value(raw_value)
        if key:
            values[key] = value
    return values


def read_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.parent.exists():
        return {}
    with _secret_lock(env_path, exclusive=False):
        return _read_env_file_unlocked(env_path)


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


def _validate_secret_value(value: str) -> None:
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("secret value must be valid UTF-8") from exc
    if not encoded:
        raise ValueError("secret value must not be empty")
    if b"\x00" in encoded:
        raise ValueError("secret value must not contain NUL bytes")
    if b"\r" in encoded or b"\n" in encoded:
        raise ValueError("secret value must be a single line")
    if len(encoded) > MAX_SECRET_BYTES:
        raise ValueError(f"secret value exceeds the {MAX_SECRET_BYTES}-byte limit")


def _ensure_private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


@contextmanager
def _secret_lock(secret_path: Path, *, exclusive: bool = True) -> Iterator[None]:
    lock_path = secret_path.with_name(f".{secret_path.name}.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    locked = False
    try:
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        locked = True
        yield
    finally:
        try:
            if locked:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def set_secret(path: str | Path, name: str, value: str) -> None:
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid secret name: {name}")
    _validate_secret_value(value)
    secret_path = Path(path)
    _ensure_private_directory(secret_path.parent)
    with _secret_lock(secret_path):
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
        text = "\n".join(output).rstrip() + "\n"
        write_if_changed(secret_path, text, mode=0o600)
        # Atomic writes return early for identical content, so enforce the
        # private mode even when the value did not change. Fail closed.
        secret_path.chmod(0o600)


def get_secret(path: str | Path, name: str) -> str:
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid secret name: {name}")
    values = read_env_file(path)
    if name not in values:
        raise ValueError(f"secret not found: {name}")
    value = values[name]
    _validate_secret_value(value)
    return value


def delete_secret(path: str | Path, name: str) -> None:
    if not SECRET_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid secret name: {name}")
    secret_path = Path(path)
    if not secret_path.parent.exists():
        raise ValueError(f"secret not found: {name}")
    with _secret_lock(secret_path):
        if not secret_path.exists():
            raise ValueError(f"secret not found: {name}")
        lines = secret_path.read_text(encoding="utf-8").splitlines()
        output = [line for line in lines if _line_key(line) != name]
        if len(output) == len(lines):
            raise ValueError(f"secret not found: {name}")
        rendered = "\n".join(output).rstrip()
        text = rendered + "\n" if rendered else ""
        write_if_changed(secret_path, text, mode=0o600)
        secret_path.chmod(0o600)


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
        stored_names=tuple(sorted(name for name, value in values.items() if value)),
    )
