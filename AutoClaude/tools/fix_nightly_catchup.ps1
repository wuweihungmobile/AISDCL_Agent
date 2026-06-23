# fix_nightly_catchup.ps1 -- one-shot remediation for AutoClaude_Nightly missed-run gap
# Root cause (2026-06-23): 06-19~21 missed = machine powered off at 02:00 + StartWhenAvailable=false (no catch-up).
#   Windows event 153 itself recommended enabling the missed-schedule start option.
# Effect: enable catch-up run after boot; stop battery from blocking the catch-up on laptop.
# Requires elevation (Set-ScheduledTask on this S4U task needs admin). Run once in an ELEVATED PowerShell.
# Idempotent: safe to re-run; only flips the two settings and re-verifies.
# ASCII-only on purpose: PowerShell 5.1 parses non-BOM UTF-8 as ANSI -> mojibake breaks the parser.

$ErrorActionPreference = 'Stop'
$TaskName = 'AutoClaude_Nightly'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Administrator rights required. Re-open PowerShell via 'Run as administrator' and re-run this script."
    exit 1
}

$t = Get-ScheduledTask -TaskName $TaskName
$t.Settings.StartWhenAvailable = $true            # run catch-up after boot when a scheduled start was missed
$t.Settings.DisallowStartIfOnBatteries = $false   # do not block the catch-up on laptop battery
Set-ScheduledTask -TaskName $TaskName -Settings $t.Settings | Out-Null

$v = (Get-ScheduledTask -TaskName $TaskName).Settings
Write-Output "StartWhenAvailable         = $($v.StartWhenAvailable)   (expected True)"
Write-Output "DisallowStartIfOnBatteries = $($v.DisallowStartIfOnBatteries)   (expected False)"
Write-Output "StopIfGoingOnBatteries     = $($v.StopIfGoingOnBatteries)"
Write-Output "WakeToRun                  = $($v.WakeToRun)"
if ($v.StartWhenAvailable -and -not $v.DisallowStartIfOnBatteries) {
    Write-Output "[OK] missed-run catch-up protection enabled."
} else {
    Write-Warning "[FAIL] settings did not take effect; check permissions."
    exit 1
}
