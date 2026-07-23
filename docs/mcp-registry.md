# Unified MCP Registry

Agent Switch treats `~/.config/agent-switch/config.json` as the source of truth
for MCP definitions and `~/.config/agent-switch/secrets.env` as the source of
truth for credential values.

## Neutral first run

A new registry is empty. Agent Switch does not preinstall search, social, or
provider-specific MCPs and does not request unrelated credentials.

```bash
agent-switch write-default-config
agent-switch mcp list
```

## Import and adoption

Preview MCPs found in Claude Code, Claude Desktop, Codex, and Hermes:

```bash
agent-switch mcp import --dry-run --json
```

Adoption is explicit:

```bash
agent-switch mcp import --adopt
```

The adopt flow validates every source first, classifies credential-shaped
environment names, stores their values without printing them, backs up the
native files, removes the imported source entries, and reconciles wrapper-backed
`agent-*` projections. Non-secret environment values stay in central config.
The native app performs this same dry-run first and shows the MCP IDs and secret
names before the user can confirm adoption.

Version 0.2 imports user-level command/stdio entries. It deliberately does not
rewrite native HTTP/SSE or OAuth definitions into an unverified transport
bridge. Those transports need a dedicated adapter that preserves each client's
authentication semantics; see the roadmap. Discovery reports those entries as
`skipped` by app and ID, and adoption leaves them untouched.

## Registry lifecycle

```bash
agent-switch mcp add NAME --command COMMAND [--arg ARG] [--secret NAME] [--app APP]
agent-switch mcp set NAME --command COMMAND [options]
agent-switch mcp enable NAME
agent-switch mcp disable NAME
agent-switch mcp remove NAME
agent-switch mcp list --json
```

Supported app IDs are `claude`, `claude_desktop`, `codex`, and `hermes`.
Disabling an MCP removes its managed projections and stale wrapper on the next
reconcile without deleting stored credential values.

`--env NAME=VALUE` is only for non-secret settings. Names that look like keys,
tokens, passwords, credentials, or authentication values are rejected and must
be declared with `--secret NAME`; their values are written separately through
the Secret UI or `agent-switch secret set --stdin NAME`.

## Ownership

Agent Switch owns only `agent-*` entries and its marked instruction blocks.
Unrelated native configuration is preserved. Existing files are written
atomically and backups are kept in the private mode-`0700` backup directory.
