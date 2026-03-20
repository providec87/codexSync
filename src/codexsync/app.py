from __future__ import annotations

import logging
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .backup import BackupManager
from .config import load_config
from .exceptions import ConfigError, ConflictError, FailSafeError, SafetyPreconditionError
from .filters import PathFilter
from .gui_prompt import confirm_process_termination
from .manifest import build_manifest, load_manifest, save_manifest
from .models import AppConfig, CopyAction, FileMeta, SyncManifest, SyncPlan
from .planner import build_sync_plan
from .process_detector import CodexProcessDetector, ProcessInfo
from .scanner import scan_tree
from .state_locator import detect_local_state_dir, resolve_state_dirs
from .sync_engine import SyncEngine

LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    config: AppConfig
    local_dir: Path
    cloud_dir: Path
    plan: SyncPlan
    local_index: dict[str, FileMeta]
    cloud_index: dict[str, FileMeta]


@dataclass(slots=True, frozen=True)
class RestoreResult:
    snapshot_name: str
    target: str
    restored_files: int


@dataclass(slots=True, frozen=True)
class ProcessSnapshot:
    main_processes: list[ProcessInfo]
    subprocesses: list[ProcessInfo]
    sandbox_detected: bool


def build_context(
    config_path: Path,
    manual_terminate_confirmation_override: bool | None = None,
    enforce_safety: bool = True,
) -> AppContext:
    cfg = load_config(config_path)
    initialize_runtime_paths(cfg)
    local_dir, cloud_dir = resolve_state_dirs(cfg.paths.local_state_dir, cfg.paths.cloud_root_dir)
    if enforce_safety:
        _enforce_safety_preconditions(cfg, manual_terminate_confirmation_override)

    local_idx, cloud_idx = _build_indexes(cfg, local_dir, cloud_dir)
    manifest = load_manifest(cfg.state.manifest_file, cfg.state.data_version)
    plan = build_sync_plan(
        local_index=local_idx,
        cloud_index=cloud_idx,
        local_root=local_dir,
        cloud_root=cloud_dir,
        previous_manifest=manifest,
        tolerance_seconds=cfg.sync.time_tolerance_seconds,
        conflict_policy=cfg.conflict.policy,
    )
    return AppContext(
        config=cfg,
        local_dir=local_dir,
        cloud_dir=cloud_dir,
        plan=plan,
        local_index=local_idx,
        cloud_index=cloud_idx,
    )


def print_plan(plan: SyncPlan) -> None:
    print("Plan:")
    print(f"  to_local: {len(plan.to_local)}")
    print(f"  to_cloud: {len(plan.to_cloud)}")
    print(f"  actions: {plan.action_count}")
    print(f"  conflicts: {len(plan.conflicts)}")
    for rel_path in plan.conflicts:
        print(f"    conflict: {rel_path}")
    for item in plan.to_local:
        print(f"    cloud -> local: {item.relative_path}")
    for item in plan.to_cloud:
        print(f"    local -> cloud: {item.relative_path}")


def run_sync(ctx: AppContext, dry_run: bool) -> None:
    if ctx.plan.conflicts and ctx.config.conflict.policy == "manual_abort":
        details = ", ".join(ctx.plan.conflicts)
        if not ctx.config.conflict.report_conflicts:
            details = "hidden by configuration"
        raise ConflictError(f"Conflict detected for files: {details}. Resolve manually and rerun.")

    mgr = BackupManager(
        backup_root=ctx.config.paths.backup_dir,
        machine_id=ctx.config.identity.machine_id or platform.node(),
        retention_days=ctx.config.backup.retention_days,
        max_backups=ctx.config.backup.max_backups,
    )
    engine = SyncEngine(
        backup_manager=mgr,
        temp_dir=ctx.config.paths.temp_dir,
        backup_before_overwrite=ctx.config.backup.backup_before_overwrite,
        fail_on_unknown=ctx.config.safety.fail_on_unknown,
    )
    engine.execute(ctx.plan, dry_run=dry_run)

    if not dry_run:
        local_idx, cloud_idx = _build_indexes(ctx.config, ctx.local_dir, ctx.cloud_dir)
        manifest = build_manifest(local_idx, cloud_idx, ctx.config.state.data_version)
        save_manifest(manifest, ctx.config.state.manifest_file)


