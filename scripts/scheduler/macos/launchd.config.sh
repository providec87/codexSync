# Edit this file before running install-launchd.sh

LABEL="com.codexsync.sync"
PYTHON_BIN="/usr/bin/python3"
PROJECT_DIR="$HOME/codexSync"
CONFIG_FILE="$HOME/codexSync/config.toml"

# Allowed values: dry-run | apply
MODE="dry-run"

# Run every N seconds (example: 900 = 15 minutes)
INTERVAL_SECONDS=900

# true -> run once right after loading
RUN_AT_LOAD=true

STDOUT_LOG="$HOME/codexSync/logs/codexsync-launchd.out.log"
STDERR_LOG="$HOME/codexSync/logs/codexsync-launchd.err.log"
