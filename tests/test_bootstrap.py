from __future__ import annotations

from pathlib import Path
import shutil
import unittest
import uuid

from codexsync.app import initialize_runtime_paths
from codexsync.models import (
    AppConfig,
    BackupConfig,
    ConflictConfig,
    FiltersConfig,
    IdentityConfig,
    LoggingConfig,
    PathsConfig,
    ProcessDetectionConfig,
    SafetyConfig,
    StateConfig,
    SyncConfig,
    TargetsConfig,
)


class BootstrapTests(unittest.TestCase):
    def test_initialize_runtime_paths_creates_dirs_and_files(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"bootstrap-{uuid.uuid4().hex}"
        local_state = root / "local-state"
        cloud_root = root / "sync"
        backup_root = root / "backups"
        temp_root = root / ".tmp"
        manifest_file = root / "state" / "manifest.json"
        log_file = root / "logs" / "codexsync.log"

        local_state.mkdir(parents=True, exist_ok=True)
        try:
            cfg = AppConfig(
                identity=IdentityConfig(machine_id="machine-a"),
                paths=PathsConfig(
                    workspace_root_dir=root,
                    local_state_dir=local_state,
                    cloud_root_dir=cloud_root,
                    backup_dir=backup_root,
                    temp_dir=temp_root,
                ),
                sync=SyncConfig(),
                safety=SafetyConfig(),
                process_detection=ProcessDetectionConfig(),
                backup=BackupConfig(),
                filters=FiltersConfig(),
                targets=TargetsConfig(
                    include_roots=[
                        "sessions",
                        "skills",
                        "plugins",
                        "session_index.jsonl",
                    ]
                ),
                conflict=ConflictConfig(),
                state=StateConfig(manifest_file=manifest_file, data_version=1),
                logging=LoggingConfig(file=log_file),
            )

            initialize_runtime_paths(cfg)

            self.assertTrue(cloud_root.is_dir())
            self.assertTrue(backup_root.is_dir())
            self.assertTrue(temp_root.is_dir())
            self.assertTrue(log_file.is_file())
            self.assertTrue(manifest_file.is_file())
            self.assertTrue((cloud_root / "sessions").is_dir())
            self.assertTrue((cloud_root / "skills").is_dir())
            self.assertTrue((cloud_root / "plugins").is_dir())
            self.assertTrue((cloud_root / "session_index.jsonl").parent.is_dir())
            self.assertFalse((cloud_root / "session_index.jsonl").exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
