from __future__ import annotations

from pathlib import Path

from .models import CopyAction, FileMeta, SnapshotFingerprint, SyncManifest, SyncPlan


def build_sync_plan(
    local_index: dict[str, FileMeta],
    cloud_index: dict[str, FileMeta],
    local_root: Path,
    cloud_root: Path,
    previous_manifest: SyncManifest | None = None,
    tolerance_seconds: int = 0,
    conflict_policy: str = "manual_abort",
) -> SyncPlan:
    """
    Builds a bidirectional copy plan with conflict detection.
    """
    tolerance_ns = tolerance_seconds * 1_000_000_000
    plan = SyncPlan()
    all_paths = sorted(set(local_index.keys()) | set(cloud_index.keys()))
    prev_files = previous_manifest.files if previous_manifest else {}

    for rel in all_paths:
        local_meta = local_index.get(rel)
        cloud_meta = cloud_index.get(rel)
        prev_entry = prev_files.get(rel)

        if local_meta and not cloud_meta:
            plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
            continue

        if cloud_meta and not local_meta:
            plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))
            continue

        if not local_meta or not cloud_meta:
            continue

        if _same_file(local_meta, cloud_meta, tolerance_ns):
            continue

        if prev_entry:
            local_changed = _has_side_changed(local_meta, prev_entry.local, tolerance_ns)
            cloud_changed = _has_side_changed(cloud_meta, prev_entry.cloud, tolerance_ns)

            if local_changed and cloud_changed:
                resolved = _resolve_conflict(
                    rel=rel,
                    local_meta=local_meta,
                    cloud_meta=cloud_meta,
                    local_root=local_root,
                    cloud_root=cloud_root,
                    plan=plan,
                    conflict_policy=conflict_policy,
                )
                if not resolved:
                    plan.conflicts.append(rel)
                continue

            if local_changed:
                plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
                continue

            if cloud_changed:
                plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))
                continue

        if local_meta.mtime_ns > cloud_meta.mtime_ns:
            plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
        else:
            plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))

    return plan


def _resolve_conflict(
    rel: str,
    local_meta: FileMeta,
    cloud_meta: FileMeta,
    local_root: Path,
    cloud_root: Path,
    plan: SyncPlan,
    conflict_policy: str,
) -> bool:
    if conflict_policy == "prefer_cloud":
        plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))
        return True
    if conflict_policy == "prefer_local":
        plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
        return True
    if conflict_policy == "prefer_newer_mtime":
        if local_meta.mtime_ns > cloud_meta.mtime_ns:
            plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
        else:
            plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))
        return True
    return False


def _same_file(local_meta: FileMeta, cloud_meta: FileMeta, tolerance_ns: int) -> bool:
    if local_meta.size != cloud_meta.size:
        return False
    return abs(local_meta.mtime_ns - cloud_meta.mtime_ns) <= tolerance_ns


def _has_side_changed(meta: FileMeta, previous: SnapshotFingerprint | None, tolerance_ns: int) -> bool:
    if previous is None:
        return True
    if meta.size != previous.size:
        return True
    return abs(meta.mtime_ns - previous.mtime_ns) > tolerance_ns
