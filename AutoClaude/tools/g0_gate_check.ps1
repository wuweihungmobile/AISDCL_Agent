# g0_gate_check.ps1 -- SD_09 W0 G0 gate check (improving_34 schedule artifact)
# Purpose: re-verify observation gates #1/#2/#3; write result to logs/.
#   Run manually anytime, or fired once by a one-time schtasks on 2026-06-26.
# Zero-trust: only reads real local jsonl honestly; never fabricates nightly / inflates progress.
# Path: current monorepo d:\CursorProject\AISDCL_Agent\AutoClaude (NOT old d:\CursorProject\AutoClaude).
# ASCII-only on purpose: PowerShell 5.1 parses non-BOM UTF-8 as ANSI -> mojibake; keep this script ASCII.

$ErrorActionPreference = 'Continue'
$Repo = 'd:\CursorProject\AISDCL_Agent\AutoClaude'
Set-Location $Repo

$stamp = Get-Date -Format 'yyyy-MM-dd'
$Log = Join-Path $Repo "logs\g0_gate_check_$stamp.log"
if (-not (Test-Path (Split-Path $Log))) { New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null }

function W($m) { $line = "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK') $m"; Write-Output $line; Add-Content -Path $Log -Value $line }

W "=== SD_09 W0 G0 gate check START (action list: docs/04_planning/AutoSDD_improving_34.md SS4) ==="
W "repo=$Repo"

# --- #2 AC4 (need ready_for_labeled_pr=true / 14 days) ---
W "--- #2 AC4 progress (ac4_progress_check --json) ---"
$ac4 = python tools/ac4_progress_check.py --history .ac4_history.jsonl --json 2>&1 | Out-String
W $ac4
$ac4_ready = $ac4 -match '"ready_for_labeled_pr"\s*:\s*true'

# --- #3 observability/drift (need green_streak>=30) ---
W "--- #3 observability GA (observability_ga_check) ---"
$obs = python tools/observability_ga_check.py --history .observability_history.jsonl 2>&1 | Out-String
W $obs
$obs_pass = $obs -match '\[PASS\]'

# --- #1 mutation unique sha (frozen => waiting for W1 token_guard source change) ---
W "--- #1 mutation last source_sha256 (frozen=waiting for W1) ---"
$mut = Get-Content .mutation_history.jsonl -ErrorAction SilentlyContinue | Select-Object -Last 1
W ($mut | Out-String)

# --- verdict ---
W "=== VERDICT ==="
if ($ac4_ready -and $obs_pass) {
  W "[G0-READY] #2 + #3 both passed -> run G0 action list (AutoSDD_improving_34.md SS4):"
  W "  1) create needs-pg-e2e labeled PR; update SD08_AC_Matrix.md AC4-2 pass date"
  W "  2) use #3 + #1 as W5 db_only cutover dual-condition (ADR-SD09-001 SS2.2)"
  W "  3) start W1 GoalSynthesis mutation pilot (axis-D safe zone; legal token_guard source change unlocks #1 unique sha)"
  W "  4) record gate_audit.md SS1-septies SD09-G0 + confirm ADR formal approval"
} else {
  $miss = @()
  if (-not $ac4_ready) { $miss += "#2 AC4 not ready (see observation_days/green_streak above; need 14 days no gap)" }
  if (-not $obs_pass)  { $miss += "#3 obs/drift not ready (need green_streak>=30; a missed nightly day pushes it back; check schtasks 02:00)" }
  W ("[G0-NOT-READY] gaps: " + ($miss -join ' ; '))
  W "note: gates accumulate via local schtasks 02:00 run_local_nightly.ps1; trailing window is sensitive to missed days."
}
W "=== check DONE (log: $Log) ==="
