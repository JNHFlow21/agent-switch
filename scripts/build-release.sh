#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
VERSION="$(<"$ROOT/VERSION")"
PROJECT="$ROOT/macos-app/AgentSwitch/AgentSwitch.xcodeproj"
SCHEME="AgentSwitch"
OUTPUT_DIR="${1:-$ROOT/dist}"
DERIVED_DATA="$(mktemp -d "${TMPDIR:-/tmp}/agent-switch-release.XXXXXX")"
APP="$DERIVED_DATA/Build/Products/Release/Agent Switch.app"
ARCHIVE="$OUTPUT_DIR/Agent-Switch-$VERSION-macos-universal.zip"

cleanup() {
  rm -rf "$DERIVED_DATA"
}
trap cleanup EXIT

fail() {
  print -u2 "Agent Switch release build failed: $*"
  exit 1
}

[[ "$(uname -s)" == "Darwin" ]] || fail "macOS is required."
for command in xcodebuild codesign ditto lipo shasum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required."
done

mkdir -p "$OUTPUT_DIR"
rm -f "$ARCHIVE" "$ARCHIVE.sha256"

xcodebuild \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration Release \
  -destination "generic/platform=macOS" \
  -derivedDataPath "$DERIVED_DATA" \
  -quiet \
  ARCHS="arm64 x86_64" \
  ONLY_ACTIVE_ARCH=NO \
  CODE_SIGNING_ALLOWED=NO \
  build

[[ -d "$APP" ]] || fail "Xcode did not produce $APP"

APP_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist")"
[[ "$APP_VERSION" == "$VERSION" ]] || fail "App version $APP_VERSION does not match VERSION $VERSION."

ARCHS="$(lipo -archs "$APP/Contents/MacOS/Agent Switch")"
[[ " $ARCHS " == *" arm64 "* ]] || fail "Release is missing arm64."
[[ " $ARCHS " == *" x86_64 "* ]] || fail "Release is missing x86_64."

# The public alpha is intentionally ad-hoc signed until a Developer ID is
# available. Homebrew installation documents the resulting Gatekeeper tradeoff.
xattr -cr "$APP"
codesign --force --sign - --options runtime --timestamp=none "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

ditto -c -k --sequesterRsrc --keepParent "$APP" "$ARCHIVE"
(cd "$OUTPUT_DIR" && shasum -a 256 "${ARCHIVE:t}" > "${ARCHIVE:t}.sha256")

print "Built $ARCHIVE"
print "Architectures: $ARCHS"
print "Signing: ad-hoc (not notarized)"
