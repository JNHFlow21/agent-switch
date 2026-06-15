# Recovery

Agent Switch writes atomically and stores backups under the Agent Switch backup directory when an existing file changes.

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

