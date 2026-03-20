# codexSync

Open-source utility for syncing local Codex state between multiple Windows machines using a cloud-synced folder.

## Why

Developers may want to continue working with Codex on another machine without losing local session state.

## What this does

* Syncs local Codex state directory
* Works only after Codex process is closed
* Uses any cloud-synced folder (Dropbox, OneDrive, Syncthing, etc.)

## What this does NOT do

* No integration with Codex internals
* No API usage
* No token extraction
* No network interception
* No real-time sync
* No checks for cloud client process/health
* No checks for free space in cloud/network storage

## Design principles

* Simple and predictable
* Safe (no corruption)
* Offline-friendly
* Backup-first
* Windows-first

## How it works (MVP)

1. Detect if Codex is running
2. If not running:

   * Compare local and cloud state
   * Sync newer files
   * Create backup before overwrite

## Conflict policy

`conflict.policy` supports:

- `manual_abort`: report conflict and stop (default)
- `prefer_cloud`: auto-resolve conflict by taking cloud version
- `prefer_local`: auto-resolve conflict by taking local version
- `prefer_newer_mtime`: auto-resolve conflict by taking side with newer mtime

## Logging

- Levels: `DEBUG|INFO|WARNING|ERROR`
- Formats (configurable): `text|json|logfmt`
- Rotation: retention-based, default `7` days

## CLI commands

Run from project root:

```powershell
python -m codexsync -c config.toml <command>
```

Validation:

```powershell
python -m codexsync -c config.toml validate
```

Build sync plan (no changes):

```powershell
python -m codexsync -c config.toml plan
```

Build plan with process snapshot (`--verbose`):

```powershell
python -m codexsync -c config.toml -v plan
```

Sync simulation (safe test):

```powershell
python -m codexsync -c config.toml sync --dry-run
```

Sync simulation with process snapshot (`--verbose`):

```powershell
python -m codexsync -c config.toml -v sync --dry-run
```

Real sync (writes files):

```powershell
python -m codexsync -c config.toml sync --apply
```

Typical handoff to another machine:

```powershell
python -m codexsync -c config.toml sync --apply
```

Restore from latest backup snapshot to local state:

```powershell
python -m codexsync -c config.toml restore --apply
```

Restore from specific backup snapshot:

```powershell
python -m codexsync -c config.toml restore --from <snapshot_dir_name> --apply
```

Restore to cloud target instead of local:

```powershell
python -m codexsync -c config.toml restore --target cloud --apply
```

Preview restore without writing:

```powershell
python -m codexsync -c config.toml restore --dry-run
```

List CLI help:

```powershell
python -m codexsync -h
```

Process termination behavior:

- On Windows, if Codex is still running during `sync`/`restore`, codexSync can terminate Codex processes before continuing.
- By default, manual GUI confirmation is enabled (`process_detection.manual_terminate_confirmation = true`).
- Background process tracking is configured by OS in `process_detection.background_process_names`:
  - `windows = ["codex-windows-sandbox"]`
  - `macos = []`
  - `linux = []`
- Confirmation channel is configured by `process_detection.terminate_confirmation_mode = "gui" | "console"` (default: `gui`).
- All confirmation prompts are in English in both GUI and console modes.
- If `codex-windows-sandbox` is detected, codexSync reports that Codex is still running and exits with code `3` (no auto-terminate).
- If `codex.exe` is running but `codex-windows-sandbox` is not detected, codexSync asks whether to terminate Codex and continue.
- You can force manual confirmation from CLI:

```powershell
python -m codexsync -c config.toml --manual-terminate-confirmation sync --apply
```

- On macOS/Linux, previous behavior is kept: running Codex process fails safety precondition.
- `--verbose` works for `plan`, `sync --dry-run`, `sync --apply`, `restore --dry-run`, and `restore --apply`; it logs tracked processes with PID/name.
- `--verbose` works for `plan`, `sync --dry-run`, `sync --apply`, `restore --dry-run`, and `restore --apply`.
- In verbose mode on Windows, codexSync logs only:
  - whether `codex.exe` is running,
  - whether `codex-windows-sandbox` is detected,
  - subprocesses under `codex.exe` (PID/name/cmd).

Termination-related exit codes for automation:

- `3` Codex is running / sandbox detected / user rejected termination
- `5` termination was approved but failed before timeout (fail-safe)

## CLI exit codes

- `0` success
- `1` runtime error
- `2` conflict detected (manual resolution required)
- `3` Codex is running (cold sync precondition failed)
- `4` invalid config or CLI arguments
- `5` safe abort (`fail-safe`)

## Required operation protocol

This tool assumes a strict handoff flow between machines:

1. Close Codex on machine A.
2. Wait until cloud sync fully propagates machine A changes.
3. Run codexSync on machine B.
4. Start Codex on machine B only after sync completes.
5. Sign in to Codex again on machine B after file sync.

Important: per OpenAI licensing constraints, authentication tokens are not transferred by codexSync.

The project intentionally does not verify cloud-provider sync status, cloud client process state, or free space on cloud/network storage. These are user responsibilities.

## Status

MVP (ready for public repository and community testing)

## Publishing

See release checklist: [docs/PUBLISHING.md](./docs/PUBLISHING.md)

## Licensing

This project uses dual licensing:

- Open-source license: `GPL-3.0-or-later` (see [LICENSE](./LICENSE))
- Commercial licensing path: see [COMMERCIAL_LICENSE.md](./COMMERCIAL_LICENSE.md)

Contributions are accepted under project contribution terms in:

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CLA.md](./CLA.md)
