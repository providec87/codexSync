from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import uuid

from .backup import BackupManager
from .models import CopyAction, SyncPlan

LOG = logging.getLogger(__name__)


class SyncEngine:
    def __init__(
        self,
        backup_manager: BackupManager,
        temp_dir: Path,
        backup_before_overwrite: bool = True,
        fail_on_unknown: bool = True,
    ) -> None:
        self._backup_manager = backup_manager
        self._temp_dir = temp_dir
        self._backup_before_overwrite = backup_before_overwrite
        self._fail_on_unknown = fail_on_unknown

    def execute(self, plan: SyncPlan, dry_run: bool = True) -> None:
        if not dry_run:
            self._cleanup_orphaned_temp_files()
        for action in plan.to_local:
            self._copy(action, dry_run=dry_run)
        for action in plan.to_cloud:
            self._copy(action, dry_run=dry_run)
        if not dry_run:
            self._backup_manager.prune()

    def _copy(self, action: CopyAction, dry_run: bool) -> None:
        LOG.info("copy %s -> %s", action.src, action.dst)
        if dry_run:
            return

        self._ensure_parent(action.dst)

        if self._backup_before_overwrite and action.dst.exists():
            backup_path = self._backup_manager.backup_file(action.dst, action.relative_path)
            if backup_path:
                LOG.debug("backup created: %s", backup_path)

        staged = self._stage_copy(action)
        try:
            os.replace(staged, action.dst)
        except OSError:
            if self._fail_on_unknown:
                LOG.exception("atomic replace failed for staged file %s -> %s", staged, action.dst)
                raise
            try:
                shutil.copy2(staged, action.dst)
            except OSError:
                LOG.exception("fallback copy failed for staged file %s -> %s", staged, action.dst)
                raise
        finally:
            staged.unlink(missing_ok=True)

    @staticmethod
    def _ensure_parent(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _stage_copy(self, action: CopyAction) -> Path:
        candidate = action.dst.parent / f".{action.dst.name}.{uuid.uuid4().hex}.tmp"
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(action.src, candidate)
            return candidate
        except OSError:
            fallback = self._temp_dir / f"{action.relative_path}.{uuid.uuid4().hex}.tmp"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(action.src, fallback)
            return fallback

    def _cleanup_orphaned_temp_files(self) -> None:
        if not self._temp_dir.exists():
            return
        removed = 0
        for path in self._temp_dir.rglob("*.tmp"):
            if not path.is_file():
                continue
            path.unlink(missing_ok=True)
            removed += 1
        if removed:
            LOG.info("removed %d orphaned temporary file(s) in %s", removed, self._temp_dir)
