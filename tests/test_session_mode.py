from __future__ import annotations

from pathlib import Path
import unittest

from codexsync.app import _apply_session_mode
from codexsync.models import FileMeta


def _meta(rel: str) -> FileMeta:
    return FileMeta(relative_path=rel, abs_path=Path(f"/tmp/{rel}"), mtime_ns=100, size=10)


class SessionModeTests(unittest.TestCase):
    def test_last_date_only_keeps_only_latest_sessions_date(self) -> None:
        local_idx = {
            "sessions/2026-03-20/a.json": _meta("sessions/2026-03-20/a.json"),
            "sessions/2026-03-21/b.json": _meta("sessions/2026-03-21/b.json"),
            "session_index.jsonl": _meta("session_index.jsonl"),
        }
        cloud_idx = {
            "sessions/2026-03-19/c.json": _meta("sessions/2026-03-19/c.json"),
            "sessions/2026-03-21/d.json": _meta("sessions/2026-03-21/d.json"),
            "skills/skill.md": _meta("skills/skill.md"),
        }

        local_filtered, cloud_filtered = _apply_session_mode(local_idx, cloud_idx, "last_date_only")

        self.assertEqual(
            sorted(local_filtered.keys()),
            ["session_index.jsonl", "sessions/2026-03-21/b.json"],
        )
        self.assertEqual(
            sorted(cloud_filtered.keys()),
            ["sessions/2026-03-21/d.json", "skills/skill.md"],
        )

    def test_last_date_only_keeps_all_when_no_date_based_sessions(self) -> None:
        local_idx = {
            "sessions/current/a.json": _meta("sessions/current/a.json"),
            "session_index.jsonl": _meta("session_index.jsonl"),
        }
        cloud_idx = {
            "sessions/current/b.json": _meta("sessions/current/b.json"),
        }

        local_filtered, cloud_filtered = _apply_session_mode(local_idx, cloud_idx, "last_date_only")

        self.assertEqual(local_filtered, local_idx)
        self.assertEqual(cloud_filtered, cloud_idx)


if __name__ == "__main__":
    unittest.main()
