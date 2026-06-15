from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlanChange:
    target: str
    path: Path | None
    action: str
    detail: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "target": self.target,
            "path": str(self.path) if self.path else None,
            "action": self.action,
            "detail": self.detail,
        }

