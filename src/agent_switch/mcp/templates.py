from __future__ import annotations

import shlex

from agent_switch.config.model import ToolSpec


def render_wrapper_script(tool: ToolSpec, secret_file: str) -> str:
    required = " ".join(shlex.quote(name) for name in tool.required_secrets)
    command = " ".join(shlex.quote(part) for part in (tool.command, *tool.args))
    env_lines = "\n".join(f"export {shlex.quote(key)}={shlex.quote(value)}" for key, value in sorted(tool.env.items()))
    if env_lines:
        env_lines += "\n"
    if tool.required_secrets:
        secret_check = f"""declare -a required=({required})
missing=()
for name in "${{required[@]}}"; do
  if [ -z "${{!name:-}}" ]; then
    missing+=("$name")
  fi
done
"""
    else:
        secret_check = "missing=()\n"
    return f"""#!/usr/bin/env bash
set -euo pipefail

SECRET_FILE="${{AGENT_SWITCH_SECRETS:-{shlex.quote(secret_file)}}}"
if [ -f "$SECRET_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$SECRET_FILE"
  set +a
fi

{env_lines}{secret_check}
if [ "${{#missing[@]}}" -gt 0 ]; then
  printf 'Agent Switch wrapper {tool.id} missing required secret(s): %s\\n' "${{missing[*]}}" >&2
  exit 78
fi

exec {command} "$@"
"""
