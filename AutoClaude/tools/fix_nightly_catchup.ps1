# fix_nightly_catchup.ps1 -- one-shot remediation for AutoClaude_Nightly missed-run gap
# Root cause (2026-06-23): 06-19~21 missed = machine powered off at 02:00 + StartWhenAvailable=false (no catch-up).
#   Windows event 153 itself recommended enabling the missed-schedule start option.
# Effect: enable catch-up run after boot; stop battery from blocking the catch-up on laptop.
# Requires elevation (Set-ScheduledTask on this S4U task needs admin). Run once in an ELEVATED PowerShell.
# Idempotent: safe to re-run; only flips the two settings and re-verifies.

$ErrorActionPreference = 'Stop'
$TaskName = 'AutoClaude_Nightly'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "需系統管理員權限。請以『以系統管理員身分執行』開啟 PowerShell 後重跑本腳本。"
    exit 1
}

$t = Get-ScheduledTask -TaskName $TaskName
$t.Settings.StartWhenAvailable = $true            # 開機後補跑錯過的排程
$t.Settings.DisallowStartIfOnBatteries = $false   # 筆電電池時不擋補跑
Set-ScheduledTask -TaskName $TaskName -Settings $t.Settings | Out-Null

$v = (Get-ScheduledTask -TaskName $TaskName).Settings
Write-Output "StartWhenAvailable         = $($v.StartWhenAvailable)   (期望 True)"
Write-Output "DisallowStartIfOnBatteries = $($v.DisallowStartIfOnBatteries)   (期望 False)"
Write-Output "StopIfGoingOnBatteries     = $($v.StopIfGoingOnBatteries)"
Write-Output "WakeToRun                  = $($v.WakeToRun)"
if ($v.StartWhenAvailable -and -not $v.DisallowStartIfOnBatteries) {
    Write-Output "[OK] 漏跑補跑保障已啟用。"
} else {
    Write-Warning "[FAIL] 設定未生效，請檢查權限。"
    exit 1
}
