from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|bearer|authorization)")
TOKEN_VALUE_RE = re.compile(
    r"(?ix)"
    r"(sk-[A-Za-z0-9_\-]{8,}|"
    r"xai-[A-Za-z0-9_\-]{8,}|"
    r"tvly-[A-Za-z0-9_\-]{8,}|"
    r"AIza[A-Za-z0-9_\-]{12,}|"
    r"[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"
)
ASSIGNMENT_RE = re.compile(r"(?i)((?:api[_-]?key|token|secret|password|authorization)\s*[=:]\s*)([^\s,'\"]+)")


def redact_text(value: str) -> str:
    redacted = TOKEN_VALUE_RE.sub("[REDACTED]", value)
    return ASSIGNMENT_RE.sub(r"\1[REDACTED]", redacted)


def redact_value(key: str | None, value: Any) -> Any:
    if isinstance(value, str):
        if key and SECRET_KEY_RE.search(key):
            return "[REDACTED]"
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(k): redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(key, item) for item in value]
    return value


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): redact_value(str(k), v) for k, v in value.items()}

