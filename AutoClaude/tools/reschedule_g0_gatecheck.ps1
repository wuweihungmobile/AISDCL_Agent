# reschedule_g0_gatecheck.ps1 -- re-point the one-time SD_09 W0 G0 gate-check trigger
# Why this script exists: AutoClaude_SD09_G0_GateCheck was first registered for 2026-06-26 09:00,
#   but observation gates #2 (AC4) and #3 (obs/drift) were not going to be met by that day, so the
#   one-time trigger had to be moved to the real ready date. It also (re)applies missed-run catch-up
#   (same root-cause list as fix_nightly_catchup.ps1) so a powered-off machine does not skip the
#   gate check.
# Requires elevation (Set-ScheduledTask on this S4U task needs admin). Run once ELEVATED.
# Idempotent: safe to re-run.
# ASCII-only on purpose: PowerShell 5.1 parses non-BOM UTF-8 as ANSI -> mojibake.
#
# 2026-07-27 -- the target moment is NO LONGER a hardcoded calendar date.
#   It used to be `$TargetWhen = Get-Date '2026-06-29 09:00:00'`, which self-expires: run the script
#   on any later day and it arms a one-time trigger in the PAST. That is not cosmetic. MEASURED that
#   day on this machine (Windows 11 build 26100, Windows PowerShell 5.1.26100.8875, non-elevated,
#   throwaway task) by replaying THIS script's own two-step path -- Set-ScheduledTask -Trigger with
#   -At '2026-06-29 09:00:00', then re-Get: the write lands (the task's stored trigger StartBoundary
#   reads back 2026-06-29T09:00:00+08:00) yet NextRunTime reads back $null, and the verify predicate
#   at the bottom of this file evaluates to False. A future -At reports the exact moment instead.
#   So the operator who follows the documented procedure with the official script gets
#   "[FAIL] reschedule did not fully take effect" and exit 1 -- for a write that actually succeeded.
#   Bumping the literal to some later date would only move the expiry, i.e. the same defect again,
#   so the moment is computed at run time instead:
#     * no -When : Get-G0TargetWhen returns the next $GateHour:00 that is at least $MinLeadMinutes
#                  ahead of now (today's if it still qualifies, otherwise tomorrow's).
#     * -When    : the operator's explicit moment, e.g. -When '2026-08-03 09:00'.
#   Both paths print the adopted moment before anything is written, and both refuse a moment that is
#   not in the future -- silently arming a past trigger is precisely what broke above.
#
# Disposition reminder for maintainers -- this script only RE-POINTS an existing one-time trigger.
#   If the G0 gate has already been signed off, the correct handling is to REMOVE the task
#   (`Unregister-ScheduledTask -TaskName AutoClaude_SD09_G0_GateCheck`), not to keep pushing its
#   trigger forward. Whether the gate is done is gate/PM state and is not observable from here, so
#   this script deliberately does NOT auto-remove anything; it only prints the reminder below.

# CmdletBinding on purpose: an unrecognised argument then becomes a binding error instead of landing
# in $args unnoticed -- a mistyped -Whn must not silently mean "use the derived default".
[CmdletBinding()]
param(
    # Explicit target moment for the one-time trigger. Prefer ISO-ish text ('yyyy-MM-dd HH:mm'):
    # string -> [datetime] binding goes through the current culture (MEASURED zh-TW on this machine)
    # and that layout parses identically under the cultures this repo targets.
    [datetime]$When
)

$ErrorActionPreference = 'Stop'
$TaskName = 'AutoClaude_SD09_G0_GateCheck'
# Hour-of-day for the derived default. 09:00 fires AFTER that day's 02:00 nightly, so the gate check
# captures the final accrual -- the same reason the original hardcoded moment used 09:00.
$GateHour = 9
# Minimum distance into the future for the derived default. Why not zero: the moment must still be
# in the future when the verify block re-reads NextRunTime a few statements later, and an elapsed
# one-time trigger reports NextRunTime = $null (MEASURED, see header) which that block reports as
# [FAIL]. A few minutes of lead stops a run started at 08:59 from producing that false failure.
# Coverage: the $null-on-elapsed-trigger behaviour is MEASURED (2026-07-27, this machine); the exact
# race window between Set-ScheduledTask and the read-back is NOT MEASURED (needs admin on the real
# task at a $GateHour:00 boundary), so this margin is a deliberate cushion, not a measurement.
$MinLeadMinutes = 5

function Get-G0TargetWhen {
    # The next $GateHour:00 that is at least $MinLeadMinutes ahead of $Now.
    # Deliberately a pure function of its arguments (no Get-Date inside): the regression tests in
    # AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py drive it with synthetic clocks,
    # which is the only way to prove "the derived default is never in the past" for every hour of
    # the day rather than for whatever time the test happened to run at.
    param(
        [Parameter(Mandatory = $true)][datetime]$Now,
        [Parameter(Mandatory = $true)][int]$GateHour,
        [Parameter(Mandatory = $true)][int]$MinLeadMinutes
    )
    $candidate = $Now.Date.AddHours($GateHour)
    if ($candidate -lt $Now.AddMinutes($MinLeadMinutes)) {
        $candidate = $candidate.AddDays(1)
    }
    return $candidate
}

