from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
from typing import Callable, Iterator

from agent_switch.atomic import WriteResult, write_if_changed
from agent_switch.config.loader import load_config, render_default_config
from agent_switch.config.model import AgentConfig, validate_config


@contextmanager
def _config_lock(config_path: Path) -> Iterator[None]:
    parent_existed = config_path.parent.exists()
    config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The default control-plane directory must be private, but a caller using
    # --config inside an existing project must not have that directory's mode
    # changed as a side effect.
    if not parent_existed:
        config_path.parent.chmod(0o700)
    lock_path = config_path.with_name(f".{config_path.name}.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def update_config(
    config_path: str | Path,
    default_secret_file: str | Path,
    backup_dir: str | Path,
    transform: Callable[[AgentConfig], AgentConfig],
) -> tuple[AgentConfig, WriteResult]:
    path = Path(config_path)
    with _config_lock(path):
        current = load_config(path, default_secret_file)
        updated = transform(current)
        validate_config(updated)
        result = write_if_changed(path, render_default_config(updated), mode=0o600, backup_dir=backup_dir)
    return updated, result
