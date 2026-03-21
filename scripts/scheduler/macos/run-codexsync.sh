#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${1:?python binary is required}"
PROJECT_DIR="${2:?project dir is required}"
CONFIG_FILE="${3:?config file is required}"
MODE="${4:-dry-run}"

if [[ "$MODE" != "dry-run" && "$MODE" != "apply" ]]; then
  echo "MODE must be dry-run or apply, got: $MODE" >&2
  exit 2
fi

cd "$PROJECT_DIR"

args=(-m codexsync -c "$CONFIG_FILE" sync)
if [[ "$MODE" == "apply" ]]; then
  args+=(--apply)
else
  args+=(--dry-run)
fi

exec "$PYTHON_BIN" "${args[@]}"
