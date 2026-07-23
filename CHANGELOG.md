# Changelog

All notable changes to Agent Switch are documented here.

## 0.2.0 - Unreleased

### Added

- Neutral empty registry for new installations.
- Unified MCP `list`, `add`, `set`, `enable`, `disable`, `remove`, and native
  `import`/`--adopt` commands.
- macOS MCP editor, target selection, import/adoption, enable/disable, and
  removal actions.
- Native import preview showing MCP IDs and secret names before adoption.
- Credential-to-MCP consumer mapping in status and the Secret UI.
- Detected-agent-only reconciliation for clean first-run behavior.

### Security

- Generated wrappers no longer source or export the complete secret store.
- Each MCP receives only its declared credentials; inherited sensitive
  variables and unrelated stored credentials are removed.
- Native-config adoption backs up files privately before removing inline MCPs.
- Backup names include both target-path and content digests to prevent collisions.
- Credential-shaped stdio arguments are migrated to declared secret placeholders.
- Positional secret values are rejected.
- Doctor warns about unpinned `npx` packages.

### Changed

- The macOS app prefers an installed Agent Switch CLI and no longer requires a
  source checkout when that CLI is available.
- `doctor --strict` now fails for drift or missing required credentials as well
  as blocked targets.

## 0.1.3 - 2026-07-13

- Initial public repository preparation with CLI, native dashboard, secret
  operations, MCP projections, Skill inventory, and CC Switch compatibility.
