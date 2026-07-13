# Security Policy

## Report a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/JNHFlow21/agent-switch/security/advisories/new). Do not open a public issue containing a secret, credential, private path, or exploit detail.

## Secret handling contract

- Never commit `~/.config/agent-switch/secrets.env` or copy it into a repository.
- Never include secret values in issues, screenshots, logs, or diagnostic output.
- Use the macOS app or `agent-switch secret set --stdin NAME` to write a value.
- Use `agent-switch secret list` for audits; it returns names only.
- Rotate an affected provider credential immediately if exposure is suspected.

## Scope

Security reports should cover Agent Switch itself: secret storage and transport, generated wrappers, MCP config projection, instruction management, the native macOS app, and CC Switch compatibility behavior.

Third-party MCP servers, CLI tools, Skill sources, and providers keep their own security boundaries.
