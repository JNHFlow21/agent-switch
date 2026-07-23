# Roadmap

Agent Switch's product goal is one control plane for MCP definitions and static
credential values across local AI agents. The project documents incomplete
boundaries explicitly instead of treating a successful demo as a finished
distribution.

## 0.2 foundation

- Neutral first run with no maintainer-specific MCPs or credentials.
- Central lifecycle for user-level command/stdio MCPs.
- Explicit import preview and backed-up adoption from supported agents.
- One private credential store with per-MCP least-privilege wrappers.
- Detected-target-only reconciliation, strict health checks, CI, and package
  build validation.

## Before stable 1.0

1. Normalize native Streamable HTTP and SSE MCP definitions without losing
   client-specific OAuth behavior; migrate static header credentials without
   printing or duplicating their values.
2. Discover project/local MCP scopes separately from user scope and require an
   explicit ownership choice before adoption.
3. Add adapters through a documented contract and fixture suite rather than
   guessing unknown agent configuration formats.
4. Ship a signed and notarized macOS release, a verified installer, published
   Python packages, and a Homebrew path.
5. Add complete English and Chinese localization plus a first-run wizard that
   previews targets, MCP IDs, and secret names before any write.
6. Add a first-class backup browser and guided restore flow.
