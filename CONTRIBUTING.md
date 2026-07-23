# Contributing

Agent Switch manages security-sensitive local configuration. Changes should be
small, testable, and preserve unrelated native configuration.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m unittest discover -s tests/integration
swift build --package-path macos-app/AgentSwitch
python3 scripts/privacy_scan.py
```

## Required boundaries

- Never commit or print real credential values.
- MCPs may receive only the credentials they explicitly declare.
- Manage only the `agent-*` namespace and marked instruction blocks.
- Import/adoption changes require preview, validation, atomic writes, and
  private backups.
- A clean user home must remain neutral until the user explicitly acts.

Open an issue before adding a new agent adapter or changing a native config
ownership boundary.
