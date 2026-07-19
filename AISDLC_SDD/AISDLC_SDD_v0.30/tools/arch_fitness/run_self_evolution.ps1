<#
.SYNOPSIS
    SDD Self-Evolution 有界驅動器（Windows / PowerShell）。

.DESCRIPTION
    驅動 workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md 的 FSE 狀態機：
      SENSE → TRIAGE → PROPOSE →（🔴 人工閘）→ APPLY → VERIFY → COMMIT｜ROLLBACK
    反死循環五道防線全部內建：硬迭代上限、單 finding retry budget、
    收斂不變量（fitness 分數須嚴格下降）、同指紋復現偵測、claude -p --max-turns。

    預設 -DryRun：只跑 SENSE 量測並印出「將執行的 claude -p 指令」，不改任何檔、
    不需 claude CLI、不連網。加 -Apply 才實際呼叫 claude -p 並進入人工閘。

.PARAMETER MaxIterations
    硬迭代上限（防線 1）。預設 3。

.PARAMETER RetryBudget
    單一 finding 的修正重試上限（防線 2，鏡像 Rule 9.1）。預設 3。

.PARAMETER Apply
    實際套用模式。省略則為 dry-run（安全預設）。

.EXAMPLE
    pwsh tools/arch_fitness/run_self_evolution.ps1
    pwsh tools/arch_fitness/run_self_evolution.ps1 -Apply -MaxIterations 2
#>
[CmdletBinding()]
param(
    [int]$MaxIterations = 3,
    [int]$RetryBudget = 3,
    [switch]$Apply
)

# R13 SH-2（比照 fsm_runtime/formal/run_tlc.ps1 的 R9 D-1 導流；DEF-101-124 同款病灶）：
# 本腳本的 native stderr 重定向模式（`git … 2>$null`，見 FSE_ROLLBACK 清理行）在
# Windows PowerShell 5.1 + $ErrorActionPreference=Stop 下會把 stderr 行包成 ErrorRecord
# 拋 NativeCommandError 中斷——引擎級行為，pwsh 7+ 無此問題。與其讓使用者在迭代中途
# 撞難解錯誤，這裡明確 fail-loud 導流。
if ($PSVersionTable.PSVersion.Major -lt 6) {
    Write-Host "ERROR: 本腳本需 pwsh 7+（PowerShell 5.1 對 native stderr 的 ErrorRecord 包裝會在 git 清理行中斷）。" -ForegroundColor Red
    Write-Host "  請改用：pwsh tools/arch_fitness/run_self_evolution.ps1" -ForegroundColor Yellow
    exit 5  # 獨立退出碼：1/2=dry-run 訊號、3=缺 claude、4=ESCALATION 皆已占用
}

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
# 讓 python 子進程 open() 一律 utf-8（Windows 預設 cp950 會爆 UTF-8 JSON）
$env:PYTHONUTF8 = "1"

# 框架根 = 本腳本的祖父目錄（tools/arch_fitness/ → AISDLC_SDD_v0.01/）
$FrameworkRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $FrameworkRoot
$ReportDir = Join-Path $FrameworkRoot "build/reports/fse"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

function Invoke-Fitness {
    param([string]$JsonOut)
    # --quiet 只寫 JSON，避免主控台編碼問題；退出碼 0/1/2 由呼叫端解讀
    python -m tools.arch_fitness.arch_fitness --strict --quiet --json $JsonOut | Out-Null
    return (Get-Content -Raw -Encoding utf8 $JsonOut | ConvertFrom-Json)
}

function Get-TopFinding {
    param($Report)
    # ROI：fail 優先於 warn；同級取第一個非 info。
    $cand = $Report.findings | Where-Object { $_.severity -ne "info" }
    $fail = $cand | Where-Object { $_.severity -eq "fail" } | Select-Object -First 1
    if ($fail) { return $fail }
    return ($cand | Select-Object -First 1)
}

Write-Host "=== FSE_SENSE：架構適應度量測 ===" -ForegroundColor Cyan
$baseJson = Join-Path $ReportDir "findings.json"
$report = Invoke-Fitness -JsonOut $baseJson
$scoreBefore = [int]$report.score
Write-Host ("基準加權缺陷分數 score={0}（fail={1} warn={2}）" -f $scoreBefore, $report.n_fail, $report.n_warn)

if ($scoreBefore -eq 0) {
    Write-Host "FSE_DONE：架構已收斂（score=0），無需演化。" -ForegroundColor Green
    exit 0
}

