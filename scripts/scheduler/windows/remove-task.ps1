param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "task.config.ps1")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

. $ConfigPath

if ([string]::IsNullOrWhiteSpace($TaskName)) {
    throw "TaskName is empty in config: $ConfigPath"
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "Task does not exist: $TaskName"
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Task removed: $TaskName"
