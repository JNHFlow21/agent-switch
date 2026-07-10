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

Use the CLI to add or update secrets:

```bash
secret-producing-command | agent-switch secret set --stdin FIRECRAWL_API_KEY
agent-switch secret set --fd 3 FIRECRAWL_API_KEY 3< <(secret-producing-command)
agent-switch secret list
```

`--stdin` and `--fd` keep the value out of the Agent Switch process arguments.
Replace `secret-producing-command` with a program that emits the value; never
replace that placeholder with the value itself. The legacy
`secret set NAME VALUE` form is deprecated in 0.1.3 and will be removed after
this compatibility release.

Secret input must be non-empty, single-line UTF-8 no larger than 64 KiB. The
CLI removes one final LF or CRLF from a producer. `--stdin` rejects interactive
TTY input, and `--fd` accepts inherited read descriptors numbered 3 or higher.

`secret list` prints names only. It does not print values.

## Global Instructions

`reconcile` also maintains global runtime instructions so new Codex, Claude Code, and Hermes sessions know where secrets and MCP configuration belong.

Managed files:

```text
~/.config/agent-switch/instructions/AGENTS.md
~/.config/agent-switch/instructions/CLAUDE.md
~/.config/agent-switch/instructions/HERMES.md
```

Native app integration:

- Codex: `~/.codex/config.toml` points `model_instructions_file` at the Agent Switch `AGENTS.md`.
- Claude Code: `~/.claude/CLAUDE.md` receives a managed Agent Switch block.
- Hermes: `~/.hermes/SOUL.md` receives a managed Agent Switch block.

These instructions are policy only. The source of truth remains `secrets.env`, wrapper scripts, and generated native MCP config.

## Wrapper Behavior

Each wrapper:

1. loads the secrets file if present;
2. validates required secret names;
3. prints missing names only;
4. executes the configured MCP command.

Wrappers are deterministic so `reconcile` can skip unchanged writes.
