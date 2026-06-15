from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path


class SafeWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteResult:
    path: Path
    changed: bool
    backup_path: Path | None
    sha256: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def backup_path_for(path: Path, backup_dir: Path, source_digest: str | None = None) -> Path:
    digest = sha256_bytes(str(path).encode("utf-8"))[:12]
    if source_digest:
        digest = source_digest[:12]
    name = f"{path.name}.{digest}.bak"
    return backup_dir / name


def write_if_changed(
    path: str | Path,
    text: str,
    *,
    mode: int | None = None,
    backup_dir: str | Path | None = None,
) -> WriteResult:
    target = Path(path)
    data = text.encode("utf-8")
    digest = sha256_bytes(data)

    try:
        existing_data = target.read_bytes() if target.exists() else None
        if existing_data == data:
            return WriteResult(target, False, None, digest)

        target.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        if target.exists() and backup_dir is not None:
            backup_root = Path(backup_dir)
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_path = backup_path_for(target, backup_root, sha256_bytes(existing_data or b""))
            shutil.copy2(target, backup_path)

        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if mode is None and target.exists():
                mode = stat.S_IMODE(target.stat().st_mode)
            if mode is not None:
                os.chmod(tmp_name, mode)
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
    except OSError as exc:
        raise SafeWriteError(f"failed to write {target}: {exc}") from exc

    return WriteResult(target, True, backup_path, digest)
