from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import time
import zipfile


class BackupManager:
    def __init__(
        self,
        backup_root: Path,
        machine_id: str | None,
        retention_days: int = 30,
        max_backups: int = 0,
        compression: str = "none",
    ) -> None:
        self._backup_root = backup_root
        self._retention_days = retention_days
        self._max_backups = max_backups
        self._compression = compression
        safe_machine = _safe_machine_id(machine_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._snapshot_path = (
            self._backup_root / f"{safe_machine}-{ts}.zip"
            if self._compression == "zip"
            else self._backup_root / f"{safe_machine}-{ts}"
        )
        self._zip_entries: set[str] = set()

    def backup_file(self, file_path: Path, relative_path: str) -> Path | None:
        """
        Backups existing destination file before overwrite.
        Returns backup file path.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        if self._compression == "zip":
            return self._backup_file_zip(file_path, relative_path)

        backup_path = self._snapshot_path / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = self._deduplicate_path(backup_path)
        shutil.copy2(file_path, backup_path)
        return backup_path

    def prune(self) -> None:
        if not self._backup_root.exists():
            return

        snapshots = [path for path in self._backup_root.iterdir() if path.is_dir() or _is_snapshot_zip(path)]
        snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        now = time.time()
        if self._retention_days > 0:
            cutoff = now - (self._retention_days * 24 * 60 * 60)
            for path in snapshots:
                if path.stat().st_mtime < cutoff:
                    _remove_snapshot(path)

        if self._max_backups > 0:
            snapshots = [path for path in self._backup_root.iterdir() if path.is_dir() or _is_snapshot_zip(path)]
            snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for stale in snapshots[self._max_backups :]:
                _remove_snapshot(stale)

    def _backup_file_zip(self, file_path: Path, relative_path: str) -> Path:
        snapshot_zip = self._snapshot_path
        snapshot_zip.parent.mkdir(parents=True, exist_ok=True)
        arcname = relative_path.replace("\\", "/")
        arcname = self._deduplicate_zip_entry(arcname)
        with zipfile.ZipFile(snapshot_zip, mode="a", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, arcname=arcname)
        return snapshot_zip

    def _deduplicate_zip_entry(self, arcname: str) -> str:
        if arcname not in self._zip_entries:
            self._zip_entries.add(arcname)
            return arcname

        candidate = arcname
        stem, dot, suffix = candidate.rpartition(".")
        if not dot:
            stem, suffix = candidate, ""
        idx = 1
        while candidate in self._zip_entries:
            if suffix:
                candidate = f"{stem}.{idx}.{suffix}"
            else:
                candidate = f"{stem}.{idx}"
            idx += 1
        self._zip_entries.add(candidate)
        return candidate

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


def _is_snapshot_zip(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".zip"


def _remove_snapshot(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return
    if _is_snapshot_zip(path):
        path.unlink(missing_ok=True)