def restore_from_backup(
    config_path: Path,
    snapshot_name: str | None,
    target: str,
    dry_run: bool,
    manual_terminate_confirmation_override: bool | None = None,
) -> RestoreResult:
    cfg = load_config(config_path)
    initialize_runtime_paths(cfg)
    _enforce_safety_preconditions(cfg, manual_terminate_confirmation_override)

    target_root = _resolve_restore_target(cfg, target)
    snapshot_dir = _resolve_snapshot_dir(cfg.paths.backup_dir, snapshot_name)
    plan = _build_restore_plan(snapshot_dir, target_root, cfg.targets.include_roots, cfg.filters.exclude_globs)

    mgr = BackupManager(
        backup_root=cfg.paths.backup_dir,
        machine_id=cfg.identity.machine_id or platform.node(),
        retention_days=cfg.backup.retention_days,
        max_backups=cfg.backup.max_backups,
    )
    engine = SyncEngine(
        backup_manager=mgr,
        temp_dir=cfg.paths.temp_dir,
        backup_before_overwrite=cfg.backup.backup_before_overwrite,
        fail_on_unknown=cfg.safety.fail_on_unknown,
    )
    engine.execute(plan, dry_run=dry_run)

    return RestoreResult(
        snapshot_name=snapshot_dir.name,
        target=target,
        restored_files=plan.action_count,
    )


def validate_config_only(config_path: Path) -> None:
    try:
        cfg = load_config(config_path)
        initialize_runtime_paths(cfg)
        _ = resolve_state_dirs(cfg.paths.local_state_dir, cfg.paths.cloud_root_dir)
    except ConfigError:
        raise


def initialize_runtime_paths(cfg: AppConfig) -> None:
    """
    Prepares runtime directories/files for first run.
    Creates only codexSync-owned infrastructure and never creates local Codex state dir.
    """
    _ensure_dir(cfg.paths.cloud_root_dir, "paths.cloud_root_dir")
    _ensure_dir(cfg.paths.backup_dir, "paths.backup_dir")
    _ensure_dir(cfg.paths.temp_dir, "paths.temp_dir")
    _bootstrap_cloud_targets(cfg)

    if cfg.logging.file:
        _ensure_dir(cfg.logging.file.parent, "logging.file parent")
        _touch_file(cfg.logging.file, "logging.file")

    if cfg.state.manifest_file:
        _ensure_dir(cfg.state.manifest_file.parent, "state.manifest_file parent")
        if not cfg.state.manifest_file.exists():
            empty_manifest = SyncManifest(data_version=cfg.state.data_version, files={})
            save_manifest(empty_manifest, cfg.state.manifest_file)


def _build_indexes(cfg: AppConfig, local_dir: Path, cloud_dir: Path) -> tuple[dict[str, FileMeta], dict[str, FileMeta]]:
    path_filter = PathFilter(cfg.filters.exclude_globs)
    local_idx = scan_tree(local_dir, cfg.targets.include_roots, path_filter)
    cloud_idx = scan_tree(cloud_dir, cfg.targets.include_roots, path_filter)
    return local_idx, cloud_idx


def _enforce_safety_preconditions(
    cfg: AppConfig,
    manual_terminate_confirmation_override: bool | None = None,
) -> None:
    if not cfg.safety.require_codex_stopped:
        return

    detector = CodexProcessDetector(cfg.process_detection.process_names)
    try:
        snapshot = collect_process_snapshot(cfg, detector=detector)
    except Exception as exc:
        if cfg.safety.fail_on_unknown:
            raise FailSafeError(
                f"Cannot verify Codex process status safely: {exc}"
            ) from exc
        LOG.warning("Cannot verify Codex process status. Continue due to fail_on_unknown=false: %s", exc)
        return

    if snapshot.main_processes:
        _handle_running_codex(
            cfg=cfg,
            detector=detector,
            snapshot=snapshot,
            manual_override=manual_terminate_confirmation_override,
        )

    if cfg.process_detection.grace_period_seconds > 0:
        time.sleep(cfg.process_detection.grace_period_seconds)


def _handle_running_codex(
    cfg: AppConfig,
    detector: CodexProcessDetector,
    snapshot: ProcessSnapshot,
    manual_override: bool | None,
) -> None:
    if not sys.platform.startswith("win"):
        raise SafetyPreconditionError("Codex process is running. Cold sync precondition failed.")

    background_present = snapshot.sandbox_detected
    if background_present:
        raise SafetyPreconditionError(
            "Codex is still running (codex-windows-sandbox detected). "
            "Close Codex and retry sync."
        )

    if not cfg.process_detection.allow_terminate_if_running:
        raise SafetyPreconditionError("Codex process is running and termination is disabled by config.")

    details = ", ".join(f"{proc.name}:{proc.pid}" for proc in snapshot.main_processes)
    approved = confirm_process_termination(
        "Codex main process is still running, but codex-windows-sandbox is not detected.\n\n"
        f"Detected main processes: {details}\n\n"
        "Terminate Codex processes now and continue sync?",
        mode=cfg.process_detection.terminate_confirmation_mode,
    )
    if not approved:
        raise SafetyPreconditionError("User rejected Codex process termination.")

    terminated = detector.terminate(snapshot.main_processes, timeout_seconds=cfg.process_detection.terminate_timeout_seconds)
    if not terminated:
        raise FailSafeError("Failed to terminate Codex processes before timeout.")


