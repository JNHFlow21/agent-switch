#!/usr/bin/env python3
"""Fail closed on common private-path and credential shapes without echoing values."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile("/" + r"Users/[^/\s]+"),
    re.compile("AK" + r"IA[0-9A-Z]{16}"),
    re.compile("gh" + r"[pousr]_[A-Za-z0-9]{20,}"),
    re.compile("sk" + r"-[A-Za-z0-9_-]{12,}"),
    re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def candidate_paths() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8", errors="strict"))
        if relative.parts and relative.parts[0] == "tests":
            continue
        paths.append(relative)
    return tuple(paths)


def main() -> int:
    findings: list[tuple[Path, int]] = []
    for relative in candidate_paths():
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append((relative, line_number))
    if findings:
        for path, line_number in findings:
            # Report location only. Never repeat the matched value into CI logs.
            print(f"potential private data at {path}:{line_number}", file=sys.stderr)
        return 1
    print("privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
