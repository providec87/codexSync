from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import time


class BackupManager:
    def __init__(
        self,
        backup_root: Path,
        machine_id: str | None,
        retention_days: int = 30,
        max_backups: int = 0,
    ) -> None:
        self._backup_root = backup_root
        self._retention_days = retention_days
        self._max_backups = max_backups
        safe_machine = _safe_machine_id(machine_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._snapshot_dir = self._backup_root / f"{safe_machine}-{ts}"

    def backup_file(self, file_path: Path, relative_path: str) -> Path | None:
        """
        Backups existing destination file before overwrite.
        Returns backup file path.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        backup_path = self._snapshot_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = self._deduplicate_path(backup_path)
        shutil.copy2(file_path, backup_path)
        return backup_path

    def prune(self) -> None:
        if not self._backup_root.exists():
            return

        snapshot_dirs = [path for path in self._backup_root.iterdir() if path.is_dir()]
        snapshot_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        now = time.time()
        if self._retention_days > 0:
            cutoff = now - (self._retention_days * 24 * 60 * 60)
            for path in snapshot_dirs:
                if path.stat().st_mtime < cutoff:
                    shutil.rmtree(path, ignore_errors=True)

        if self._max_backups > 0:
            snapshot_dirs = [path for path in self._backup_root.iterdir() if path.is_dir()]
            snapshot_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for stale in snapshot_dirs[self._max_backups :]:
                shutil.rmtree(stale, ignore_errors=True)

    @staticmethod
    def _deduplicate_path(path: Path) -> Path:
        if not path.exists():
            return path
        idx = 1
        candidate = path
        while candidate.exists():
            candidate = path.with_name(f"{path.stem}.{idx}{path.suffix}")
            idx += 1
        return candidate


def _safe_machine_id(raw: str | None) -> str:
    if not raw:
        return "unknown-machine"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw.strip())
    cleaned = cleaned.strip("-.")
    return cleaned or "unknown-machine"
