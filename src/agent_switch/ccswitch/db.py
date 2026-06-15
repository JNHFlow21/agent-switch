from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_switch.config.model import ManagedApps


REQUIRED_MCP_COLUMNS = {
    "id",
    "name",
    "server_config",
    "description",
    "homepage",
    "docs",
    "tags",
    "enabled_claude",
    "enabled_codex",
    "enabled_gemini",
    "enabled_opencode",
    "enabled_hermes",
}


class CcSwitchSchemaError(RuntimeError):
    pass


class CcSwitchDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpRow:
    id: str
    name: str
    server_config: dict[str, Any]
    apps: ManagedApps

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "serverConfig": self.server_config,
            "apps": self.apps.to_dict(),
        }


class CcSwitchDb:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def schema_columns(self) -> set[str]:
        if not self.path.exists():
            raise CcSwitchSchemaError(f"CC Switch database not found: {self.path}")
        with self._connect() as conn:
            rows = conn.execute("PRAGMA table_info(mcp_servers)").fetchall()
        if not rows:
            raise CcSwitchSchemaError("mcp_servers table is missing")
        return {str(row[1]) for row in rows}

    def ensure_schema(self) -> None:
        columns = self.schema_columns()
        missing = REQUIRED_MCP_COLUMNS - columns
        if missing:
            raise CcSwitchSchemaError(f"mcp_servers schema missing columns: {', '.join(sorted(missing))}")

    def list_mcp_servers(self) -> dict[str, McpRow]:
        self.ensure_schema()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, server_config, enabled_claude, enabled_codex, enabled_hermes
                FROM mcp_servers
                ORDER BY id ASC
                """
            ).fetchall()
        result: dict[str, McpRow] = {}
        for row in rows:
            try:
                server_config = json.loads(row[2]) if row[2] else {}
            except json.JSONDecodeError as exc:
                raise CcSwitchDataError(f"invalid server_config JSON for MCP row {row[0]}: {exc}") from exc
            result[row[0]] = McpRow(
                id=row[0],
                name=row[1],
                server_config=server_config,
                apps=ManagedApps(
                    claude=bool(row[3]),
                    claude_desktop=False,
                    codex=bool(row[4]),
                    hermes=bool(row[5]),
                ),
            )
        return result

    def upsert_agent_mcp_server(
        self,
        server_id: str,
        name: str,
        server_config: dict[str, Any],
        apps: ManagedApps,
    ) -> None:
        if not server_id.startswith("agent-"):
            raise ValueError(f"refusing to write non-agent MCP id: {server_id}")
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO mcp_servers (
                    id, name, server_config, description, homepage, docs, tags,
                    enabled_claude, enabled_codex, enabled_gemini, enabled_opencode, enabled_hermes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    server_id,
                    name,
                    json.dumps(server_config, ensure_ascii=False, sort_keys=True),
                    "Managed by Agent Switch.",
                    None,
                    None,
                    json.dumps(["agent-switch"], ensure_ascii=False),
                    bool(apps.claude),
                    bool(apps.codex),
                    False,
                    False,
                    bool(apps.hermes),
                ),
            )
