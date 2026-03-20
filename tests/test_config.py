from __future__ import annotations

from pathlib import Path
import shutil
import textwrap
import unittest
import uuid

from codexsync.config import load_config


class ConfigTests(unittest.TestCase):
    def test_workspace_root_substitution(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"config-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            cfg_path = root / "config.toml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    [identity]
                    machine_id = "machine-a"

                    [sync]
                    mode = "cold"
                    direction = "bidirectional"
                    compare = "mtime"
                    delete_policy = "never"

                    [paths]
                    workspace_root_dir = "D:/codexSync"
                    local_state_dir = "C:/Users/user/.codex_test"
                    cloud_root_dir = "${workspace_root}/sync"
                    backup_dir = "${workspace_root}/backups"
                    temp_dir = "${workspace_root}/.tmp"

                    [state]
                    manifest_file = "${workspace_root}/state/manifest.json"
                    data_version = 1

                    [logging]
                    file = "${workspace_root}/logs/codexsync.log"
                    format = "text"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            cfg = load_config(cfg_path)
            self.assertEqual(str(cfg.paths.workspace_root_dir), "D:\\codexSync")
            self.assertEqual(str(cfg.paths.cloud_root_dir), "D:\\codexSync\\sync")
            self.assertEqual(str(cfg.paths.backup_dir), "D:\\codexSync\\backups")
            self.assertEqual(str(cfg.paths.temp_dir), "D:\\codexSync\\.tmp")
            assert cfg.state.manifest_file is not None
            self.assertEqual(str(cfg.state.manifest_file), "D:\\codexSync\\state\\manifest.json")
            assert cfg.logging.file is not None
            self.assertEqual(str(cfg.logging.file), "D:\\codexSync\\logs\\codexsync.log")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_background_process_names_by_os(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"config-bg-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            cfg_path = root / "config.toml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    [sync]
                    mode = "cold"
                    direction = "bidirectional"
                    compare = "mtime"
                    delete_policy = "never"

                    [paths]
                    cloud_root_dir = "sync"
                    backup_dir = "backups"
                    temp_dir = ".tmp"

                    [process_detection]
                    process_names = ["Codex.EXE", "CODEX", "codex"]
                    terminate_confirmation_mode = "CONSOLE"

                    [process_detection.background_process_names]
                    windows = ["codex-windows-sandbox", "codex-gpu-helper.exe"]
                    macos = ["codex-macos-helper"]
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            cfg = load_config(cfg_path)
            self.assertEqual(cfg.process_detection.process_names, ["codex.exe", "codex"])
            self.assertEqual(cfg.process_detection.terminate_confirmation_mode, "console")
            self.assertEqual(
                cfg.process_detection.background_process_names["windows"],
                ["codex-windows-sandbox", "codex-gpu-helper.exe"],
            )
            self.assertEqual(
                cfg.process_detection.background_process_names["macos"],
                ["codex-macos-helper"],
            )
            self.assertEqual(cfg.process_detection.background_process_names["linux"], [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