def _current_os_background_processes(cfg: AppConfig) -> list[str]:
    os_key = _current_os_key()
    configured = cfg.process_detection.background_process_names.get(os_key, [])
    return [name.strip() for name in configured if name.strip()]


def collect_codex_processes(cfg: AppConfig) -> list[ProcessInfo]:
    snapshot = collect_process_snapshot(cfg)
    return snapshot.subprocesses


def collect_process_snapshot(cfg: AppConfig, detector: CodexProcessDetector | None = None) -> ProcessSnapshot:
    detector = detector or CodexProcessDetector(cfg.process_detection.process_names)
    main, subprocesses = detector.get_subprocess_tree(cfg.process_detection.process_names)
    markers = _current_os_background_processes(cfg)
    sandbox_detected = any(
        detector.has_marker(proc, marker)
        for marker in markers
        for proc in subprocesses
    )
    if not sandbox_detected and sys.platform.startswith("win"):
        sandbox_detected = _has_enable_sandbox_flag(main + subprocesses)
    return ProcessSnapshot(
        main_processes=main,
        subprocesses=subprocesses,
        sandbox_detected=sandbox_detected,
    )


def _has_enable_sandbox_flag(processes: list[ProcessInfo]) -> bool:
    return any("--enable-sandbox" in proc.command_line.lower() for proc in processes)


def _current_os_key() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _ensure_dir(path: Path, field_name: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"Cannot create directory for {field_name}: {path}. {exc}") from exc
    if not path.is_dir():
        raise ConfigError(f"Path for {field_name} is not a directory: {path}")


def _touch_file(path: Path, field_name: str) -> None:
    try:
        path.touch(exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"Cannot create file for {field_name}: {path}. {exc}") from exc
    if not path.is_file():
        raise ConfigError(f"Path for {field_name} is not a file: {path}")


def _bootstrap_cloud_targets(cfg: AppConfig) -> None:
    root = cfg.paths.cloud_root_dir.resolve()
    for rel in cfg.targets.include_roots:
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ConfigError(f"targets.include_roots points outside cloud root: {rel}") from exc

        # Heuristic: entries with suffix are treated as files, others as directories.
        if Path(rel).suffix:
            _ensure_dir(candidate.parent, f"targets.include_roots parent for {rel}")
        else:
            _ensure_dir(candidate, f"targets.include_roots dir {rel}")


def _resolve_restore_target(cfg: AppConfig, target: str) -> Path:
    if target == "local":
        return detect_local_state_dir(cfg.paths.local_state_dir)
    if target == "cloud":
        return cfg.paths.cloud_root_dir
    raise ConfigError(f"Unsupported restore target: {target}")


def _resolve_snapshot_dir(backup_root: Path, snapshot_name: str | None) -> Path:
    if snapshot_name:
        snapshot = (backup_root / snapshot_name).resolve()
        if not snapshot.exists() or not snapshot.is_dir():
            raise ConfigError(f"Backup snapshot not found: {snapshot_name}")
        return snapshot

    snapshots = [p for p in backup_root.iterdir() if p.is_dir()] if backup_root.exists() else []
    if not snapshots:
        raise ConfigError(f"No backup snapshots found in: {backup_root}")
    snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return snapshots[0]


def _build_restore_plan(
    snapshot_dir: Path,
    target_root: Path,
    include_roots: list[str],
    exclude_globs: list[str],
) -> SyncPlan:
    path_filter = PathFilter(exclude_globs)
    allowed_roots = [root.strip("/\\") for root in include_roots if root.strip("/\\")]
    actions: list[CopyAction] = []

    for source in snapshot_dir.rglob("*"):
        if not source.is_file():
            continue
        rel = source.relative_to(snapshot_dir).as_posix()
        if not _is_included_root(rel, allowed_roots):
            continue
        if path_filter.is_excluded(rel):
            continue
        dst = target_root / Path(rel.replace("/", os.sep))
        actions.append(CopyAction(src=source, dst=dst, relative_path=rel))

    return SyncPlan(to_local=actions, to_cloud=[])


def _is_included_root(relative_path: str, include_roots: list[str]) -> bool:
    rel = relative_path.strip("/\\")
    for root in include_roots:
        if rel == root or rel.startswith(f"{root}/"):
            return True
    return False
