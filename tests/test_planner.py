from __future__ import annotations

from pathlib import Path
import unittest

from codexsync.models import FileMeta, ManifestEntry, SnapshotFingerprint, SyncManifest
from codexsync.planner import build_sync_plan


def _file_meta(rel: str, mtime_ns: int, size: int = 10) -> FileMeta:
    return FileMeta(relative_path=rel, abs_path=Path(f"/tmp/{rel}"), mtime_ns=mtime_ns, size=size)


class PlannerTests(unittest.TestCase):
    def test_newer_file_wins_without_manifest(self) -> None:
        local_index = {"sessions/a.json": _file_meta("sessions/a.json", mtime_ns=200)}
        cloud_index = {"sessions/a.json": _file_meta("sessions/a.json", mtime_ns=100)}

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
        )

        self.assertEqual(len(plan.to_cloud), 1)
        self.assertEqual(len(plan.to_local), 0)
        self.assertEqual(plan.conflicts, [])

    def test_conflict_when_both_sides_changed_since_manifest(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=300, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=350, size=12)}
        manifest = SyncManifest(
            data_version=1,
            files={
                rel: ManifestEntry(
                    local=SnapshotFingerprint(mtime_ns=100, size=10),
                    cloud=SnapshotFingerprint(mtime_ns=100, size=10),
                )
            },
        )

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            previous_manifest=manifest,
        )

        self.assertEqual(plan.conflicts, [rel])
        self.assertEqual(plan.action_count, 0)

    def test_conflict_resolved_with_prefer_cloud(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=300, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=350, size=12)}
        manifest = SyncManifest(
            data_version=1,
            files={
                rel: ManifestEntry(
                    local=SnapshotFingerprint(mtime_ns=100, size=10),
                    cloud=SnapshotFingerprint(mtime_ns=100, size=10),
                )
            },
        )

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            previous_manifest=manifest,
            conflict_policy="prefer_cloud",
        )

        self.assertEqual(plan.conflicts, [])
        self.assertEqual(len(plan.to_local), 1)
        self.assertEqual(len(plan.to_cloud), 0)

    def test_conflict_resolved_with_prefer_local(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=300, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=350, size=12)}
        manifest = SyncManifest(
            data_version=1,
            files={
                rel: ManifestEntry(
                    local=SnapshotFingerprint(mtime_ns=100, size=10),
                    cloud=SnapshotFingerprint(mtime_ns=100, size=10),
                )
            },
        )

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            previous_manifest=manifest,
            conflict_policy="prefer_local",
        )

        self.assertEqual(plan.conflicts, [])
        self.assertEqual(len(plan.to_cloud), 1)
        self.assertEqual(len(plan.to_local), 0)

    def test_conflict_resolved_with_prefer_newer_mtime(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=300, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=350, size=12)}
        manifest = SyncManifest(
            data_version=1,
            files={
                rel: ManifestEntry(
                    local=SnapshotFingerprint(mtime_ns=100, size=10),
                    cloud=SnapshotFingerprint(mtime_ns=100, size=10),
                )
            },
        )

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            previous_manifest=manifest,
            conflict_policy="prefer_newer_mtime",
        )

        self.assertEqual(plan.conflicts, [])
        self.assertEqual(len(plan.to_local), 1)
        self.assertEqual(len(plan.to_cloud), 0)

    def test_one_side_changed_syncs_without_conflict(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=150, size=10)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=100, size=10)}
        manifest = SyncManifest(
            data_version=1,
            files={
                rel: ManifestEntry(
                    local=SnapshotFingerprint(mtime_ns=100, size=10),
                    cloud=SnapshotFingerprint(mtime_ns=100, size=10),
                )
            },
        )

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            previous_manifest=manifest,
        )

        self.assertEqual(len(plan.to_cloud), 1)
        self.assertEqual(plan.conflicts, [])


if __name__ == "__main__":
    unittest.main()
