# Decisions

## D-001: Sync strategy
We use cold sync only.
Sync happens only when Codex is fully closed.

## D-002: Legal/safety boundary
The project only works with user-local files.
No token handling, no network interception, no reverse engineering.

## D-003: Scope
The project is a utility, not a Codex plugin.

## D-004: Storage
Cloud folder can be OneDrive, Dropbox, Syncthing, Google Drive mirror, etc, or a network folder.

## D-005: Conflict policy
Single-writer assumption.
User should not actively work in Codex on two machines at the same time.

## D-006: Initial platform
Windows first.

## D-007: Operational handoff contract
The expected workflow is strict and manual:
close Codex on machine A, wait for cloud propagation, then sync on machine B.

## D-008: Responsibility boundary for cloud environment
The utility does not verify cloud client process status or free space in cloud/network storage.
These checks are out of scope and owned by the user.

## D-009: CI target matrix for MVP
CI runs on Windows and macOS runners (`windows-latest`, `macos-latest`).
Linux CI is intentionally disabled for MVP until Linux runtime support is explicitly in scope.

## D-010: Preflight diagnostics mode
The CLI provides `doctor` and `preflight` commands (equivalent behavior).
These checks are read-mostly and validate runtime readiness before sync:
- config/runtime path readiness
- local/cloud/backup/temp write access probes
- Codex process precondition
- manifest data-version compatibility
- suspicious mtime drift between local/cloud probes
- orphan temp file detection

If any preflight check fails, the command exits with code `5` (`fail-safe`).
