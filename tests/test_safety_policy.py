from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import unittest

from codexsync.app import ProcessSnapshot, _handle_running_codex
from codexsync.exceptions import FailSafeError, SafetyPreconditionError
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
    def __init__(self, terminate_ok: bool = True) -> None:
        self._terminate_ok = terminate_ok
        self.terminated: list[list[ProcessInfo]] = []

    def terminate(self, processes: list[ProcessInfo], timeout_seconds: int) -> bool:
        _ = timeout_seconds
        self.terminated.append(processes)
        return self._terminate_ok


def _build_cfg() -> AppConfig:
    return AppConfig(
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


class SafetyPolicyTests(unittest.TestCase):
    @patch("codexsync.app.sys.platform", "win32")
    def test_sandbox_detected_blocks_without_terminate(self) -> None:
        cfg = _build_cfg()
        detector = _DetectorStub()
        snapshot = ProcessSnapshot(
            main_processes=[ProcessInfo(pid=10, name="Codex.exe")],
            subprocesses=[],
            sandbox_detected=True,
        )
        with self.assertRaises(SafetyPreconditionError):
            _handle_running_codex(cfg, detector, snapshot, manual_override=None)
        self.assertEqual(detector.terminated, [])

    @patch("codexsync.app.sys.platform", "win32")
    @patch("codexsync.app.confirm_process_termination", return_value=True)
    def test_no_sandbox_prompts_and_terminates(self, _confirm_mock) -> None:
        cfg = _build_cfg()
        detector = _DetectorStub()
        main = [ProcessInfo(pid=10, name="Codex.exe")]
        snapshot = ProcessSnapshot(
            main_processes=main,
            subprocesses=[],
            sandbox_detected=False,
        )
        _handle_running_codex(cfg, detector, snapshot, manual_override=None)
        self.assertEqual(detector.terminated, [main])

    @patch("codexsync.app.sys.platform", "win32")
    @patch("codexsync.app.confirm_process_termination", return_value=True)
    def test_terminate_failure_returns_failsafe(self, _confirm_mock) -> None:
        cfg = _build_cfg()
        detector = _DetectorStub(terminate_ok=False)
        snapshot = ProcessSnapshot(
            main_processes=[ProcessInfo(pid=10, name="Codex.exe")],
            subprocesses=[],
            sandbox_detected=False,
        )
        with self.assertRaises(FailSafeError):
            _handle_running_codex(cfg, detector, snapshot, manual_override=None)


if __name__ == "__main__":
    unittest.main()
