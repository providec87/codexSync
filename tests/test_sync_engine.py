from __future__ import annotations

from pathlib import Path
import shutil
import unittest
import uuid
import zipfile

from codexsync.backup import BackupManager
from codexsync.models import CopyAction, SyncPlan
from codexsync.sync_engine import SyncEngine


class SyncEngineTests(unittest.TestCase):
    def test_backup_before_overwrite(self) -> None:
        tmp_root = Path.cwd() / "test-sandbox"
        tmp_root.mkdir(parents=True, exist_ok=True)
        case_dir = tmp_root / f"sync-engine-{uuid.uuid4().hex}"
        case_dir.mkdir(parents=True, exist_ok=False)
        try:
            root = case_dir
            src = root / "src.txt"
            dst = root / "dst.txt"
            backup_root = root / "backups"
            temp_root = root / ".tmp"

            src.write_text("new-data", encoding="utf-8")
            dst.write_text("old-data", encoding="utf-8")

            action = CopyAction(src=src, dst=dst, relative_path="dst.txt")
            plan = SyncPlan(to_local=[action], to_cloud=[])

            manager = BackupManager(
                backup_root=backup_root,
                machine_id="machine-a",
                retention_days=7,
                max_backups=0,
            )
            engine = SyncEngine(
                backup_manager=manager,
                temp_dir=temp_root,
                backup_before_overwrite=True,
                fail_on_unknown=True,
            )
            engine.execute(plan, dry_run=False)

            self.assertEqual(dst.read_text(encoding="utf-8"), "new-data")
            backup_files = [p for p in backup_root.rglob("*") if p.is_file()]
            self.assertEqual(len(backup_files), 1)
            self.assertEqual(backup_files[0].read_text(encoding="utf-8"), "old-data")
        finally:
            shutil.rmtree(case_dir, ignore_errors=True)

    def test_backup_before_overwrite_with_zip_compression(self) -> None:
        tmp_root = Path.cwd() / "test-sandbox"
        tmp_root.mkdir(parents=True, exist_ok=True)
        case_dir = tmp_root / f"sync-engine-zip-{uuid.uuid4().hex}"
        case_dir.mkdir(parents=True, exist_ok=False)
        try:
            root = case_dir
            src = root / "src.txt"
            dst = root / "dst.txt"
            backup_root = root / "backups"
            temp_root = root / ".tmp"

            src.write_text("new-data", encoding="utf-8")
            dst.write_text("old-data", encoding="utf-8")

            action = CopyAction(src=src, dst=dst, relative_path="dst.txt")
            plan = SyncPlan(to_local=[action], to_cloud=[])

            manager = BackupManager(
                backup_root=backup_root,
                machine_id="machine-a",
                retention_days=7,
                max_backups=0,
                compression="zip",
            )
            engine = SyncEngine(
                backup_manager=manager,
                temp_dir=temp_root,
                backup_before_overwrite=True,
                fail_on_unknown=True,
            )
            engine.execute(plan, dry_run=False)

            self.assertEqual(dst.read_text(encoding="utf-8"), "new-data")
            backup_zips = list(backup_root.glob("*.zip"))
            self.assertEqual(len(backup_zips), 1)
            with zipfile.ZipFile(backup_zips[0], "r") as zf:
                self.assertEqual(zf.namelist(), ["dst.txt"])
                self.assertEqual(zf.read("dst.txt").decode("utf-8"), "old-data")
        finally:
            shutil.rmtree(case_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
