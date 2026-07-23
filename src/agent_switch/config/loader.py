from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import AgentConfig, ConfigError, RouteConfig, ToolSpec, default_config, validate_config


def load_config(config_file: str | Path, default_secret_file: str | Path) -> AgentConfig:
    path = Path(config_file)
    if not path.exists():
        return default_config(Path(default_secret_file))
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid config JSON at {path}: {exc}") from exc

    secret_value = raw.get("secretFile", raw.get("secret_file", str(default_secret_file)))
    secret_file = Path(secret_value).expanduser()
    if not secret_file.is_absolute():
        secret_file = (path.parent / secret_file).resolve()
    tools = tuple(ToolSpec.from_mapping(item) for item in raw.get("tools", []))
    config = AgentConfig(
        tools=tools,
        routes=RouteConfig.from_mapping(raw.get("routes")),
        secret_file=secret_file,
    )
    validate_config(config)
    return config


def render_default_config(config: AgentConfig) -> str:
    return json.dumps(config.to_config_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
