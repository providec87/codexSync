from __future__ import annotations

from pathlib import Path
import shutil
import textwrap
import unittest
import uuid
import zipfile

from codexsync.app import restore_from_backup
from codexsync.exceptions import ConfigError


class RestoreTests(unittest.TestCase):
    def test_restore_from_latest_snapshot_to_local(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"restore-{uuid.uuid4().hex}"
        local_state = root / "local-state"
        cloud_root = root / "cloud"
        backup_root = root / "backups"
        temp_root = root / ".tmp"
        config_path = root / "config.toml"

        local_state.mkdir(parents=True, exist_ok=True)
        cloud_root.mkdir(parents=True, exist_ok=True)
        backup_root.mkdir(parents=True, exist_ok=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        snapshot_old = backup_root / "machine-a-20260101T000000Z"
        snapshot_new = backup_root / "machine-a-20260101T000100Z"
        (snapshot_old / "sessions").mkdir(parents=True, exist_ok=True)
        (snapshot_new / "sessions").mkdir(parents=True, exist_ok=True)
        (snapshot_old / "sessions" / "a.txt").write_text("old", encoding="utf-8")
        (snapshot_new / "sessions" / "a.txt").write_text("new", encoding="utf-8")

        config_path.write_text(
            textwrap.dedent(
                f"""
                [identity]
                machine_id = "machine-a"

                [sync]
                mode = "cold"
                direction = "bidirectional"
                compare = "mtime"
                delete_policy = "never"

                [safety]
                require_codex_stopped = false
                fail_on_unknown = true

                [paths]
                workspace_root_dir = "{root.as_posix()}"
                local_state_dir = "{local_state.as_posix()}"
                cloud_root_dir = "{cloud_root.as_posix()}"
                backup_dir = "{backup_root.as_posix()}"
                temp_dir = "{temp_root.as_posix()}"

                [targets]
                include_roots = ["sessions"]
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        try:
            result = restore_from_backup(
                config_path=config_path,
                snapshot_name=snapshot_new.name,
                target="local",
                dry_run=False,
            )

            restored = local_state / "sessions" / "a.txt"
            self.assertTrue(restored.exists())
            self.assertEqual(restored.read_text(encoding="utf-8"), "new")
            self.assertEqual(result.snapshot_name, snapshot_new.name)
            self.assertEqual(result.target, "local")
            self.assertEqual(result.restored_files, 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_restore_from_zip_snapshot_to_local(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"restore-zip-{uuid.uuid4().hex}"
        local_state = root / "local-state"
        cloud_root = root / "cloud"
        backup_root = root / "backups"
        temp_root = root / ".tmp"
        config_path = root / "config.toml"

        local_state.mkdir(parents=True, exist_ok=True)
        cloud_root.mkdir(parents=True, exist_ok=True)
        backup_root.mkdir(parents=True, exist_ok=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        snapshot_zip = backup_root / "machine-a-20260101T000200Z.zip"
        with zipfile.ZipFile(snapshot_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sessions/a.txt", "zip-new")

        config_path.write_text(
            textwrap.dedent(
                f"""
                [identity]
                machine_id = "machine-a"

                [sync]
                mode = "cold"
                direction = "bidirectional"
                compare = "mtime"
                delete_policy = "never"

                [safety]
                require_codex_stopped = false
                fail_on_unknown = true

                [paths]
                workspace_root_dir = "{root.as_posix()}"
                local_state_dir = "{local_state.as_posix()}"
                cloud_root_dir = "{cloud_root.as_posix()}"
                backup_dir = "{backup_root.as_posix()}"
                temp_dir = "{temp_root.as_posix()}"

                [backup]
                compression = "zip"

                [targets]
                include_roots = ["sessions"]
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        try:
            result = restore_from_backup(
                config_path=config_path,
                snapshot_name=snapshot_zip.name,
                target="local",
                dry_run=False,
            )

            restored = local_state / "sessions" / "a.txt"
            self.assertTrue(restored.exists())
            self.assertEqual(restored.read_text(encoding="utf-8"), "zip-new")
            self.assertEqual(result.snapshot_name, snapshot_zip.name)
            self.assertEqual(result.target, "local")
            self.assertEqual(result.restored_files, 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_restore_rejects_snapshot_outside_backup_root(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"restore-traversal-{uuid.uuid4().hex}"
        local_state = root / "local-state"
        cloud_root = root / "cloud"
        backup_root = root / "backups"
        temp_root = root / ".tmp"
        config_path = root / "config.toml"

        local_state.mkdir(parents=True, exist_ok=True)
        cloud_root.mkdir(parents=True, exist_ok=True)
        backup_root.mkdir(parents=True, exist_ok=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        outside_snapshot = root / "outside.zip"
        with zipfile.ZipFile(outside_snapshot, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sessions/a.txt", "outside")

        config_path.write_text(
            textwrap.dedent(
                f"""
                [identity]
                machine_id = "machine-a"

                [sync]
                mode = "cold"
                direction = "bidirectional"
                compare = "mtime"
                delete_policy = "never"

                [safety]
                require_codex_stopped = false
                fail_on_unknown = true

                [paths]
                workspace_root_dir = "{root.as_posix()}"
                local_state_dir = "{local_state.as_posix()}"
                cloud_root_dir = "{cloud_root.as_posix()}"
                backup_dir = "{backup_root.as_posix()}"
                temp_dir = "{temp_root.as_posix()}"

                [targets]
                include_roots = ["sessions"]
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        try:
            with self.assertRaises(ConfigError):
                restore_from_backup(
                    config_path=config_path,
                    snapshot_name="../outside.zip",
                    target="local",
                    dry_run=False,
                )
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_restore_zip_with_empty_include_roots_restores_all_files(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"restore-zip-all-{uuid.uuid4().hex}"
        local_state = root / "local-state"
        cloud_root = root / "cloud"
        backup_root = root / "backups"
        temp_root = root / ".tmp"
        config_path = root / "config.toml"

        local_state.mkdir(parents=True, exist_ok=True)
        cloud_root.mkdir(parents=True, exist_ok=True)
        backup_root.mkdir(parents=True, exist_ok=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        snapshot_zip = backup_root / "machine-a-20260101T000300Z.zip"
        with zipfile.ZipFile(snapshot_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sessions/a.txt", "zip-new")
            zf.writestr("plugins/tool.txt", "plugin-data")

        config_path.write_text(
            textwrap.dedent(
                f"""
                [identity]
                machine_id = "machine-a"

                [sync]
                mode = "cold"
                direction = "bidirectional"
                compare = "mtime"
                delete_policy = "never"

                [safety]
                require_codex_stopped = false
                fail_on_unknown = true

                [paths]
                workspace_root_dir = "{root.as_posix()}"
                local_state_dir = "{local_state.as_posix()}"
                cloud_root_dir = "{cloud_root.as_posix()}"
                backup_dir = "{backup_root.as_posix()}"
                temp_dir = "{temp_root.as_posix()}"

                [backup]
                compression = "zip"

                [targets]
                include_roots = []
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        try:
            result = restore_from_backup(
                config_path=config_path,
                snapshot_name=snapshot_zip.name,
                target="local",
                dry_run=False,
            )

            self.assertEqual(result.restored_files, 2)
            self.assertEqual((local_state / "sessions" / "a.txt").read_text(encoding="utf-8"), "zip-new")
            self.assertEqual((local_state / "plugins" / "tool.txt").read_text(encoding="utf-8"), "plugin-data")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
