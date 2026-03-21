# Edit this file before running install-task.ps1

$TaskName = "codexSyncSync"
$PythonExe = "python"
$ProjectDir = "D:\codexSync"
$ConfigFile = "D:\codexSync\config.toml"

# Allowed values: dry-run | apply
$Mode = "dry-run"

# Run every N minutes
$IntervalMinutes = 15

# First run time in local timezone, format HH:mm
$StartTime = "09:00"

# Where run-codexsync.ps1 writes execution output
$LogDir = "D:\codexSync\logs"
