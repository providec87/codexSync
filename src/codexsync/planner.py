from __future__ import annotations

import hashlib
from pathlib import Path

from .models import CopyAction, FileMeta, SnapshotFingerprint, SyncManifest, SyncPlan


def build_sync_plan(
    local_index: dict[str, FileMeta],
    cloud_index: dict[str, FileMeta],
    local_root: Path,
    cloud_root: Path,
    previous_manifest: SyncManifest | None = None,
    compare_mode: str = "mtime",
    tolerance_seconds: int = 0,
    conflict_policy: str = "manual_abort",
    equal_mtime_action: str = "skip",
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

        if _same_file(local_meta, cloud_meta, tolerance_ns, compare_mode):
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

        if abs(local_meta.mtime_ns - cloud_meta.mtime_ns) <= tolerance_ns:
            resolved = _resolve_equal_mtime(
                rel=rel,
                local_meta=local_meta,
                cloud_meta=cloud_meta,
                local_root=local_root,
                cloud_root=cloud_root,
                plan=plan,
                equal_mtime_action=equal_mtime_action,
            )
            if not resolved:
                plan.conflicts.append(rel)
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


def _resolve_equal_mtime(
    rel: str,
    local_meta: FileMeta,
    cloud_meta: FileMeta,
    local_root: Path,
    cloud_root: Path,
    plan: SyncPlan,
    equal_mtime_action: str,
) -> bool:
    if equal_mtime_action == "skip":
        return True
    if equal_mtime_action == "prefer_local":
        plan.to_cloud.append(CopyAction(local_meta.abs_path, cloud_root / rel, rel))
        return True
    if equal_mtime_action == "prefer_cloud":
        plan.to_local.append(CopyAction(cloud_meta.abs_path, local_root / rel, rel))
        return True
    if equal_mtime_action == "manual_abort":
        return False
    return False


def _same_file(local_meta: FileMeta, cloud_meta: FileMeta, tolerance_ns: int, compare_mode: str) -> bool:
    if local_meta.size != cloud_meta.size:
        return False
    mtime_close = abs(local_meta.mtime_ns - cloud_meta.mtime_ns) <= tolerance_ns
    if not mtime_close:
        return False
    if compare_mode == "mtime_hash_fallback":
        return _same_content(local_meta.abs_path, cloud_meta.abs_path)
    return True


def _has_side_changed(meta: FileMeta, previous: SnapshotFingerprint | None, tolerance_ns: int) -> bool:
    if previous is None:
        return True
    if meta.size != previous.size:
        return True
    return abs(meta.mtime_ns - previous.mtime_ns) > tolerance_ns


def _same_content(left: Path, right: Path) -> bool:
    return _sha256(left) == _sha256(right)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
