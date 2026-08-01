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

.NOTES
    🔴 退出碼契約（R68；.sh／.ps1 兩側逐碼同語意，規格側見
    workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md「退出碼契約」節。
    修改任一側前先讀該節——兩側原本各自在註解裡枚舉「已占用」而未看對面，
    導致同一失敗條件〔PATH 上無可用 python〕bash 回 5、pwsh 回 7）：
      0=收斂／乾淨收工　1=dry-run advisory 訊號（僅 warn）
      2=dry-run structural fail 訊號　3=缺 claude CLI
      4=ESCALATION（retry budget 用盡）　5=無可用 python 直譯器
      6=平台前置不足（PowerShell < 7；bash 側不適用，保留不重用）
      7=git 操作失敗（git switch -c）　64=未知參數（usage，僅 bash 側）
      8=SSOT WindowsAppsGuard.ps1 缺席（僅 .ps1 側；bash 側因 POSIX 無 WindowsApps
        空殼陷阱而採降級回退，兩側於此刻意不對等，理由見下方 guard 區段註解）
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
    exit 6  # R68 退出碼契約：6=平台前置不足（原為 5，與 bash 側「無可用 python」碰撞）
}

$ErrorActionPreference = "Stop"
# 顯式關閉：讓原生指令（git）非零 exit code 一律走 $LASTEXITCODE 顯式檢查，
# 不讓 $PSNativeCommandUseErrorActionPreference（pwsh 7.3+ 預設 $true，行為隨版本/
# 設定而異，見下方 FSE_APPLY 段落註解）把它另外升級成例外，避免顯式檢查變成
# 版本相依的不可達分支——這是本腳本唯一支援版本無關的判斷依據。
$PSNativeCommandUseErrorActionPreference = $false
$OutputEncoding = [System.Text.Encoding]::UTF8
# 讓 python 子進程 open() 一律 utf-8（Windows 預設 cp950 會爆 UTF-8 JSON）
$env:PYTHONUTF8 = "1"

# 框架根 = 本腳本的祖父目錄（tools/arch_fitness/ → AISDLC_SDD_v0.01/）
$FrameworkRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $FrameworkRoot
$ReportDir = Join-Path $FrameworkRoot "build/reports/fse"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

# R44 跨平台複審：本檔的 Invoke-Fitness／FSE_APPLY／FSE_VERIFY 三處直接呼叫
# python，先前從未做過任何可用性判斷——全新未裝真 Python 的 Windows 11 機器上，
# `Get-Command python` 仍會命中 WindowsApps App Execution Alias 空殼（找得到但
# 執行只跳出 Microsoft Store 安裝提示）。dot-source 共用 guard（比照
# tools/bootstrap.ps1／tools/dev_start.ps1／LATEST install_post_commit.ps1 三個
# 已收斂呼叫點），在首次呼叫 python 前 fail-loud。
# 🔴 R68 誠實劃界（本輪**刻意不做**「缺席即降級」）：guard 位於 monorepo 根（框架版本根
# 之外兩層），框架被單獨 clone／經同版 tools/init_project.sh 部署到使用者專案後該路徑不
# 存在，故本檔在非 monorepo 佈局下確實跑不起來——這是**已知且未修**的缺口（R68 Scan-A2）。
# 曾嘗試比照 bash 側改為「缺席則降級為 Get-Command python」，經
# tools/tests/test_windowsapps_guard_cross_consistency.py::
# test_python_calls_in_ps1_all_go_through_ssot 攔下並判定為真陽性：降級路徑會讓
# $PythonUsable 在**未經 Test-IsRealPython** 的情況下為真，而 WindowsApps 空殼陷阱恰恰
# 只在 Windows 成立 ⇒ 降級等於在唯一有此陷阱的平台上關掉唯一的防線（bash 側可以降級，
# 正因為 POSIX 根本沒有這個陷阱——兩側「不對等」在此是正確的，不是缺陷）。
# 正解是讓 SSOT 可攜（部署時一併帶出 guard），成本超出本輪授權面，留待後輪。
$RepoRoot = Split-Path -Parent (Split-Path -Parent $FrameworkRoot)
$WindowsAppsGuardPath = Join-Path $RepoRoot "tools/lib/WindowsAppsGuard.ps1"
if (-not (Test-Path $WindowsAppsGuardPath)) {
    Write-Host "ERROR: 找不到共用函式 $WindowsAppsGuardPath（tools/lib/WindowsAppsGuard.ps1）— 請在完整 monorepo checkout 內執行本腳本" -ForegroundColor Red
    exit 8  # R68 退出碼契約：8=SSOT guard 缺席（monorepo 佈局前提不成立；.ps1 側限定）
}
. $WindowsAppsGuardPath
if (-not (Test-IsRealPython -CandidateName 'python')) {
    Write-Host "ERROR: 找不到可用的 python 直譯器（PATH 上找不到，或僅命中 WindowsApps 空殼）" -ForegroundColor Red
    exit 5  # R68 退出碼契約：5=無可用 python（原為 7，與 bash 側 5 不對等）
}

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
    if ($LASTEXITCODE -ne 0) {
        # 鏡像 .sh 側 `set -e` 對「單獨陳述式」的語意：git switch -c 失敗必須立即中止，
        # 不可能落到分支已建立失敗、卻仍往下對錯誤分支跑 APPLY 的狀態。
        # 不可倚賴 $ErrorActionPreference="Stop" 讓原生指令失敗自動終止腳本——
        # 這只在 pwsh 7.3+ 且 $PSNativeCommandUseErrorActionPreference 維持預設 $true 時成立，
        # 本腳本僅要求 PSVersion.Major -ge 6，故顯式檢查 $LASTEXITCODE 才是跨版本一致的作法。
        Write-Host "FSE_FATAL：git switch -c 失敗（exit $LASTEXITCODE），中止（鏡像 .sh 側 set -e 語意）。" -ForegroundColor Red
        exit 7  # R68 退出碼契約：7=git 操作失敗（原為 6，該碼已改配給「平台前置不足」）
    }
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
            # 鏡像 .sh 側 `git add -A && git commit ...` 的短路語意：add 失敗時 commit 不得執行，
            # 且 add/commit 失敗時不得標記 $applied（避免「驗證段過但未真正 commit」被當作
            # 已解決放行）——舊寫法先無條件印 FSE_COMMIT、再無條件設 $applied=$true/break，
            # add 失敗時仍會落到「已完成」狀態，與驗證意圖不符。
            git add -A
            if ($LASTEXITCODE -eq 0) {
                git commit -m "fse: 修正 arch_fitness finding $($top.fingerprint)" | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host ("FSE_COMMIT：通過（score {0} → {1}）。" -f $scoreBefore, $scoreAfter) -ForegroundColor Green
                    $applied = $true
                    break
                }
                Write-Host "FSE_WARN：git commit 失敗（exit $LASTEXITCODE），本次嘗試視為未完成，進入 rollback 重試。" -ForegroundColor Yellow
            } else {
                Write-Host "FSE_WARN：git add 失敗（exit $LASTEXITCODE），本次嘗試視為未完成，進入 rollback 重試。" -ForegroundColor Yellow
            }
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