$now = Get-Date
if ($PSBoundParameters.ContainsKey('When')) {
    # MEASURED: an unbound [datetime] parameter is $null here (not [datetime]::MinValue), so
    # $PSBoundParameters -- not a value comparison -- is what tells "operator supplied" apart.
    $TargetWhen = $When
    $whenSource = 'from -When'
} else {
    $TargetWhen = Get-G0TargetWhen -Now $now -GateHour $GateHour -MinLeadMinutes $MinLeadMinutes
    $whenSource = 'derived: next {0:00}:00, at least {1} min ahead' -f $GateHour, $MinLeadMinutes
}
# One single source for the moment's text: the verify block below reuses $targetText instead of
# spelling the moment out again (this file used to print a second, hardcoded copy that still said
# 2026-06-29 even for a 2099 trigger). HH\:mm escapes the culture-dependent .NET time separator so a
# non-en-US machine still prints 09:00 (verified on zh-TW).
$targetText = $TargetWhen.ToString('yyyy-MM-dd HH\:mm')
$nowText = $now.ToString('yyyy-MM-dd HH\:mm')
Write-Output "TargetWhen                 = $targetText   ($whenSource; now $nowText)"
Write-Output "[i]  If the G0 gate is already signed off, the correct handling is to REMOVE this task"
Write-Output "     (Unregister-ScheduledTask -TaskName $TaskName), not to reschedule it."

# Refuse a non-future moment BEFORE touching anything -- argument validation first, environment
# checks (elevation, task existence) after, so a bad -When is reported as a bad -When. Arming a
# one-time trigger in the past means either an immediate catch-up run nobody is watching, or the
# NextRunTime = $null that this very script then reports as [FAIL]. Failing loudly here instead of
# quietly writing the past moment is the whole point of the 2026-07-27 change.
if ($TargetWhen -le $now) {
    # Note the wording detail: no ':' straight after an interpolated variable. PowerShell reads
    # "$targetText:" as a scope/drive-qualified variable reference and refuses to parse the file at
    # all (caught by the editor's parser while writing this line), which would turn a fail-loud
    # message into a script that cannot even start.
    Write-Warning "[FAIL] refusing to arm the one-time trigger at $targetText -- that moment is not in the future (now $nowText). Pass a future -When, or omit -When for the derived default."
    exit 1
}

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

# new one-time trigger at the target moment
$trigger = New-ScheduledTaskTrigger -Once -At $TargetWhen
Set-ScheduledTask -TaskName $TaskName -Trigger $trigger | Out-Null

# missed-run protection (2026-06-30 ops hotfix): off -> catch-up; asleep -> wake; battery -> do not block
$t = Get-ScheduledTask -TaskName $TaskName
$t.Settings.StartWhenAvailable = $true
$t.Settings.WakeToRun = $true                     # wake the machine from sleep/hibernate to run at scheduled time
$t.Settings.DisallowStartIfOnBatteries = $false   # do not block start on battery
$t.Settings.StopIfGoingOnBatteries = $false       # do not kill a running job on AC->battery switch
Set-ScheduledTask -TaskName $TaskName -Settings $t.Settings | Out-Null

# Verify ALL FOUR power/catch-up settings, not just two (2026-07-27, first real native
# Windows run of this script's verification block).
# Why this mattered: the old gate only checked NextRunTime + StartWhenAvailable, so a task
# whose StopIfGoingOnBatteries was still True still printed
# "[OK] ... with catch-up protection". Measured on this machine that day,
# AutoClaude_SD09_G0_GateCheck really did have StopIfGoingOnBatteries=True (the schtasks
# default) while every other setting was correct. Consequence on a laptop: switching to
# battery MID-RUN makes Task Scheduler kill the process outright, so the forensic log is
# truncated or absent -- and the operator, having already seen [OK], never comes back to
# look. Four independent failure modes, so all four must be gated (same rationale as
# fix_nightly_catchup.ps1's root-cause list at the top of that file).
# The condition below is deliberately character-for-character the same predicate as
# fix_nightly_catchup.ps1 (its L36), so the two sister scripts cannot drift into two
# different definitions of "the settings are correct".
#
# Remediation note -- do NOT rebuild the task, just re-run this script ELEVATED.
# The Set-ScheduledTask assignments above DO persist; a mismatch here means the elevated
# write never happened (or an older revision of this script ran), not that the field is
# unwritable. Evidence (2026-07-27, Windows 11 build 26100, PowerShell 5.1): on a throwaway
# task, replaying this script's exact two-step sequence -- Set-ScheduledTask -Trigger, then
# re-Get + Set-ScheduledTask -Settings -- read all four values back as intended, including
# StopIfGoingOnBatteries=False, and the exported task XML agreed.
# Coverage of that probe: MEASURED for a task created by the same user in a non-elevated
# session; NOT MEASURED for an elevated write to a pre-existing S4U task (needs admin);
# NOT EXHAUSTIVE across Windows builds or group-policy-managed machines.
$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
$v = (Get-ScheduledTask -TaskName $TaskName).Settings
Write-Output "NextRunTime                = $($info.NextRunTime)   (expected $targetText)"
Write-Output "StartWhenAvailable         = $($v.StartWhenAvailable)   (expected True)"
Write-Output "WakeToRun                  = $($v.WakeToRun)   (expected True)"
Write-Output "DisallowStartIfOnBatteries = $($v.DisallowStartIfOnBatteries)   (expected False)"
Write-Output "StopIfGoingOnBatteries     = $($v.StopIfGoingOnBatteries)   (expected False)"
$powerOk = $v.StartWhenAvailable -and $v.WakeToRun -and -not $v.DisallowStartIfOnBatteries -and -not $v.StopIfGoingOnBatteries
if ($info.NextRunTime -and $info.NextRunTime.Date -eq $TargetWhen.Date -and $powerOk) {
    Write-Output "[OK] G0 gate-check rescheduled to $targetText with catch-up protection."
    Write-Output "[i]  If the run still misses while ASLEEP, the power plan may block wake timers. Run (elevated):"
    Write-Output "     powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1; powercfg /SETACTIVE SCHEME_CURRENT"
} else {
    Write-Warning "[FAIL] reschedule did not fully take effect; compare each line above with its (expected ...) marker. Re-run this script ELEVATED."
    exit 1
}
