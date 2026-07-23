# Recovery

Agent Switch writes atomically and stores backups under the Agent Switch backup directory when an existing file changes.
The backup directory is mode `0700` and backup files are mode `0600` because an
adopted native MCP config may have contained an inline credential.

## Failed Native Config Write

1. Run `agent-switch doctor --json`.
2. Check the blocked target and message.
3. Restore the relevant backup from `~/.config/agent-switch/backups/` if needed.
4. Fix the source file syntax if it is malformed.
5. Run `agent-switch doctor` again before `reconcile`.

## CC Switch Schema Drift

If `doctor` reports an incompatible `mcp_servers` schema, Agent Switch blocks database writes.

Native app writes should be treated as unsafe until the CC Switch adapter is updated against the new schema.

## Missing Secrets

Missing secrets are warnings, not config write blockers. The generated MCP entries can be repaired while the wrappers continue to fail closed at runtime until the missing names are added.

## Bad Agent Entry

Delete only the bad `agent-*` entry from the affected native config or CC Switch database, then run:

```bash
agent-switch reconcile
```

Agent Switch will recreate the entry from central config.

## Agent Enrollment

The macOS onboarding and Agent management page call the same `reconcile`
operation as the CLI. Existing Claude and Hermes instruction text outside the
Agent Switch managed block is preserved. Codex, MCP, and instruction target
files are written atomically and backed up under `~/.config/agent-switch/backups/`.

If enrollment does not converge, run `agent-switch agents --json` followed by
`agent-switch doctor --json` and restore only the affected target backup.

## MCP Import Or Adoption

Always preview first:

```bash
agent-switch mcp import --dry-run --json
```

`mcp import --adopt` validates all detected source formats before removing any
source entry. It then backs up each changed native file, migrates credential
values to the private store without printing them, and reconciles managed
projections. If adoption is interrupted, run `agent-switch doctor --json` and
restore only the affected private backup before retrying.
