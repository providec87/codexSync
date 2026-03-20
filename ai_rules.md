# AI Rules

## 1. Scope
- Work only with local files.
- Do not use Codex APIs.
- Do not extract tokens, credentials, or secrets.
- Do not intercept network traffic.
- Do not modify Codex binaries or runtime.
- Do not check cloud client process state.
- Do not check free space in cloud/network storage.

## 2. Mandatory Sync Model
- Cold sync only.
- Sync is allowed only when Codex is fully stopped.
- One active machine at a time.
- Handoff protocol is mandatory:
  1. Close Codex on source machine.
  2. Wait for cloud propagation.
  3. Run sync on target machine.
  4. Start Codex on target machine only after sync is complete.

## 3. Safety Guarantees
- Always create a backup before any overwrite.
- If data state is uncertain, exit without writing.
- Exclude temporary, lock, and cache files from sync.
- Never delete source data without a confirmed backup.

## 4. Technical Requirements
- Minimum Python version: `3.8`.
- Supported OS:
  - Windows `10+`.
  - macOS on `Apple Silicon` (minimum OS version requires separate validation; working target: `14+`).
  - Linux: out of current MVP scope (pending official Codex Linux release).

## 5. Tool Interface Requirements
- CLI-first.
- Configuration file support.
- Detailed logging.
- `--dry-run` mode.
- Scheduled mode:
  - Windows Task Scheduler.
  - macOS LaunchAgent (`launchd`).
- For Windows, `.exe` packaging is allowed.

## 6. Implementation Rules
- Any sync operation must be idempotent within a single run.
- Change comparison: timestamp first, hash when ambiguous.
- Log dangerous actions separately (create backup, overwrite, skip).
- Conflict when both sides changed:
  - Do not perform sync writes.
  - Return conflict code.
  - Print conflict file list.
  - Require manual resolution and rerun.
- No separate file-time normalization in MVP (no UTC conversion and no clock drift compensation).

## 7. CLI Exit Codes
- `0` success (completed or no changes).
- `1` runtime error.
- `2` conflict detected (manual handling required).
- `3` codex running (cold-sync precondition violated).
- `4` config/args error (invalid config or CLI parameters).
- `5` safe abort (fail-safe stop).

## 8. Minimum MVP Test Set
- Unit tests for exclusion filtering.
- Unit tests for source-side selection in comparison logic.
- Integration test for dry-run without disk writes.
- Integration test for backup+overwrite on test directories.
- Integration conflict test: no writes, conflict list output, exit code `2`.

## 9. Definition of Done (MVP)
- Tool blocks sync correctly when Codex is running.
- Creates backup before overwrite in every overwrite scenario.
- Executes dry-run safely with a readable report.
- Works on Windows 10+ and on macOS Apple Silicon in validated test configuration.
- On conflict, performs no writes and exits with code `2`.
