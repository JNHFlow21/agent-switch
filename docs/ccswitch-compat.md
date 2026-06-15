# CC Switch Compatibility

Agent Switch does not take over the `ccswitch://` URL scheme. Provider, prompt, and skill links are previewed and then forwarded to CC Switch.

MCP links are different: Agent Switch can normalize an MCP deep link into `agent-*` tool definitions so CC Switch and native app configs only see wrapper-backed commands.

## Database Mirror

The CC Switch database is treated as an external mirror. Agent Switch writes only rows whose `id` starts with `agent-`.

Before writing, Agent Switch checks that `mcp_servers` has the expected columns:

- `id`
- `name`
- `server_config`
- `description`
- `homepage`
- `docs`
- `tags`
- `enabled_claude`
- `enabled_codex`
- `enabled_gemini`
- `enabled_opencode`
- `enabled_hermes`

If the schema does not match, database writes are blocked and reported by `doctor`.

## Native Config Projection

Agent Switch writes only agent-owned MCP entries into:

- Claude Code JSON MCP config;
- Claude Desktop JSON MCP config;
- Codex TOML `mcp_servers` entries;
- Hermes YAML `mcp_servers` entries.

Provider fields, CC Switch deployment mode, and unrelated MCP entries are preserved.

