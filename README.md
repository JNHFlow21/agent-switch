<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

# Agent Switch

**Define each MCP once. Store each credential once. Project both into every supported local AI agent.**

[![CI](https://github.com/JNHFlow21/agent-switch/actions/workflows/ci.yml/badge.svg)](https://github.com/JNHFlow21/agent-switch/actions/workflows/ci.yml)
[![macOS 14+](https://img.shields.io/badge/macOS-14%2B-111111?logo=apple)](https://www.apple.com/macos/)
[![License: MIT](https://img.shields.io/badge/license-MIT-111111.svg)](LICENSE)

Codex, Claude Code, Claude Desktop, and Hermes each keep their own MCP
configuration. Copying the same servers and credentials into every client
creates drift and spreads secrets across files.

Agent Switch replaces those copies with one local registry, one private
credential store, and deterministic per-agent projections.

> [!IMPORTANT]
> Agent Switch is **alpha software**. The current installer builds from source
> and requires Xcode. The intended public distribution is a Developer ID-signed,
> notarized GitHub Release installed through Homebrew Cask. That release channel
> is not available yet, so this README does not advertise a fake `brew` command.

## Quick start

### Prerequisites

- macOS 14 or newer
- Git
- Python 3.11 or newer
- [`pipx`](https://pipx.pypa.io/)
- Full Xcode with `xcodebuild`

Install missing command-line prerequisites with:

```bash
brew install python pipx
```

### Install

Run one verified source-install command:

```bash
git clone https://github.com/JNHFlow21/agent-switch.git && cd agent-switch && ./scripts/install.sh
```

The installer:

1. verifies macOS, Python, pipx, and Xcode;
2. installs the Python CLI in an isolated pipx environment;
3. builds and installs the native app at `~/Applications/Agent Switch.app`;
4. creates a neutral, empty Agent Switch config if none exists;
5. opens the app without adopting MCPs or rewriting native agent configs.

Expected first result:

```text
agent-switch --version  -> agent-switch 0.2.0
Native app              -> opens from ~/Applications/Agent Switch.app
```

Then preview your existing user-level command/stdio MCPs:

```bash
agent-switch mcp import --dry-run --json
agent-switch doctor
```

Review the detected MCP IDs, target apps, and required secret **names** before
running `agent-switch mcp import --adopt` or `agent-switch reconcile`.

<details>
<summary>Why not npm, NPX, or a public Homebrew command?</summary>

Agent Switch is a native macOS application with a Python CLI; Node.js is not
part of its runtime. npm/NPX would add an unrelated dependency and still need
to build or download the macOS app.

The correct end-user channel is:

```text
signed + notarized release artifact -> GitHub Releases -> Homebrew Cask
```

Until that artifact exists, the source installer above is the shortest honest
path. See the [roadmap](docs/roadmap.md).

</details>

## What changes for you

| Before Agent Switch | With Agent Switch |
| --- | --- |
| The same MCP is configured separately in every agent | Register it once and choose its target agents |
| API keys are copied into native client configs | Values remain in one private local store |
| A changed MCP silently drifts between clients | `doctor` reports drift; `reconcile` repairs it |
| Every MCP can inherit the entire shell environment | Each wrapper injects only its declared secret names |
| Existing config migration is an all-or-nothing edit | Preview first, then explicitly adopt with backups |

New installations start with an empty registry. Agent Switch does not install
the maintainer's preferred MCPs or request unrelated credentials.

## Core workflow

```bash
# 1. Preview supported user-level stdio MCPs without changing files
agent-switch mcp import --dry-run --json

# 2. Back up native configs and explicitly adopt the previewed MCPs
agent-switch mcp import --adopt

# 3. Write a credential locally without putting its value in argv or chat
secret-producing-command | agent-switch secret set --stdin SEARCH_API_KEY

# 4. Preview health and drift, then apply the central state
agent-switch doctor
agent-switch reconcile

# 5. Require a clean managed state
agent-switch doctor --strict
```

Never replace `secret-producing-command` with a literal secret in a recorded
command. The macOS app is the simplest interactive way to enter a value.

## What Agent Switch manages

| Area | Current behavior |
| --- | --- |
| **MCP servers** | Import, add, edit, target, enable, disable, remove, and reconcile user-level command/stdio MCPs |
| **Credentials** | Store values once and grant each MCP only its declared secret names |
| **Agent policy** | Synchronize bounded instruction blocks for Codex, Claude Code, and Hermes |
| **Health** | Detect invalid config, missing secret names, unpinned `npx` packages, blocked targets, and managed drift |
| **Recovery** | Write atomically and back up native files before migration or replacement |
| **CLI inventory** | Show installed AI tools, versions, package managers, and executable paths |
| **Skills** | Inventory optional Skill Hub sources without treating download as activation |
| **CC Switch** | Preserve provider switching and mirror only Agent Switch-owned MCP rows |

## How it works

```mermaid
flowchart LR
    UI["macOS app or CLI"] --> C["Central config"]
    C --> D["Doctor"]
    D --> R["Reconcile"]
    S["Private secret store"] --> W["Per-MCP wrappers"]
    R --> X["Secret-free agent configs"]
    W --> M["MCP processes"]
    X --> A["Codex"]
    X --> B["Claude Code / Desktop"]
    X --> H["Hermes"]
```

| Local source of truth | Default path |
| --- | --- |
| MCP definitions and grants | `~/.config/agent-switch/config.json` |
| Credential values | `~/.config/agent-switch/secrets.env` |
| Generated MCP wrappers | `~/.config/agent-switch/mcp/bin/` |
| Native config backups | `~/.config/agent-switch/backups/` |

Agent Switch owns only `agent-*` MCP entries and marked instruction blocks.
Unrelated provider and MCP settings are preserved.

## Supported integrations

| Integration | MCP sync | Shared policy | Inventory |
| --- | :---: | :---: | :---: |
| Codex | ✓ | ✓ | ✓ |
| Claude Code | ✓ | ✓ | ✓ |
| Claude Desktop | ✓ | — | — |
| Hermes | ✓ | ✓ | ✓ |
| CC Switch | Owned-row mirror | Provider settings preserved | Schema check |
| Skill Hub | Skill inventory/update | Explicit project/global profiles | ✓ |

A new agent requires a tested adapter. Agent Switch does not guess unknown
configuration formats.

## Credential and privacy boundaries

Agent Switch is local-first, but it is **not a password vault**.

- Credential values stay in a local mode-`0600` file, not in Git, app
  preferences, generated agent configs, or wrapper source.
- Secret writes use stdin or inherited file descriptors, never positional
  arguments.
- Secret reads refuse stdout, stderr, terminals, and aliased descriptors.
- Wrappers parse the store as data, remove inherited sensitive variables, and
  inject only the names granted to that MCP.
- Diagnostics, import previews, and audits report secret **names**, never
  values.
- Wrappers fail closed when a required secret name is missing.
- No upload service or cloud account is implemented. An MCP can still contact
  its own provider when an agent invokes it.

Read [Secrets and wrappers](docs/secrets-and-wrappers.md) and the
[Security Policy](SECURITY.md) before using sensitive credentials. Security
reports should follow the private reporting route in `SECURITY.md`, not a public
issue.

## Current alpha scope

Version 0.2 manages user-level command/stdio MCP definitions and static
credential values on macOS.

It does **not** yet provide:

- migration for native HTTP/SSE transports or OAuth sessions;
- project-scoped MCP discovery;
- automatic support for unknown agents;
- a signed and notarized downloadable app;
- a published Homebrew Cask or Python package;
- a password-manager or hardware-backed credential vault.

These are limitations, not hidden features. Planned work lives in the
[roadmap](docs/roadmap.md).

## Command reference

```bash
agent-switch agents               # detected agents and policy enrollment
agent-switch clis                 # installed AI CLI inventory
agent-switch mcp list             # central MCP registry
agent-switch secret list          # credential names only
agent-switch skills               # optional Skill Hub inventory
agent-switch doctor --json        # machine-readable health report
agent-switch reconcile --dry-run  # planned managed changes
```

Add a centrally managed MCP:

```bash
agent-switch mcp add filesystem \
  --command npx \
  --arg=-y \
  --arg=@modelcontextprotocol/server-filesystem@1.0.0 \
  --app codex \
  --app claude

agent-switch reconcile
```

See [Unified MCP Registry](docs/mcp-registry.md) for lifecycle commands and
safe import behavior.

## Update

From the cloned repository:

```bash
git pull --ff-only && ./scripts/install.sh
```

Agent Switch does not silently update itself, third-party CLIs, or Skill
sources.

## Documentation

- [Unified MCP Registry](docs/mcp-registry.md)
- [Secrets and wrappers](docs/secrets-and-wrappers.md)
- [CC Switch compatibility](docs/ccswitch-compat.md)
- [Recovery and rollback](docs/recovery.md)
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## Development

```bash
git clone https://github.com/JNHFlow21/agent-switch.git
cd agent-switch
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests
python -m unittest discover -s tests/integration
```

The native app lives in [`macos-app/AgentSwitch`](macos-app/AgentSwitch) and
targets macOS 14+. See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete test
and privacy gate.

## License

[MIT](LICENSE) © 2026 JNHFlow21
