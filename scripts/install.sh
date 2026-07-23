#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"

fail() {
  print -u2 "Agent Switch install failed: $*"
  exit 1
}

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required."
command -v python3 >/dev/null 2>&1 || fail "Python 3.11 or newer is required."
command -v pipx >/dev/null 2>&1 || fail "pipx is required. Install it with: brew install pipx"
command -v xcodebuild >/dev/null 2>&1 || fail "Full Xcode with xcodebuild is required."

python3 - <<'PY' || fail "Python 3.11 or newer is required."
import sys

raise SystemExit(sys.version_info < (3, 11))
PY

xcodebuild -version >/dev/null 2>&1 || fail "Select a full Xcode installation with xcode-select."

print "Installing Agent Switch CLI..."
if ! pipx install --force "$ROOT"; then
  print "The existing pipx environment could not be refreshed; recreating it..."
  pipx uninstall agent-switch >/dev/null 2>&1 || true
  pipx install "$ROOT"
fi

PIPX_BIN_DIR="$(pipx environment --value PIPX_BIN_DIR)"
CLI="$PIPX_BIN_DIR/agent-switch"
[[ -x "$CLI" ]] || fail "pipx installed the package but the agent-switch executable was not found."
"$CLI" --version

print "Building and installing the native macOS app..."
"$ROOT/macos-app/AgentSwitch/install.sh"

"$CLI" write-default-config

cat <<EOF

Agent Switch is installed.

App: ~/Applications/Agent Switch.app
CLI: $CLI

Next:
  agent-switch mcp import --dry-run --json
  agent-switch doctor

Review the import preview before adopting existing MCPs or reconciling native configs.
EOF
