# Secrets And Wrappers

Agent Switch keeps secrets out of generated app configs by using wrapper commands.

Native app configs and CC Switch rows contain:

- wrapper command path;
- non-secret args.

They do not contain:

- API keys;
- tokens;
- bearer values;
- per-tool secret values.

## Secrets File

Default path:

```bash
~/.config/agent-switch/secrets.env
```

Example shape:

```bash
TAVILY_API_KEY=...
XCRAWL_API_KEY=...
BIRDREAD_API_KEY=...
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

The status output reports missing secret names only. It never prints values.

## Wrapper Behavior

Each wrapper:

1. loads the secrets file if present;
2. validates required secret names;
3. prints missing names only;
4. executes the configured MCP command.

Wrappers are deterministic so `reconcile` can skip unchanged writes.

