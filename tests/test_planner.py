from __future__ import annotations

from pathlib import Path
import shutil
import unittest
import uuid

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

    def test_equal_mtime_skip_by_default(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=100, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=100, size=12)}

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
        )

        self.assertEqual(plan.action_count, 0)
        self.assertEqual(plan.conflicts, [])

    def test_equal_mtime_prefer_local(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=100, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=100, size=12)}

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            equal_mtime_action="prefer_local",
        )

        self.assertEqual(len(plan.to_cloud), 1)
        self.assertEqual(len(plan.to_local), 0)
        self.assertEqual(plan.conflicts, [])

    def test_equal_mtime_prefer_cloud(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=100, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=100, size=12)}

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            equal_mtime_action="prefer_cloud",
        )

        self.assertEqual(len(plan.to_local), 1)
        self.assertEqual(len(plan.to_cloud), 0)
        self.assertEqual(plan.conflicts, [])

    def test_equal_mtime_manual_abort(self) -> None:
        rel = "sessions/a.json"
        local_index = {rel: _file_meta(rel, mtime_ns=100, size=11)}
        cloud_index = {rel: _file_meta(rel, mtime_ns=100, size=12)}

        plan = build_sync_plan(
            local_index=local_index,
            cloud_index=cloud_index,
            local_root=Path("/local"),
            cloud_root=Path("/cloud"),
            equal_mtime_action="manual_abort",
        )

        self.assertEqual(plan.action_count, 0)
        self.assertEqual(plan.conflicts, [rel])

    def test_mtime_hash_fallback_detects_content_difference(self) -> None:
        root = Path.cwd() / "test-sandbox" / f"planner-hash-{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            rel = "sessions/a.json"
            local_file = root / "local-a.json"
            cloud_file = root / "cloud-a.json"
            local_file.write_text("A", encoding="utf-8")
            cloud_file.write_text("B", encoding="utf-8")

            local_meta = FileMeta(relative_path=rel, abs_path=local_file, mtime_ns=100, size=1)
            cloud_meta = FileMeta(relative_path=rel, abs_path=cloud_file, mtime_ns=100, size=1)
            local_index = {rel: local_meta}
            cloud_index = {rel: cloud_meta}

            plan_mtime = build_sync_plan(
                local_index=local_index,
                cloud_index=cloud_index,
                local_root=Path("/local"),
                cloud_root=Path("/cloud"),
                compare_mode="mtime",
            )
            self.assertEqual(plan_mtime.action_count, 0)
            self.assertEqual(plan_mtime.conflicts, [])

            plan_fallback = build_sync_plan(
                local_index=local_index,
                cloud_index=cloud_index,
                local_root=Path("/local"),
                cloud_root=Path("/cloud"),
                compare_mode="mtime_hash_fallback",
                equal_mtime_action="manual_abort",
            )
            self.assertEqual(plan_fallback.action_count, 0)
            self.assertEqual(plan_fallback.conflicts, [rel])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
