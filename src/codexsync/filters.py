from __future__ import annotations

from pathlib import PurePosixPath


class PathFilter:
    def __init__(self, exclude_globs: list[str]) -> None:
        self._exclude_globs = exclude_globs

    def is_excluded(self, rel_path: str) -> bool:
        path = PurePosixPath(rel_path.replace("\\", "/"))
        return any(path.match(pattern) for pattern in self._exclude_globs)
