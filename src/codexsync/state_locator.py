from __future__ import annotations

import os
from pathlib import Path

from .exceptions import ConfigError


def resolve_state_dirs(local_state_dir: Path | None, cloud_root_dir: Path) -> tuple[Path, Path]:
    """
    Validates and returns the pair of state directories participating in sync.
    """
    local = detect_local_state_dir(local_state_dir)
    cloud = cloud_root_dir.expanduser()

    if not cloud.exists():
        raise ConfigError(f"Cloud state dir does not exist: {cloud}")
    if not cloud.is_dir():
        raise ConfigError(f"Cloud state dir is not a directory: {cloud}")

    return local, cloud


def detect_local_state_dir(configured_path: Path | None) -> Path:
    candidates: list[Path] = []
    if configured_path:
        candidates.append(configured_path.expanduser())

    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home).expanduser())

    candidates.append(Path.home() / ".codex")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    tried = ", ".join(str(path) for path in candidates)
    raise ConfigError(f"Cannot detect Codex state directory. Tried: {tried}")
