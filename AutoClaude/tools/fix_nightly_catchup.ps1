# fix_nightly_catchup.ps1 -- one-shot remediation for AutoClaude_Nightly missed-run gap
# Root causes of missed schtasks runs (must ALL be covered, else observation-period idle gaps):
#   (1) machine POWERED OFF at scheduled time      -> StartWhenAvailable=true  (catch-up after boot)
#   (2) machine ASLEEP/HIBERNATING at sched. time  -> WakeToRun=true           (wake to run)
#   (3) laptop ON BATTERY                           -> DisallowStartIfOnBatteries=false (do not block)
#   Note 2026-06-23: 06-19~21 missed = powered off + StartWhenAvailable=false (Windows event 153).
#   Note (2026-06-30 ops hotfix): WakeToRun was only PRINTED, never SET -> sleep/hibernate at 02:00 still missed.
# WakeToRun caveat: also requires the power plan's wake timers to be allowed. If runs still miss while
#   asleep, run (elevated):  powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1; powercfg /SETACTIVE SCHEME_CURRENT
# Requires elevation (Set-ScheduledTask on this S4U task needs admin). Run once in an ELEVATED PowerShell.
# Idempotent: safe to re-run; only flips the settings and re-verifies.
# ASCII-only on purpose: PowerShell 5.1 parses non-BOM UTF-8 as ANSI -> mojibake breaks the parser.

$ErrorActionPreference = 'Stop'
$TaskName = 'AutoClaude_Nightly'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Administrator rights required. Re-open PowerShell via 'Run as administrator' and re-run this script."
    exit 1
}

$t = Get-ScheduledTask -TaskName $TaskName
$t.Settings.StartWhenAvailable = $true            # (1) powered off: run catch-up after boot when a start was missed
$t.Settings.WakeToRun = $true                     # (2) asleep/hibernating: wake the machine to run at scheduled time
$t.Settings.DisallowStartIfOnBatteries = $false   # (3) laptop battery: do not block the run
Set-ScheduledTask -TaskName $TaskName -Settings $t.Settings | Out-Null

$v = (Get-ScheduledTask -TaskName $TaskName).Settings
Write-Output "StartWhenAvailable         = $($v.StartWhenAvailable)   (expected True)"
Write-Output "DisallowStartIfOnBatteries = $($v.DisallowStartIfOnBatteries)   (expected False)"
Write-Output "StopIfGoingOnBatteries     = $($v.StopIfGoingOnBatteries)"
Write-Output "WakeToRun                  = $($v.WakeToRun)   (expected True)"
if ($v.StartWhenAvailable -and $v.WakeToRun -and -not $v.DisallowStartIfOnBatteries) {
    Write-Output "[OK] missed-run protection enabled (powered-off catch-up + sleep wake + battery allowed)."
    Write-Output "[i]  If runs still miss while ASLEEP, the power plan may block wake timers. Run (elevated):"
    Write-Output "     powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1; powercfg /SETACTIVE SCHEME_CURRENT"
} else {
    Write-Warning "[FAIL] settings did not take effect; check permissions."
    exit 1
}
