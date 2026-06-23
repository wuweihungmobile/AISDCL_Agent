# reschedule_g0_gatecheck.ps1 -- move the one-time SD_09 W0 G0 gate-check to the real ready date
# Why: AutoClaude_SD09_G0_GateCheck was set to 2026-06-26 09:00, but observation gates
#   #2 (AC4, ready ~06-28) and #3 (obs/drift, ready ~06-29) will NOT be met by 06-26.
#   Binding constraint = #3 = 2026-06-29. 09:00 fires AFTER that day's 02:00 nightly,
#   so it captures the final accrual. Also adds missed-run catch-up (same root-cause fix
#   as fix_nightly_catchup.ps1) so a powered-off machine does not skip the gate check.
# Requires elevation (Set-ScheduledTask on this S4U task needs admin). Run once ELEVATED.
# Idempotent: safe to re-run.
# ASCII-only on purpose: PowerShell 5.1 parses non-BOM UTF-8 as ANSI -> mojibake.

$ErrorActionPreference = 'Stop'
$TaskName = 'AutoClaude_SD09_G0_GateCheck'
$TargetWhen = Get-Date '2026-06-29 09:00:00'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Administrator rights required. Re-open PowerShell via 'Run as administrator' and re-run this script."
    exit 1
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Warning "Task '$TaskName' not found. Nothing to reschedule."
    exit 1
}

# new one-time trigger at the target date
$trigger = New-ScheduledTaskTrigger -Once -At $TargetWhen
Set-ScheduledTask -TaskName $TaskName -Trigger $trigger | Out-Null

# catch-up protection (machine off at 09:00 -> run when available; do not block on battery)
$t = Get-ScheduledTask -TaskName $TaskName
$t.Settings.StartWhenAvailable = $true
$t.Settings.DisallowStartIfOnBatteries = $false
Set-ScheduledTask -TaskName $TaskName -Settings $t.Settings | Out-Null

$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
$v = (Get-ScheduledTask -TaskName $TaskName).Settings
Write-Output "NextRunTime                = $($info.NextRunTime)   (expected 2026-06-29 09:00)"
Write-Output "StartWhenAvailable         = $($v.StartWhenAvailable)   (expected True)"
Write-Output "DisallowStartIfOnBatteries = $($v.DisallowStartIfOnBatteries)   (expected False)"
if ($info.NextRunTime -and $info.NextRunTime.Date -eq $TargetWhen.Date -and $v.StartWhenAvailable) {
    Write-Output "[OK] G0 gate-check rescheduled to 2026-06-29 09:00 with catch-up protection."
} else {
    Write-Warning "[FAIL] reschedule did not take effect; check permissions/output above."
    exit 1
}
