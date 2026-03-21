from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
import shutil
import unittest
import uuid

from codexsync.logging_setup import configure_logging
from codexsync.models import LoggingConfig


class LoggingSetupTests(unittest.TestCase):
    @staticmethod
    def _mute_console_logging() -> None:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.CRITICAL + 1)

    def test_zip_archive_mode_rotates_by_size(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"logging-zip-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            base_log = root / "logs" / "codexsync.log"
            configure_logging(
                LoggingConfig(
                    level="INFO",
                    file=base_log,
                    format="text",
                    retention_days=7,
                    archive_mode="zip",
                    max_file_size_mb=1,
                    machine_id="machine-a",
                ),
                verbose=False,
            )
            self._mute_console_logging()
            logger = logging.getLogger("tests.logging.zip")
            chunk = "x" * 20_000
            for i in range(90):
                logger.info("entry=%s %s", i, chunk)
            logging.shutdown()

            today = date.today().isoformat()
            log_files = sorted((root / "logs").glob("codexsync-machine-a-*.log"))
            zip_files = sorted((root / "logs").glob("codexsync-machine-a-*.log.zip"))

            self.assertTrue(log_files, "active .log file is expected")
            self.assertTrue(zip_files, "archived .zip logs are expected after size rollover")
            self.assertTrue(any(today in p.name for p in log_files))
            self.assertTrue(all(p.stat().st_size <= 1024 * 1024 for p in log_files))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_text_archive_mode_keeps_plain_rotated_logs(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"logging-text-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            base_log = root / "logs" / "codexsync.log"
            configure_logging(
                LoggingConfig(
                    level="INFO",
                    file=base_log,
                    format="text",
                    retention_days=7,
                    archive_mode="text",
                    max_file_size_mb=1,
                    machine_id="machine-a",
                ),
                verbose=False,
            )
            self._mute_console_logging()
            logger = logging.getLogger("tests.logging.text")
            chunk = "y" * 20_000
            for i in range(90):
                logger.info("entry=%s %s", i, chunk)
            logging.shutdown()

            log_files = sorted((root / "logs").glob("codexsync-machine-a-*.log"))
            zip_files = sorted((root / "logs").glob("codexsync-machine-a-*.log.zip"))
            self.assertGreaterEqual(len(log_files), 2)
            self.assertEqual(len(zip_files), 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_retention_removes_old_logs(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"logging-retention-{uuid.uuid4().hex}"
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=False)
        try:
            old_text = log_dir / "codexsync-machine-a-2000-01-01.log"
            old_zip = log_dir / "codexsync-machine-a-2000-01-01.log.zip"
            old_text.write_text("old", encoding="utf-8")
            old_zip.write_bytes(b"old-zip")

            base_log = log_dir / "codexsync.log"
            configure_logging(
                LoggingConfig(
                    level="INFO",
                    file=base_log,
                    format="text",
                    retention_days=7,
                    archive_mode="zip",
                    max_file_size_mb=10,
                    machine_id="machine-a",
                ),
                verbose=False,
            )
            self._mute_console_logging()
            logger = logging.getLogger("tests.logging.retention")
            logger.info("hello")
            logging.shutdown()

            self.assertFalse(old_text.exists())
            self.assertFalse(old_zip.exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
