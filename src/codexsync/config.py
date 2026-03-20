from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .exceptions import ConfigError
from .models import (
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


def _to_path(
    value: str | None,
    field_name: str,
    *,
    base_dir: Path,
    workspace_root: Path | None = None,
    required: bool = True,
) -> Path | None:
    if not value:
        if required:
            raise ConfigError(f"Missing required path field: {field_name}")
        return None

    resolved = _expand_workspace_var(value, workspace_root, field_name)
    raw = Path(resolved).expanduser()
    if raw.is_absolute():
        return raw
    anchor = workspace_root if workspace_root else base_dir
    return (anchor / raw).resolve()


def _expand_workspace_var(raw_value: str, workspace_root: Path | None, field_name: str) -> str:
    token = "${workspace_root}"
    if token not in raw_value:
        return raw_value
    if workspace_root is None:
        raise ConfigError(
            f"{field_name} uses {token}, but paths.workspace_root_dir is not configured"
        )
    return raw_value.replace(token, str(workspace_root))


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    base_dir = path.parent.resolve()
    with path.open("rb") as fh:
        raw: dict[str, Any] = tomllib.load(fh)

    identity_raw = raw.get("identity", {})
    paths_raw = raw.get("paths", {})
    sync_raw = raw.get("sync", {})
    safety_raw = raw.get("safety", {})
    proc_raw = raw.get("process_detection", {})
    backup_raw = raw.get("backup", {})
    filters_raw = raw.get("filters", {})
    targets_raw = raw.get("targets", {})
    conflict_raw = raw.get("conflict", {})
    state_raw = raw.get("state", {})
    logging_raw = raw.get("logging", {})

    identity = IdentityConfig(machine_id=identity_raw.get("machine_id"))

    workspace_root_dir = _to_path(
        paths_raw.get("workspace_root_dir"),
        "paths.workspace_root_dir",
        base_dir=base_dir,
        required=False,
    )
    cloud_root_dir = _to_path(
        paths_raw.get("cloud_root_dir"),
        "paths.cloud_root_dir",
        base_dir=base_dir,
        workspace_root=workspace_root_dir,
    )
    backup_dir = _to_path(
        paths_raw.get("backup_dir"),
        "paths.backup_dir",
        base_dir=base_dir,
        workspace_root=workspace_root_dir,
    )
    temp_dir = _to_path(
        paths_raw.get("temp_dir"),
        "paths.temp_dir",
        base_dir=base_dir,
        workspace_root=workspace_root_dir,
    )
    if cloud_root_dir is None or backup_dir is None or temp_dir is None:
        raise ConfigError("paths.cloud_root_dir, paths.backup_dir and paths.temp_dir are required")

    paths = PathsConfig(
        workspace_root_dir=workspace_root_dir,
        local_state_dir=_to_path(
            paths_raw.get("local_state_dir"),
            "paths.local_state_dir",
            base_dir=base_dir,
            workspace_root=workspace_root_dir,
            required=False,
        ),
        cloud_root_dir=cloud_root_dir,
        backup_dir=backup_dir,
        temp_dir=temp_dir,
    )

    sync = SyncConfig(
        mode=sync_raw.get("mode", "cold"),
        direction=sync_raw.get("direction", "bidirectional"),
        compare=sync_raw.get("compare", "mtime"),
        time_tolerance_seconds=int(sync_raw.get("time_tolerance_seconds", 0)),
        equal_mtime_action=sync_raw.get("equal_mtime_action", "skip"),
        dry_run_default=bool(sync_raw.get("dry_run_default", True)),
        delete_policy=sync_raw.get("delete_policy", "never"),
        session_mode=sync_raw.get("session_mode"),
    )

    safety = SafetyConfig(
        require_codex_stopped=bool(safety_raw.get("require_codex_stopped", True)),
        fail_on_unknown=bool(safety_raw.get("fail_on_unknown", True)),
    )

    background_process_names = _parse_background_process_names(proc_raw)
    process_detection = ProcessDetectionConfig(
        process_names=_parse_process_names(proc_raw.get("process_names", ["codex.exe", "codex"])),
        grace_period_seconds=int(proc_raw.get("grace_period_seconds", 2)),
        allow_terminate_if_running=bool(proc_raw.get("allow_terminate_if_running", True)),
        manual_terminate_confirmation=bool(proc_raw.get("manual_terminate_confirmation", True)),
        terminate_confirmation_mode=str(proc_raw.get("terminate_confirmation_mode", "gui")).strip().lower(),
        terminate_timeout_seconds=int(proc_raw.get("terminate_timeout_seconds", 20)),
        background_process_names=background_process_names,
    )

    backup = BackupConfig(
        backup_before_overwrite=bool(backup_raw.get("backup_before_overwrite", True)),
        retention_days=int(backup_raw.get("retention_days", 30)),
        max_backups=int(backup_raw.get("max_backups", 0)),
        compression=backup_raw.get("compression", "none"),
    )

    filters = FiltersConfig(exclude_globs=list(filters_raw.get("exclude_globs", [])))
    targets = TargetsConfig(include_roots=list(targets_raw.get("include_roots", [])))
    conflict = ConflictConfig(
        policy=conflict_raw.get("policy", "manual_abort"),
        report_conflicts=bool(conflict_raw.get("report_conflicts", True)),
    )
    state = StateConfig(
        manifest_file=_to_path(
            state_raw.get("manifest_file"),
            "state.manifest_file",
            base_dir=base_dir,
            workspace_root=workspace_root_dir,
            required=False,
        ),
        data_version=int(state_raw.get("data_version", 1)),
    )

    log_file = logging_raw.get("file")
    logging_cfg = LoggingConfig(
        level=logging_raw.get("level", "INFO"),
        file=_to_path(
            log_file,
            "logging.file",
            base_dir=base_dir,
            workspace_root=workspace_root_dir,
            required=False,
        ),
        format=logging_raw.get("format", "text"),
        retention_days=int(logging_raw.get("retention_days", 7)),
    )

    cfg = AppConfig(
        identity=identity,
        paths=paths,
        sync=sync,
        safety=safety,
        process_detection=process_detection,
        backup=backup,
        filters=filters,
        targets=targets,
        conflict=conflict,
        state=state,
        logging=logging_cfg,
    )
    _validate_config(cfg)
    return cfg


def _validate_config(cfg: AppConfig) -> None:
    if cfg.sync.mode != "cold":
        raise ConfigError("Only cold sync mode is supported")

    if cfg.sync.compare != "mtime":
        raise ConfigError("Only compare=mtime is supported")

    if cfg.sync.direction != "bidirectional":
        raise ConfigError("Only bidirectional sync direction is supported")

    if cfg.sync.delete_policy != "never":
        raise ConfigError("Only delete_policy=never is supported in MVP")

    if cfg.sync.time_tolerance_seconds < 0:
        raise ConfigError("sync.time_tolerance_seconds must be >= 0")

    allowed_conflict_policies = {"manual_abort", "prefer_cloud", "prefer_local", "prefer_newer_mtime"}
    if cfg.conflict.policy not in allowed_conflict_policies:
        raise ConfigError(
            "conflict.policy must be one of: manual_abort, prefer_cloud, prefer_local, prefer_newer_mtime"
        )

    if cfg.backup.compression not in {"none"}:
        raise ConfigError("Only backup.compression=none is supported")

    if not cfg.process_detection.process_names:
        raise ConfigError("process_detection.process_names must not be empty")

    if cfg.process_detection.terminate_timeout_seconds < 0:
        raise ConfigError("process_detection.terminate_timeout_seconds must be >= 0")

    if cfg.process_detection.terminate_confirmation_mode not in {"gui", "console"}:
        raise ConfigError("process_detection.terminate_confirmation_mode must be one of: gui, console")

    allowed_os_keys = {"windows", "macos", "linux"}
    for os_key, names in cfg.process_detection.background_process_names.items():
        if os_key not in allowed_os_keys:
            raise ConfigError(
                f"process_detection.background_process_names has unsupported OS key: {os_key}"
            )
        if not isinstance(names, list):
            raise ConfigError(
                f"process_detection.background_process_names.{os_key} must be a list of process names"
            )

    if cfg.logging.format.lower() not in {"text", "json", "logfmt"}:
        raise ConfigError("logging.format must be one of: text, json, logfmt")

    if cfg.paths.local_state_dir and cfg.paths.local_state_dir == cfg.paths.cloud_root_dir:
        raise ConfigError("paths.local_state_dir and paths.cloud_root_dir must be different")


def _parse_background_process_names(proc_raw: dict[str, Any]) -> dict[str, list[str]]:
    default_mapping: dict[str, list[str]] = {
        "windows": ["codex-windows-sandbox"],
        "macos": [],
        "linux": [],
    }
    raw_mapping = proc_raw.get("background_process_names")
    if isinstance(raw_mapping, dict):
        parsed: dict[str, list[str]] = {}
        for key in ("windows", "macos", "linux"):
            value = raw_mapping.get(key, default_mapping[key])
            if not isinstance(value, list):
                raise ConfigError(
                    f"process_detection.background_process_names.{key} must be a list of process names"
                )
            parsed[key] = [str(name).strip() for name in value if str(name).strip()]
        return parsed
    return default_mapping


def _parse_process_names(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        raise ConfigError("process_detection.process_names must be a list")
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        name = str(item).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result
