from __future__ import annotations

from pathlib import Path
import unittest

from codexsync.app import collect_process_snapshot
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
from codexsync.process_detector import ProcessInfo


class _DetectorStub:
    def __init__(self, main: list[ProcessInfo], children: list[ProcessInfo]) -> None:
        self._main = main
        self._children = children

    def get_subprocess_tree(self, _parent_process_names: list[str]) -> tuple[list[ProcessInfo], list[ProcessInfo]]:
        return self._main, self._children

    def has_marker(self, _proc: ProcessInfo, _marker_name: str) -> bool:
        return False


class ProcessSnapshotTests(unittest.TestCase):
    def test_windows_fallback_detects_enable_sandbox_flag(self) -> None:
        cfg = AppConfig(
            identity=IdentityConfig(machine_id="machine-a"),
            paths=PathsConfig(
                workspace_root_dir=Path("D:/x"),
                local_state_dir=Path("C:/Users/user/.codex"),
                cloud_root_dir=Path("D:/x/sync"),
                backup_dir=Path("D:/x/backups"),
                temp_dir=Path("D:/x/.tmp"),
            ),
            sync=SyncConfig(),
            safety=SafetyConfig(),
            process_detection=ProcessDetectionConfig(),
            backup=BackupConfig(),
            filters=FiltersConfig(),
            targets=TargetsConfig(),
            conflict=ConflictConfig(),
            state=StateConfig(data_version=1),
            logging=LoggingConfig(),
        )
        detector = _DetectorStub(
            main=[ProcessInfo(pid=100, name="Codex.exe")],
            children=[
                ProcessInfo(
                    pid=101,
                    name="Codex.exe",
                    command_line='"Codex.exe" --type=renderer --enable-sandbox',
                    parent_pid=100,
                )
            ],
        )

        snapshot = collect_process_snapshot(cfg, detector=detector)
        self.assertTrue(snapshot.sandbox_detected)


if __name__ == "__main__":
    unittest.main()
