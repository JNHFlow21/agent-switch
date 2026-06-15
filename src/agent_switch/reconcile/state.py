from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplySummary:
    changed: int
    unchanged: int
    blocked: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"changed": self.changed, "unchanged": self.unchanged, "blocked": self.blocked}

