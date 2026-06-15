# Agent Switch

Agent Switch is a local runtime layer for agent-owned MCP tools. It keeps CC Switch as the provider import and switching UI, while Agent Switch owns:

- central agent MCP tool definitions;
- a single local secrets file;
- wrapper commands that load secrets at runtime;
- drift repair for Claude Code, Claude Desktop, Codex, Hermes, and the CC Switch MCP database mirror.

The boundary is strict: Agent Switch only manages MCP IDs that start with `agent-`. It preserves every unrelated MCP entry and provider setting.

## Quick Start

Run from this directory:

```bash
PYTHONPATH=src python3 -m agent_switch doctor
PYTHONPATH=src python3 -m agent_switch reconcile
```

Use a fixture or test home instead of real app configs:

```bash
PYTHONPATH=src python3 -m agent_switch --home /tmp/as-home --user-home /tmp/as-user doctor --json --no-ccswitch
```

Preview a CC Switch link without applying it:

```bash
PYTHONPATH=src python3 -m agent_switch preview 'ccswitch://v1/import?resource=provider&app=claude&name=demo'
```

## Central Files

Default runtime paths:

- config: `~/.config/agent-switch/config.json`
- secrets: `~/.config/agent-switch/secrets.env`
- wrappers: `~/.config/agent-switch/mcp/bin/`
- backups: `~/.config/agent-switch/backups/`

The default tool set is:

- `agent-tavily`
- `agent-xcrawl`
- `agent-birdread`
- `agent-xurl-fallback`

## Operational Model

1. Import provider links into CC Switch as before.
2. Switch provider nodes in CC Switch as before.
3. Run `agent-switch doctor` to inspect MCP drift.
4. Run `agent-switch reconcile` to restore only `agent-*` MCP entries.

Provider keys stay in CC Switch. Tool secrets stay in the Agent Switch secrets file and are loaded only by wrapper scripts.