$claudeAvailable = [bool](Get-Command claude -ErrorAction SilentlyContinue)
if (-not $Apply) {
    Write-Host "`n[Dry-Run] 偵測到 $($report.n_fail) 個 structural fail / $($report.n_warn) 個 advisory。" -ForegroundColor Yellow
    $top = Get-TopFinding -Report $report
    if ($top) {
        Write-Host "最高 ROI finding：[$($top.ff)] $($top.title)  (fingerprint=$($top.fingerprint))"
        Write-Host "`n[Dry-Run] FSE_PROPOSE 將執行（需 -Apply 才實跑）："
        Write-Host "  claude -p `"針對 finding $($top.fingerprint) 產出根因+最小變更+blast radius+rollback`" ``"
        Write-Host "         --max-turns 6 --allowedTools `"Read`" `"Grep`" `"Glob`" --permission-mode plan --output-format json"
    }
    Write-Host "`n加 -Apply 進入完整 SENSE→...→VERIFY 有界閉環（含 🔴 人工閘）。"
    # 寫法沿革：早期為相容 PS 5.1 避開三元運算子；R13 起檔頭已強制 pwsh 7+
    # （SH-2 導流，PS 5.1 於 native stderr 重定向處必崩），非三元寫法保留無害
    if ($report.n_fail -gt 0) { exit 2 } else { exit 1 }
}

if (-not $claudeAvailable) {
    Write-Host "找不到 claude CLI；-Apply 需要它。請先安裝 Claude Code。" -ForegroundColor Red
    exit 3
}

# ===== 有界閉環 =====
for ($iter = 1; $iter -le $MaxIterations; $iter++) {
    Write-Host "`n========== 迭代 $iter / $MaxIterations ==========" -ForegroundColor Cyan
    $report = Invoke-Fitness -JsonOut $baseJson
    $scoreBefore = [int]$report.score
    if ($scoreBefore -eq 0) { Write-Host "FSE_DONE：score=0，收斂。" -ForegroundColor Green; exit 0 }

    $top = Get-TopFinding -Report $report
    if (-not $top) { Write-Host "FSE_DONE：僅剩 info，收斂。" -ForegroundColor Green; exit 0 }
    if ($top.severity -ne "fail") {
        Write-Host "FSE_DONE：僅剩 advisory（$($top.ff)），依設計不自動修。" -ForegroundColor Green; exit 0
    }
    Write-Host "FSE_TRIAGE：選定 [$($top.ff)] $($top.title)"

    # FSE_PROPOSE（唯讀）
    Write-Host "FSE_PROPOSE：產出提案..."
    $proposal = claude -p "針對 arch_fitness finding fingerprint=$($top.fingerprint)（$($top.title)）產出：①根因 ②最小變更方案 ③blast radius ④rollback 步驟。只規劃不改檔。" --max-turns 6 --allowedTools "Read" "Grep" "Glob" --permission-mode plan
    Write-Host $proposal

    # FSE_HUMAN_GATE（🔴 Rule 8）
    $ans = Read-Host "`n🔴 核可此提案並套用？(yes/no/skip)"
    if ($ans -eq "skip") { Write-Host "跳過此 finding。"; continue }
    if ($ans -ne "yes") { Write-Host "人工駁回，停機。"; exit 0 }

    # FSE_APPLY（隔離分支）+ retry budget
    $branch = "fse/$($top.fingerprint)-$(Get-Date -Format yyyyMMddHHmmss)"
    git switch -c $branch | Out-Null
    $applied = $false
    for ($r = 1; $r -le $RetryBudget; $r++) {
        Write-Host "FSE_APPLY（嘗試 $r/$RetryBudget，branch=$branch）..."
        claude -p "依已核可提案實作 arch_fitness finding $($top.fingerprint) 的修正。改完自行 pytest。" --max-turns 12 --allowedTools "Edit" "Write" "Bash(python -m pytest:*)" --permission-mode acceptEdits | Out-Host

        # FSE_VERIFY：測試 + 收斂閘
        Write-Host "FSE_VERIFY：pytest + fitness..."
        python -m pytest -m "not chaos" -q
        $pytestOk = ($LASTEXITCODE -eq 0)
        $after = Invoke-Fitness -JsonOut (Join-Path $ReportDir "findings-after.json")
        $scoreAfter = [int]$after.score
        $stillThere = $after.findings | Where-Object { $_.fingerprint -eq $top.fingerprint }

        if ($pytestOk -and ($scoreAfter -lt $scoreBefore) -and (-not $stillThere)) {
            Write-Host ("FSE_COMMIT：通過（score {0} → {1}）。" -f $scoreBefore, $scoreAfter) -ForegroundColor Green
            git add -A; git commit -m "fse: 修正 arch_fitness finding $($top.fingerprint)" | Out-Null
            $applied = $true
            break
        }

        # 同指紋復現（防線 4）
        if ($stillThere) { Write-Host "同指紋復現，修正未生效。" -ForegroundColor Yellow }
        Write-Host ("FSE_ROLLBACK：未收斂（pytest={0} score {1}→{2}），復原。" -f $pytestOk, $scoreBefore, $scoreAfter) -ForegroundColor Yellow
        git restore --staged . 2>$null; git checkout -- . 2>$null; git clean -fd 2>$null | Out-Null
    }

    if (-not $applied) {
        Write-Host "FSE_ESCALATION：finding $($top.fingerprint) 連 $RetryBudget 次未收斂，停機等待人工。" -ForegroundColor Red
        git switch - | Out-Null
        exit 4
    }
    git switch - | Out-Null
}

Write-Host "`nFSE_DONE：達迭代上限 $MaxIterations，乾淨收工。" -ForegroundColor Green
exit 0
