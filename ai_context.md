# AI Context

## Purpose
`codexSync` is a local CLI utility for cold-syncing Codex state between two personal machines through a synchronized folder.

## Goal
Allow developers to continue work on a second machine without losing Codex local context.

## Core Assumptions
- Sync runs only when Codex is fully closed.
- Only one active machine is used at a time.
- The user is responsible for cloud sync readiness and available storage capacity.
- The project does not use Codex APIs and does not interfere with Codex runtime internals.

## Target Platforms and Versions
- Python: `3.8+` (minimum supported version).
- Windows: `Windows 10+`.
- macOS:
  - Officially confirmed: Codex app is available on `macOS (Apple Silicon)`.
  - Architecture constraint: Intel Mac is not treated as a target platform.
  - Minimum macOS version is not explicitly fixed in public docs; until separate validation, target `macOS 14+` on Apple Silicon (working assumption).
- Linux: future support is possible, but versions are not fixed until official Codex Linux availability.

## Run Modes
- Direct run: manual (`python ...` or packaged binary).
- Scheduled run:
  - Windows: Task Scheduler.
  - macOS: `launchd` (LaunchAgent) or equivalent scheduled job.
- For Windows, packaging the Python script into `.exe` (for example via PyInstaller) is allowed to simplify deployment.

## MVP Features
1. Detect Codex process (Windows at minimum, with macOS extension).
2. Detect Codex state directory.
3. Compare local and cloud copies.
4. Sync changes.
5. Enforce backup before overwrite.
6. Exclude temp/lock/cache files.

## Safety Criteria
- Never write to state while Codex is running.
- Always create a backup before overwrite.
- On uncertainty, fail-safe (abort without writes).

## Recorded Decisions
- Conflict policy: if both sides changed, treat as conflict, do not sync, print conflict file list, and exit.
- Conflict resolution: manual by user; rerun required after manual resolution.
- Logging:
  - Levels: `DEBUG|INFO|WARNING|ERROR`.
  - Formats: `text|json|logfmt` (configurable).
  - Rotation: retention-based, default `7` days.
- File-time normalization: no dedicated normalization/clock compensation in MVP; rely on OS/filesystem timestamps.
- CLI exit codes (for CI/automation):
  - `0` success (including no-op).
  - `1` runtime error.
  - `2` conflicts detected, manual resolution required.
  - `3` Codex is running, sync blocked.
  - `4` config or argument error.
  - `5` safe abort (`fail-safe`) due to uncertain state.
