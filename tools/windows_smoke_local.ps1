#Requires -Version 5.1
# windows_smoke_local.ps1 — Windows 側本地驗證聚合腳本（QA-10 / DEF-101-139 修復；
# 鏡射 tools/macos_smoke_local.sh 的定位與結構）。
#
# 為何存在：GitHub Actions 因帳單問題停擺（DEF-101-081）期間，Windows 側「執行級」
# .ps1 驗證真空——windows-compat-ci.yml 內 install 腳本 worktree 拒絕、
# install_post_commit.ps1 實跑等 step 的唯一載體本身就是死的補償控制。本腳本讓
# Windows 開發者一鍵跑 windows-smoke 中「可本地化」的步驟，與
# .github/workflows/windows-compat-ci.yml 對應 step 同步維護（改那邊記得改這邊）。
#
# 前置需求：git >= 2.31（[5] 用 `git rev-parse --path-format=absolute`）；python
# （install 共用層 tools/git_hooks_install_common.py 與 LATEST 解析 SSOT 都要用）。
# Windows PowerShell 5.1 相容（禁 &&/|| 鏈接、三元、??、?.；$LASTEXITCODE 顯式檢查）。
#
# 涵蓋（對照 windows-compat-ci.yml windows-smoke 各 step；預期 PASS 總數 = 12）：
#   [1] PowerShell parse 檢查：active .ps1 **四棵樹**（根層 tools/ + AutoClaude/tools/
#       + AISDLC_SDD/scripts/ + AISDLC_SDD LATEST 版，皆遞迴）以
#       [System.Management.Automation.Language.Parser]::ParseFile 驗 0 error
#       （對本 repo 直跑、唯讀。凍結版 AISDLC_SDD/AISDLC_SDD_v0.01~v0.(N-1) 依凍結
#       紀律不回改 → 排除；LATEST 由 scripts/sdd_version.py SSOT 解析，空值 Fail-Item。
#       R56 起與 root-infra-ci.yml「pwsh 語法解析」step **同四棵樹**，不再只掃根層
#       子集——原根層子集使 13 支子專案 active .ps1 在 Windows 本機零語法訊號，
#       與同輪 macOS 側 [1/7] 擴面後方向相反的不對稱。附 per-tree 檔數下限釘選）
#   [-] fake repo 建立（git clone -c core.longpaths=true HEAD → OS temp；記 1 點）
#   [2] AutoClaude/tools/install_git_hooks.ps1 於 fake repo 安裝／解除往返
#   [3] install_git_hooks.ps1 於 linked worktree 內應拒絕 exit 1（worktree add 顯式
#       檢查失敗即 FAIL、Push-Location 失敗走哨兵 rc=9——同 DEF-101-135「worktree add
#       未檢查→假 PASS」防護，本 .ps1 版第一天就帶）
#   [4] AISDLC_SDD/scripts/install-hooks.ps1 安裝往返 + linked worktree 拒絕（各記 1 點）
#   [5] LATEST install_post_commit.ps1 於 linked worktree 實跑 + 安裝路徑斷言
#       （--git-common-dir 下 hooks/post-commit 存在、內容含 post_commit_drift.py 與
#       closure_evidence_verify.py）+ worktree 移除「後」內嵌路徑仍存在於磁碟
#       （2026-07-16 P1 回歸鎖，鏡射 windows-compat-ci 對應 step）。LATEST 一律由
#       SSOT resolver AISDLC_SDD/scripts/sdd_version.py 解析（DEF-101-133，禁止自行
#       實作版本 glob/regex）；resolver 檔案取自「真 repo」路徑、--sdd-root 指向
#       fake repo——resolver 屬驗證工具、不必來自被測樹（且其未 commit 期 HEAD
#       clone 內沒有它，取真 repo 路徑才能運作）。
#   [6] 非 ASCII 路徑防護抽驗：於含中文名的 temp 子目錄（煙霧測試）clone fake repo，
#       跑 [2] 同款安裝往返一次，並直讀 .git/config（UTF-8 bytes、不經主控台解碼）
#       斷言 core.hooksPath 保有「煙霧測試」片段未被編碼損毀（cp950 炸裂是 R9 修復
#       主題；對應 windows-compat-ci install_post_commit 編碼斷言的精神抽驗）
#   [7] install_git_hooks.ps1 於「-Command 非典型呼叫鏈」下 linked worktree 拒絕仍生效
#       （R27 訂正 DEF-101-263④：該列原判定「pwsh -Command 包裝 dot-source 呼叫全庫
#       零命中、純理論性」，本輪以 `powershell -NoProfile -Command "& '<installer>'"`
#       重現：tools/lib/GitHooksInstallCommon.ps1 的 dot-source 陷阱防護若只檢查呼叫棧
#       「最外層」frame 的 ScriptName，此類非 -File 頂層呼叫會讓 Assert-NotLinkedWorktree
#       失敗分支從 exit 1 靜默降級為 return，linked worktree 防呆因而失效。已改為改看
#       呼叫棧 [1]（dot-source 點的直接呼叫者）是否有真實 .ps1 檔案，本步驟即為此修復
#       的回歸鎖）
#   [8] check_ntfs_paths.py + check_script_parity.py（唯讀，直接對本 repo；R18 全面
#       掃描補齊——這兩支純 Python、平台無關的檢查先前僅由 macos_smoke_local.sh [5]
#       覆蓋，Windows 本機 smoke 從未在 Windows 環境下實際跑過，消除兩平台 smoke
#       覆蓋不對稱）
#   [9] tools\install_windows_nightly.ps1 -WhatIf 預覽（R20 全面掃描補齊——R19 新增
#       此安裝器後從未被任何 smoke 涵蓋，鏡射 macos_smoke_local.sh [6/7] 對
#       install_mac_nightly.sh --render-only 的精神；-WhatIf 不需 elevation、不真的
#       動 Task Scheduler，可安全對本 repo 直跑）
#
# 限制（如實揭露）：
#   - fake repo 以 git clone 自本 repo HEAD 建立 → 未 commit 的變更不在驗證範圍
#     （worktree/clone 隔離盲區：驗證前先 commit）。
#   - 無法（或不宜）本地化的 windows-compat-ci step 不在本腳本範圍：
#     bootstrap.ps1／dev_start.ps1 實跑、integration_gate.ps1 -SkipFull、ci-gate.ps1、
#     tools/tests pytest、「根層 dispatcher hooks 真實 git commit 觸發」step（需 bash
#     載體＋probe commit）、install_post_commit.ps1 中文 clone 的逐字編碼斷言
#     （本檔 [6] 以安裝往返 + .git/config 直讀做精神抽驗，未逐字鏡射該 step）。
#   - [6] 的編碼斷言直讀 .git/config 位元組（UTF-8），不依賴主控台解碼；若在傳統
#     cp950 主控台下 FAIL，反映的是該環境下安裝腳本對非 ASCII 路徑的真實缺陷，
#     而非本載具誤報。
#   - 🔴 載具要求：請以「原生 PowerShell」執行（PowerShell 視窗／schtasks／
#     Windows Terminal）。經 Git Bash 間接呼叫 powershell.exe 時，msys→Win32
#     引數/主控台編碼轉換會弄壞 [6] 中文路徑情境（R10 實測：Git Bash 載具
#     PASS=7 假紅、原生 PowerShell PASS=8 全綠）——載具問題非生產缺陷。
#     **R59 起本要求已機械強制**（DEF-101-511）：偵測到 MSYS 衍生環境即 exit 1 拒跑。
#     WHY 要從「只寫在註解」升為「腳本自己擋」——本要求自 R10 起就寫在這裡，R59 的
#     主控仍然照樣用 Git Bash 跑並收到 PASS=11 FAIL=2 的假紅（原生重跑 PASS=12
#     FAIL=0）。純文件約束對「工具只有 Bash 載具可用」的呼叫者沒有攔阻力，而假紅與
#     漏測同等有害：它會讓人去追一個不存在的生產缺陷，或反過來讓人習慣性忽略這支
#     腳本的紅燈。刻意不做「跳過 [6] 並降低 MinPass」的降級路徑——那會產生一支
#     「少驗一項卻仍回報成功」的閘門，正是 R59 同輪在 ci-gate.ps1 fallback 上修掉的
#     反面示範（DEF-101-512）。
#     偵測用 `$env:MSYSTEM`（MSYS2／Git Bash 專有；R59 實測：Git Bash 載具下為
#     `MINGW64`、`[Console]::OutputEncoding=big5`，原生 PowerShell 下 MSYSTEM 為空、
#     編碼為 utf-8）。**刻意不用「非 ASCII 引數 round-trip 能力探針」**——R59 實測該
#     探針在兩種載具下都回 `equal=True`（Git Bash 下看到的亂碼只是終端顯示層，引數
#     本身完好），零鑑別力；真正壞掉的環節在 [6] 的 `git clone` 到含中文路徑時的
#     msys 路徑轉換，而那條路徑無法用一行探針忠實模擬，故改用身分訊號。
#
# ─────────────────────────────────────────────────────────────────────────────
# 🔴 退出判準（R74 新增；此前全庫查不到任何一條，這是它至今無法結束的直接原因）
# ─────────────────────────────────────────────────────────────────────────────
# 先分清兩個不同的東西——之前沒分清，所以「這個測試能不能結束」根本問不出答案：
#
#   (甲) **本腳本**（tools\windows_smoke_local.ps1）＝Windows 側對雲端
#        windows-compat-ci 的本地鏡像。**永久保留、無退出判準。**
#        理由：它的價值是「push 前／離線時能在 88 秒內知道有沒有壞」，這個價值與雲端
#        CI 活不活著無關。雲端 CI 再健康，也不會在你 push 之前告訴你答案。
#
#   (乙) **每日排程任務 AutoClaude_WindowsSmoke**＝R60 為「雲端 CI 帳務停擺
#        （DEF-101-081）期間 Windows 側零執行級訊號」而建的**補償控制**。
#        補償控制的存在理由是「主通道死了」，所以它**有**退出判準：主通道復活即退場。
#
# ⇒ 下面這條判準只管 (乙)，不管 (甲)。
#
# 【(乙) 的退出判準｜可機械查】三條**全部**成立才可移除該排程任務：
#   E1. 雲端主通道活著：windows-compat-ci 近 30 天內有 ≥ 20 個 run，且其中零筆
#       conclusion 屬 billing/startup_failure 類（＝帳務或基礎設施停擺已結束）。
#           gh run list --workflow windows-compat-ci.yml --limit 40 \
#             --json createdAt,conclusion,status
#   E2. 本腳本每一項都有雲端對應 step：由 tools/tests/test_smoke_ci_sync.py 的
#       步驟語意鎖判定（該鎖已存在且為綠＝零 smoke-only 項目）。
#   E3. 移除後 Windows 側仍有每日執行級心跳。**量測對象只有 AutoClaude_Nightly 這一支**：
#       它存在，且它自己那 7 項設定零漂移。可機械查（兩步都不看 smoke 任務在不在）：
#           Get-ScheduledTask -TaskName AutoClaude_Nightly -ErrorAction SilentlyContinue
#           python tools/check_scheduled_task_drift.py --json
#             ⇒ 讀 .tasks.AutoClaude_Nightly.present 為 true 且 .tasks.AutoClaude_Nightly.drifts 為空
#       刻意讀**逐任務**欄位而不是整支工具的 rc／status：後者把 smoke 任務一起算進去。
#
# 🔴 E3 的一般化規則（R75 頭號教訓，在它第三次同形態復發後就地寫下）：
#   **判準的量測對象，不得隨「被它所判的動作」而改變。**
#   E3 原文寫的是「移除後 tools/check_scheduled_task_drift.py 回 rc=0」，而該工具的期望值
#   SSOT（tools/scheduled_task_expectations.json）**同時列了兩支任務** ⇒ 一旦執行 E3 自己
#   授權的動作（移除 AutoClaude_WindowsSmoke），該工具必然回 status=task_missing／rc=1。
#   判準因此在結構上不可滿足：這支排程永遠退不了場，而且沒有人看得出原因——它看起來只是
#   「條件還沒到」。R75 已為同一形態付出代價（雲端錨判準拿 origin/main 當比較對象，於是
#   結構上每次 push 必紅、main 三支全紅）。寫任何退場／解鎖判準前先問一句：
#   **「執行我授權的那個動作之後，我自己還量得到綠嗎？」**
#   本條的機械物：tools/tests/test_install_windows_nightly.py::
#   TestWindowsSmokeTaskHasWrittenExitCriteria::test_e3_measures_only_what_survives_its_own_action
#
# 🔴 為何 E1 不是「smoke 連續 N 天零發現就可以撤」（本輪實測反證）：
#   R74 同輪雲端 windows-compat-ci 抓到一筆**本機十道閘門全綠**的 P0（hook 的中文
#   指引在非 CJK codepage 被 escape）。也就是說「零發現」不代表「沒有東西可發現」，
#   只代表這一層看不到那一類缺陷。用「零發現」當退場依據，會在通道還有價值時把它撤掉。
#   反過來說，那筆缺陷是**雲端** runner 抓的、不是本機 smoke——所以它也不支持
#   「smoke 排程是唯一發現通道」這個 R60 立案前提。**兩個方向都不成立，這正是為什麼
#   判準要綁在「主通道活性」（E1）而不是綁在「發現數」上。**
#
# 🔴 本節刻意**不再快照三條判準的顏色**（R76 訂正）。原文把 2026-08-04 當天量到的三個
# 顏色連同 smoke 任務的逐項漂移值寫成常數；2026-08-05 掌舵者提權重跑安裝器後，那三句
# 全部與磁碟相反，而沒有任何東西會因為它們過期而說話。**這裡刻意不逐字重述那三句**
# ——訂正文若把假話原樣抄一遍，讀者只會記得那三個數字（R73 已為此付出過代價）。
# 判準的顏色是會漂移的量測值，一律現查（同根 CLAUDE.md「工作清單是會漂移的量測值」）：
#     gh run list --workflow windows-compat-ci.yml --limit 40 --json createdAt,conclusion,status
#     python -m unittest discover -s tools/tests -p test_smoke_ci_sync.py
#     python tools/check_scheduled_task_drift.py --json
# 只留**不會過期**的處置規則：三條全成立才可移除該排程任務；任一條未取證就不算成立
# （「沒去查」不等於「已通過」）。移除本身是掌舵者的決定，本腳本不自動執行。
#
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File tools\windows_smoke_local.ps1
# Exit：0＝全部 PASS；1＝任一 FAIL（結尾彙總）或前置守門失敗。

# 控制流全靠顯式 rc / 狀態檢查（鏡射 .sh 版 set -u 精神），不用例外中斷：
# 刻意不設 $ErrorActionPreference = 'Stop'——受測腳本自帶 exit 慣例，用
# $LASTEXITCODE 斷言比例外傳播可預期（見 windows-compat-ci.yml 同款手法註解）。

$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))

# ── 取證層（DEF-101-761）：本腳本原本全檔只 Write-Host，schtasks 起的 console
# 輸出直接進虛空 ⇒ 排程紅燈**事後完全不可考**。2026-08-01 與 08-03 兩次
# LastTaskResult=1 的真因都因此永久佚失，而同一支腳本手動跑是 rc=0
# （PASS=12 FAIL=0 實測）——「只在排程載具下紅」正是最需要取證的一類，卻剛好沒紀錄。
#
# 落點形狀對齊 nightly（AutoClaude/logs/ + `_latest` + 14 天輪替），差別在**歸檔時機**：
# 本腳本有 3 個前置守門 exit 點 + 2 個結尾 exit 點，PowerShell 的 `exit` 不保證跑
# finally，逐點加收尾容易漏。故改為「**下一次啟動時**把上一輪的 latest 歸檔成 dated」
# ——不需要任何收尾 hook，且行程被強制中止（例如 ExecutionTimeLimit 到期）時，
# 上一輪的內容依然會在下一輪被完整保留下來。
# transcript 起在三道守門**之前**，故連「守門就 exit」也有紀錄。
$LogDir = Join-Path $RepoRoot 'AutoClaude/logs'
$LatestLog = Join-Path $LogDir 'windows_smoke_latest.log'
try {
  if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
  }
  # 上一輪的 latest 先歸檔（以它自己的寫入時刻命名，不是現在時刻）
  if (Test-Path -LiteralPath $LatestLog) {
    $prev = Get-Item -LiteralPath $LatestLog
    $archived = Join-Path $LogDir ("windows_smoke_{0}.log" -f $prev.LastWriteTime.ToString('yyyy-MM-dd_HHmmss'))
    if (-not (Test-Path -LiteralPath $archived)) {
      Move-Item -LiteralPath $LatestLog -Destination $archived -Force
    }
  }
  Get-ChildItem -LiteralPath $LogDir -Filter 'windows_smoke_*.log' -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne 'windows_smoke_latest.log' -and $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
    Remove-Item -Force -ErrorAction SilentlyContinue
  Start-Transcript -LiteralPath $LatestLog -Force | Out-Null
  # 排程載具診斷欄——手動跑全綠而排程跑紅時，差異幾乎都落在這幾項。
  Write-Host "[smoke-env] cwd=$($PWD.Path)"
  Write-Host "[smoke-env] whoami=$env:USERNAME interactive=$([Environment]::UserInteractive) msys=$($env:MSYSTEM)"
  Write-Host "[smoke-env] codepage=$([Console]::OutputEncoding.CodePage) psver=$($PSVersionTable.PSVersion)"
  Write-Host "[smoke-env] python=$((Get-Command python -ErrorAction SilentlyContinue).Source)"
  Write-Host "[smoke-env] git=$((Get-Command git -ErrorAction SilentlyContinue).Source)"
} catch {
  # 取證層失敗**不得**阻斷驗證本身（否則等於用取證換掉被取證的東西）。
  Write-Host "[smoke-env] ⚠️ 取證層啟動失敗，本輪無 log 落點：$($_.Exception.Message)" -ForegroundColor Yellow
}

# ── 前置守門：載具必須是原生 PowerShell（DEF-101-511，WHY 見檔頭「載具要求」）─────
if ($env:MSYSTEM) {
  Write-Host "❌ 偵測到 MSYS 衍生環境（MSYSTEM=$env:MSYSTEM）— 本腳本必須以原生 PowerShell 執行，拒絕在此載具下跑。" -ForegroundColor Red
  Write-Host '   原因：經 Git Bash 間接呼叫時，msys→Win32 路徑/編碼轉換會弄壞 [6] 非 ASCII 路徑情境，' -ForegroundColor Red
  Write-Host '         產生與生產無關的假紅（R10／R59 兩度實測；詳見本檔檔頭「載具要求」段）。' -ForegroundColor Red
  Write-Host '   請改用：powershell -NoProfile -ExecutionPolicy Bypass -File tools\windows_smoke_local.ps1' -ForegroundColor Yellow
  Write-Host '         （PowerShell 視窗／Windows Terminal／schtasks／Claude Code 的 PowerShell 工具皆可）' -ForegroundColor Yellow
  exit 1
}

# ── 前置守門：引擎必須是 Windows PowerShell 5.1（R73／DEF-101-776）───────────────
# 🔴 為何 R73 才補：在 pwsh 7 裝上這台機器之前，本守門**不可能**被觸發——`powershell`
# 就是 5.1，沒有第二個引擎可選。2026-08-04 本機裝上 PowerShell 7.6.4 後，這條路第一次
# 變得可達，而且失效方向是**靜默且偏危險側**：
#   · [1/9] 的 `Parser::ParseFile` 用的是**執行本腳本那個引擎**的文法。
#   · 5.1 與 7 的 `Encoding::Default` 不同（本機 zh-TW：big5 vs utf-8），於是「UTF-8
#     無 BOM ＋ 中文註解」的 .ps1 在 7 解析全綠、在 5.1 被 Big5 誤讀到吃掉引號而 parse 死。
#     R73 實測全庫 137 支 .ps1：5.1 → OK=108/ERR=29，7.6.4 → OK=137/ERR=0。
#   · 生產（schtasks 兩支 job 的 Action）跑的是 `powershell.exe`＝5.1。用 7 跑本腳本
#     等於用寬鬆文法去驗一個受 5.1 約束的對象 ⇒ 綠燈沒有鑑別力，且不會有任何訊號。
# 這正是 CI 早已釘住的同一件事：`.github/workflows/windows-compat-ci.yml` 的
# `windows-smoke` job 帶 `if ($PSVersionTable.PSVersion.Major -ne 5) { throw "ENGINE-MISMATCH..." }`。
# 本機鏡射是同一個閘門，先前卻只 `Write-Host` 印版本、不擋——CI 有牙、本機沒有。
# 一致性優先於方便：本守門刻意不提供 `-Force` 之類的旁路（旁路一旦存在就會被習慣性使用，
# 而它豁免掉的正是這支腳本唯一的鑑別力來源）。
if ($PSVersionTable.PSVersion.Major -ne 5) {
  Write-Host "❌ ENGINE-MISMATCH：本腳本必須以 Windows PowerShell 5.1 執行，實測 $($PSVersionTable.PSVersion)。" -ForegroundColor Red
  Write-Host '   原因：[1/9] 的語法解析用的是執行本腳本那個引擎的文法，而生產（schtasks）跑的是 5.1；' -ForegroundColor Red
  Write-Host '         用 pwsh 7 跑會讓「5.1 解析不過、7 解析得過」的寫法全部逸出（實測 29 支檔案的差異）。' -ForegroundColor Red
  Write-Host '   請改用：powershell -NoProfile -ExecutionPolicy Bypass -File tools\windows_smoke_local.ps1' -ForegroundColor Yellow
  Write-Host '         （注意是 powershell.exe，不是 pwsh.exe；兩支同時存在時必須指名前者）' -ForegroundColor Yellow
  exit 1
}

# ── 前置守門：git / python 缺席 fail-fast（比照 .sh 版與共用層訊息）─────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host '❌ 找不到 git — 請先安裝 Git for Windows（見 ONBOARDING.md §2）' -ForegroundColor Red
  exit 1
}
# WindowsApps 空殼排除比照 tools/bootstrap.ps1／tools/dev_start.ps1 既有 SSOT（R44 收斂）
. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"
if (-not (Test-IsRealPython -CandidateName 'python')) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

$script:Pass = 0
$script:Fail = 0
$script:FailList = @()

# 讀「原生指令輸出的路徑」專用（DEF-101-762）：呼叫期間把主控台輸出編碼釘成 UTF-8。
# WHY：PowerShell 解碼原生指令 stdout 用的是 `[Console]::OutputEncoding`，而 git／
# 本 repo 的 python CLI 都以 UTF-8 輸出路徑。在 **cp950**（繁中 Windows 的 OEM 預設，
# 也就是 schtasks 排程環境）下，含非 ASCII 的路徑會被解成 mojibake——本載具據以
# Join-Path 出 .git/config 位置就會指到不存在的檔案，把生產缺陷誤報成本載具的紅燈。
#
# 🔴 刻意**只**包本載具自己的 git 讀取，絕不在腳本頂端整支釘 UTF-8：受測腳本是以
# `& $installer`／`& $ipc` **同行程**呼叫的，會直接繼承主控台編碼。整支釘 UTF-8 等於
# 讓 [5][6] 在任何載具下都拿到 UTF-8 主控台，那個「只在 cp950 顯形」的生產缺陷
# （DEF-101-762 本體）就再也重現不出來——那是把 tripwire 拆掉，不是修好它。
function Read-NativeUtf8 {
  param([Parameter(Mandatory = $true)][scriptblock]$Body)
  $prevEnc = $null
  try {
    if ([Console]::OutputEncoding.CodePage -ne 65001) {
      $prevEnc = [Console]::OutputEncoding
      [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    }
  } catch {
    $prevEnc = $null   # 無主控台可設；維持既有行為，下游斷言仍會 fail-loud
  }
  try { & $Body } finally { if ($null -ne $prevEnc) { [Console]::OutputEncoding = $prevEnc } }
}

function Pass-Item([string]$Msg) {
  $script:Pass += 1
  Write-Host "  ✅ PASS: ${Msg}" -ForegroundColor Green
}

function Fail-Item([string]$Msg) {
  $script:Fail += 1
  $script:FailList += $Msg
  Write-Host "  ❌ FAIL: ${Msg}" -ForegroundColor Red
}

# 安裝／解除往返共用（[2][4a][6] 同款斷言；一次呼叫恰記 1 個 PASS 點或至少 1 個 FAIL）。
# 所有 git config 讀寫都在 Push-Location 成功進入「受測 repo」後才執行——Push 失敗
# 立即 FAIL 返回，絕不讓後續 git config 落在呼叫端 CWD（可能是真 repo）上。
function Test-InstallRoundtrip {
  param(
    [Parameter(Mandatory = $true)][string]$TargetRepo,
    [Parameter(Mandatory = $true)][string]$InstallerRel,
    [switch]$UninstallSwitch,   # $true=用 -Uninstall 解除；否則手動 git config --unset
    [switch]$CheckSeparators,   # 斷言 core.hooksPath 不得混用 / 與 \（鏡射 CI install-hooks.ps1 step）
    [string]$NonAsciiProbe = '',# 非空時直讀 .git/config（UTF-8）斷言含此片段（[6] 編碼防護）
    [Parameter(Mandatory = $true)][string]$Label
  )
  $installer = Join-Path $TargetRepo $InstallerRel
  if (-not (Test-Path -LiteralPath $installer)) {
    Fail-Item "${Label}：找不到安裝腳本 ${installer}"
    return
  }
  try {
    Push-Location -LiteralPath $TargetRepo -ErrorAction Stop
  } catch {
    Fail-Item "${Label}：無法進入受測 repo ${TargetRepo}（非假 PASS）"
    return
  }
  try {
    & $installer
    $rcInstall = $LASTEXITCODE
    $hp = Read-NativeUtf8 { git config --get core.hooksPath }
    if ($rcInstall -ne 0) {
      Fail-Item "${Label}：安裝執行失敗（rc=${rcInstall}）"
      return
    }
    if ([string]::IsNullOrEmpty($hp)) {
      Fail-Item "${Label}：安裝後 core.hooksPath 未設定"
      return
    }
    if ($CheckSeparators -and ($hp -match '/') -and ($hp -match '\\')) {
      Fail-Item "${Label}：core.hooksPath 含混合分隔符：${hp}"
      return
    }
    if ($NonAsciiProbe -ne '') {
      # 直讀共享 config 的 UTF-8 位元組，不經主控台解碼——編碼損毀（cp950
      # 誤讀成 mojibake / '?'）會在此現形（R9 修復主題）。用 --git-common-dir
      # 解析實際 config 位置（而非硬編 .git\config，DEF-101-235②）：一般
      # `git clone` 下 .git 是目錄，解析結果等同 .git；linked worktree
      # （`git worktree add`）下 .git 是內含 `gitdir: <path>` 一行文字的檔案，
      # core.hooksPath 寫入的是共享 config（主 repo 的 .git/config）——
      # --git-common-dir 兩種情境皆正確解析、不受此陷阱影響（同本檔 [5]
      # 既有用法，需 git >= 2.31）。
      # R17 四方一審 SD 發現：git < 2.31 不認得 --path-format 時，rev-parse 不會
      # 以非零 rc 報錯，而是把未知旗標原樣 echo 成額外一行輸出（`rev-parse` 既有
      # 文件行為），令 $LASTEXITCODE/IsNullOrEmpty 兩道守衛皆偵測不到、把夾雜
      # 旗標字串的多行輸出誤當合法路徑餵進 Join-Path。強制用 @() 收成陣列並斷言
      # 恰好一行，才是能真正攔住此情境的判準。
      $commonDirLines = @(Read-NativeUtf8 { git -C $TargetRepo rev-parse --path-format=absolute --git-common-dir 2>$null })
      if ($LASTEXITCODE -ne 0 -or $commonDirLines.Count -ne 1 -or [string]::IsNullOrEmpty($commonDirLines[0])) {
        Fail-Item "${Label}：git rev-parse --git-common-dir 失敗（需 git >= 2.31）——無法定位共享 config"
        return
      }
      $cfgPath = Join-Path $commonDirLines[0].Trim() 'config'
      $cfgText = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8)
      if ($cfgText -notmatch [regex]::Escape($NonAsciiProbe)) {
        Fail-Item "${Label}：.git/config 內 core.hooksPath 遺失非 ASCII 片段「${NonAsciiProbe}」（編碼損毀，R9 cp950 類回歸）"
        return
      }
    }
    if ($UninstallSwitch) {
      & $installer -Uninstall
      $rcUn = $LASTEXITCODE
      if ($rcUn -ne 0) {
        Fail-Item "${Label}：-Uninstall 執行失敗（rc=${rcUn}）"
        return
      }
    } else {
      git config --unset core.hooksPath
      if ($LASTEXITCODE -ne 0) {
        Fail-Item "${Label}：git config --unset core.hooksPath 失敗"
        return
      }
    }
    $hp2 = Read-NativeUtf8 { git config --get core.hooksPath }
    if (-not [string]::IsNullOrEmpty($hp2)) {
      Fail-Item "${Label}：解除後 core.hooksPath 仍殘留：${hp2}"
      return
    }
    Pass-Item "${Label} 安裝／解除往返"
  } finally {
    Pop-Location
  }
}

# linked worktree 拒絕共用（[3][4b]）——DEF-101-135 假 PASS 防護：
# worktree add 顯式檢查（失敗即 FAIL，不得默默把「沒跑到」當拒絕成功）；
# Push-Location 失敗或安裝腳本不存在時 rc 停在哨兵 9（受測腳本根本沒執行 ≠ 拒絕成功）。
function Test-WorktreeRejectNestedCommand {
  <#
  .SYNOPSIS
  linked worktree 拒絕守門的「非典型呼叫鏈」回歸鎖（DEF-101-263④ 訂正 / R27）：
  安裝器不是以典型 `powershell -File installer.ps1` 頂層執行，而是被包在
  `powershell -Command "& 'installer.ps1'"` 這種寫法之下（例如某些自動化/CI
  包裝器慣用 -Command 而非 -File 呼叫子腳本）。此寫法下最外層呼叫棧 frame 沒有
  真實 .ps1 檔案（ScriptName 為空），R23~R26 的偵測寫法
  `[bool]((Get-PSCallStack)[-1].ScriptName)` 只看最外層，會誤判為「使用者互動式
  探索」而把 Assert-NotLinkedWorktree 的失敗分支從 exit 1 降級為 return——linked
  worktree 防呆因而在此類呼叫情境下靜默失效（R27 手動重現：改用此呼叫寫法後
  [3][4] 由預期 rc=1 變成 rc=0 或哨兵 rc=9）。修復後改看呼叫棧 [1]（dot-source
  點的直接呼叫者，非本檔自身/非最外層），本函式即模擬此呼叫寫法、確認修復後
  仍正確 exit 1，避免此偵測邏輯未來再度悄悄退化為只看最外層。
  #>
  param(
    [Parameter(Mandatory = $true)][string]$BaseRepo,
    [Parameter(Mandatory = $true)][string]$InstallerRel,
    [Parameter(Mandatory = $true)][string]$WorktreeName,
    [Parameter(Mandatory = $true)][string]$Label
  )
  $wt = Join-Path $script:Work $WorktreeName
  git -C $BaseRepo worktree add --quiet --detach $wt HEAD
  if ($LASTEXITCODE -ne 0) {
    Fail-Item "${Label}：worktree add 失敗——非典型呼叫鏈拒絕情境未能執行（非假 PASS）"
    return
  }
  $installer = Join-Path $wt $InstallerRel
  # 刻意用 -Command 包一層 `& '<installer>'`（而非 -File 直接指向 installer），
  # 重現「最外層呼叫棧 frame 非真實 .ps1 檔案」的非典型呼叫鏈情境。子行程須先
  # Set-Location 進 worktree 目錄——linked worktree 偵測靠當前目錄的
  # git-dir/git-common-dir 判斷，子行程繼承呼叫端 cwd（本 repo 根，非 worktree），
  # 不切換目錄會讓偵測邏輯連「這是 worktree」都判斷不到，與 [3][4] 既有
  # Push-Location 進 worktree 再呼叫同一精神。
  & powershell -NoProfile -Command "Set-Location -LiteralPath '$wt'; & '$installer'" | Out-Null
  $rc = $LASTEXITCODE
  git -C $BaseRepo worktree remove --force $wt
  if ($rc -eq 1) {
    Pass-Item "${Label}（-Command 非典型呼叫鏈）linked worktree 拒絕（rc=1 as expected）"
  } else {
    Fail-Item "${Label}（-Command 非典型呼叫鏈）：於 linked worktree 應 exit 1，實際 rc=${rc}"
  }
}

function Test-WorktreeReject {
  param(
    [Parameter(Mandatory = $true)][string]$BaseRepo,
    [Parameter(Mandatory = $true)][string]$InstallerRel,
    [Parameter(Mandatory = $true)][string]$WorktreeName,
    [Parameter(Mandatory = $true)][string]$Label
  )
  $wt = Join-Path $script:Work $WorktreeName
  git -C $BaseRepo worktree add --quiet --detach $wt HEAD
  if ($LASTEXITCODE -ne 0) {
    Fail-Item "${Label}：worktree add 失敗——拒絕情境未能執行（非假 PASS）"
    return
  }
  $rc = 9  # 哨兵：維持 9 代表受測腳本根本沒被執行
  try {
    Push-Location -LiteralPath $wt -ErrorAction Stop
    try {
      $installer = Join-Path $wt $InstallerRel
      if (Test-Path -LiteralPath $installer) {
        & $installer
        $rc = $LASTEXITCODE
      }
    } finally {
      Pop-Location
    }
  } catch {
    # Push-Location 失敗 → rc 停在哨兵 9
  }
  git -C $BaseRepo worktree remove --force $wt
  if ($rc -eq 1) {
    Pass-Item "${Label} linked worktree 拒絕（rc=1 as expected）"
  } else {
    Fail-Item "${Label}：於 linked worktree 應 exit 1，實際 rc=${rc}（9=哨兵：腳本未被執行）"
  }
}

# ── OS temp 工作目錄（mktemp 式隨機名；fake repo 全程住這裡）────────────────────
$script:Work = Join-Path $env:TEMP ('windows_smoke_local.' + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $script:Work -ErrorAction SilentlyContinue | Out-Null
if (-not (Test-Path -LiteralPath $script:Work)) {
  Write-Host "❌ 無法建立 OS temp 工作目錄：${script:Work}" -ForegroundColor Red
  exit 1
}
$Work = $script:Work

Write-Host '===== windows_smoke_local（DEF-101-081 補償控制 / QA-10 DEF-101-139）====='
Write-Host "repo 根：${RepoRoot}"
Write-Host "PowerShell：$($PSVersionTable.PSVersion)（$($PSVersionTable.PSEdition)）"
Write-Host "git：$(git --version)"
Write-Host "python：$(python --version)"
Write-Host "OS temp 工作目錄：${Work}"
$dirty = git -C $RepoRoot status --porcelain
if ($dirty) {
  Write-Host '⚠ 本 repo 有未 commit 變更——[2]~[6] 驗證的是 HEAD（clone），未含這些變更' -ForegroundColor Yellow
}

try {
  # ── [1/9] PowerShell parse 檢查（四棵樹 active .ps1，唯讀）────────────────────
  # R56 修正（Architect round 3）：本步驟原僅掃根層 tools/（8 支），而 R56 同輪已把
  # macOS 對等品 tools/macos_smoke_local.sh [1/7] 由「根層 tools/」擴為與
  # root-infra-ci.yml 第 1 道同一份清單。該擴面的立論正是「平台待遇不對稱」，結果
  # 不對稱只是從 CI 層搬到本機層、方向恰好相反：CI 第 2 道掃四棵樹（21 支 active
  # .ps1），Windows 本機側卻只掃根層 8 支，13 支（含 install_git_hooks.ps1／
  # local_ci_gate.ps1 等 AutoClaude/AISDLC_SDD 側入口）在本機零語法訊號，只能燒 CI
  # 額度才發現 parse error。故擴為與 root-infra-ci.yml 第 2 道同四棵樹、皆 -Recurse。
  # 凍結版 AISDLC_SDD/AISDLC_SDD_v0.01~v0.(N-1) 依紀律不回改 → 排除；LATEST 一律
  # 委派 AISDLC_SDD/scripts/sdd_version.py SSOT 解析（DEF-101-133，禁自行實作版本
  # glob/regex），空值 Fail-Item 不靜默縮面（鏡射該 CI step 的 throw 語意）。
  # per-tree 檔數下限釘選（防單棵樹目錄搬家/樣式改壞後靜默縮面）＝2026-07-27 實測
  # 各樹支數，刻意刪減時同步下修（慣例對齊 tools/tests/test_bash32_compat.py）。
  Write-Host ''
  Write-Host '--- [1/9] Parser 解析檢查（active .ps1 四棵樹：tools/ + AutoClaude/tools/ + AISDLC_SDD/scripts/ + LATEST，皆遞迴；對本 repo 直跑）---'
  $sddRoot = Join-Path $RepoRoot 'AISDLC_SDD'
  $latestName = ''
  $resolver = Join-Path $sddRoot 'scripts\sdd_version.py'
  if (Test-Path -LiteralPath $resolver) {
    $latestName = (& python $resolver --sdd-root $sddRoot | Out-String).Trim()
  }
  $ps1Trees = @(
    @{ Rel = 'tools'; Floor = 8 },
    # R76：Floor 由 7 下修為 6（reschedule_g0_gatecheck.ps1 整支刪除，真孤兒——它要重排的
    # AutoClaude_SD09_G0_GateCheck 於 R71 已從本機移除）。姊妹站點＝test_ps51_compat._TREE_FLOORS。
    @{ Rel = 'AutoClaude\tools'; Floor = 6 },
    @{ Rel = 'AISDLC_SDD\scripts'; Floor = 2 }
  )
  if ($latestName) {
    Write-Host "    AISDLC_SDD LATEST 版：${latestName}（其餘凍結版排除）"
    $ps1Trees += @{ Rel = (Join-Path 'AISDLC_SDD' $latestName); Floor = 4 }
  } else {
    Fail-Item 'AISDLC_SDD LATEST 解析失敗（scripts/sdd_version.py 無輸出）——掃描邊界不得靜默縮小'
  }
  $ps1Files = @()
  $treeBad = 0
  foreach ($tree in $ps1Trees) {
    $treeFull = Join-Path $RepoRoot $tree.Rel
    $found = @(Get-ChildItem -Path $treeFull -Recurse -Filter *.ps1 -File -ErrorAction SilentlyContinue)
    Write-Host "    $($tree.Rel)：$($found.Count) 支（下限 $($tree.Floor)）"
    if ($found.Count -lt $tree.Floor) {
      Fail-Item "active .ps1 掃描面異常縮小：$($tree.Rel) 僅 $($found.Count) 支（現況應 >= $($tree.Floor)）——目錄搬家或 Get-ChildItem 樣式疑似被改壞"
      $treeBad += 1
    }
    $ps1Files += $found
  }
  $parseBad = 0
  foreach ($f in $ps1Files) {
    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
      foreach ($e in $parseErrors) {
        Write-Host "    $($f.FullName):$($e.Extent.StartLineNumber) $($e.Message)"
      }
      Fail-Item "Parser parse error：$($f.FullName)"
      $parseBad += 1
    }
  }
  if ($parseBad -eq 0 -and $treeBad -eq 0 -and $latestName) {
    Pass-Item "Parser 解析全數通過（$($ps1Files.Count) 檔／四棵樹）"
  }

  # ── 建立 fake repo（供 [2]~[6]；git clone HEAD → OS temp）─────────────────────
  Write-Host ''
  Write-Host '--- 建立 fake repo（git clone HEAD → OS temp）---'
  $Fake = Join-Path $Work 'repo'
  # -c core.longpaths=true：僅保護 git 自身內部的路徑處理（clone/checkout 等），
  # 不涵蓋本腳本後續 Test-Path／New-Item／[System.IO.File]::ReadAllText 等
  # .NET／PowerShell 5.1 原生 API 對同一批深路徑的操作——這些 API 在 PS 5.1 上
  # 若無系統級 LongPathsEnabled 登錄機碼 + app-manifest opt-in，不會自動獲得
  # 長路徑保護，MAX_PATH=260 風險依然存在（尤其隨 AISDLC_SDD_v0.NN 版本號
  # 增加路徑深度）；如需徹底解決需系統級開啟 LongPathsEnabled（鏡射 .sh 版）。
  git clone --quiet -c core.longpaths=true $RepoRoot $Fake
  $FakeReady = $false
  if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path $Fake '.git'))) {
    Pass-Item "fake repo 建立完成：${Fake}"
    $FakeReady = $true
  } else {
    Fail-Item 'git clone 建立 fake repo 失敗——[2]~[6] 無法執行'
  }

  if ($FakeReady) {
    # ── [2/9] install_git_hooks.ps1 安裝／解除往返（fake repo）───────────────────
    Write-Host ''
    Write-Host '--- [2/9] AutoClaude/tools/install_git_hooks.ps1 安裝／解除往返（fake repo）---'
    Test-InstallRoundtrip -TargetRepo $Fake -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
      -UninstallSwitch -Label '[2] install_git_hooks.ps1'

    # ── [3/9] install_git_hooks.ps1 linked worktree 拒絕 ─────────────────────────
    Write-Host ''
    Write-Host '--- [3/9] install_git_hooks.ps1 於 linked worktree 應拒絕（fail-loud）---'
    Test-WorktreeReject -BaseRepo $Fake -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
      -WorktreeName 'wt-install-git-hooks-reject' -Label '[3] install_git_hooks.ps1'

    # ── [4/9] install-hooks.ps1 安裝往返 + linked worktree 拒絕 ──────────────────
    Write-Host ''
    Write-Host '--- [4/9] AISDLC_SDD/scripts/install-hooks.ps1 往返 + worktree 拒絕（fake repo）---'
    Test-InstallRoundtrip -TargetRepo $Fake -InstallerRel 'AISDLC_SDD\scripts\install-hooks.ps1' `
      -CheckSeparators -Label '[4] install-hooks.ps1'
    Test-WorktreeReject -BaseRepo $Fake -InstallerRel 'AISDLC_SDD\scripts\install-hooks.ps1' `
      -WorktreeName 'wt-install-hooks-reject' -Label '[4] install-hooks.ps1'

    # ── [5/9] LATEST install_post_commit.ps1 worktree 實跑 + 移除後路徑斷言 ───────
    Write-Host ''
    Write-Host '--- [5/9] install_post_commit.ps1 worktree 實跑 + 移除後路徑斷言（fake repo）---'
    # LATEST 解析一律走 SSOT resolver（DEF-101-133）；resolver 檔取自真 repo、
    # --sdd-root 指向 fake repo（resolver 屬驗證工具、不必來自被測樹）。
    $resolver = Join-Path $RepoRoot 'AISDLC_SDD\scripts\sdd_version.py'
    $latestName = & python $resolver --sdd-root (Join-Path $Fake 'AISDLC_SDD') | Select-Object -Last 1
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($latestName)) {
      Fail-Item "[5] LATEST 解析失敗（sdd_version.py rc=${LASTEXITCODE}）——install_post_commit.ps1 驗證未能執行"
    } else {
      $latestName = ([string]$latestName).Trim()
      Write-Host "AISDLC_SDD LATEST 版：${latestName}（SSOT resolver）"
      $wt = Join-Path $Work 'wt-install-post-commit'
      git -C $Fake worktree add --quiet --detach $wt HEAD
      if ($LASTEXITCODE -ne 0) {
        Fail-Item '[5] worktree add 失敗——install_post_commit.ps1 實跑未能執行（非假 PASS）'
      } else {
        $rc = 9  # 哨兵：同 Test-WorktreeReject（腳本未被執行 ≠ 成功）
        try {
          Push-Location -LiteralPath $wt -ErrorAction Stop
          try {
            $installer = Join-Path $wt ('AISDLC_SDD\' + $latestName + '\tools\install_hooks\install_post_commit.ps1')
            if (Test-Path -LiteralPath $installer) {
              & $installer
              $rc = $LASTEXITCODE
            }
          } finally {
            Pop-Location
          }
        } catch {
          # Push-Location 失敗 → rc 停在哨兵 9
        }
        $step5Ok = $true
        # R17 四方一審 SD 發現（與本檔 [4] Test-InstallRoundtrip 同構修復）：git < 2.31
        # 不認得 --path-format 時不會以非零 rc 報錯，而是把未知旗標原樣 echo 成額外
        # 一行輸出，令 $LASTEXITCODE/IsNullOrEmpty 兩道守衛皆偵測不到。強制用 @()
        # 收成陣列並斷言恰好一行。
        $commonDirLines = @(Read-NativeUtf8 { git -C $Fake rev-parse --path-format=absolute --git-common-dir 2>$null })
        if ($LASTEXITCODE -ne 0 -or $commonDirLines.Count -ne 1 -or [string]::IsNullOrEmpty($commonDirLines[0])) {
          Fail-Item '[5] git rev-parse --git-common-dir 失敗（需 git >= 2.31）'
          $step5Ok = $false
        } else {
          $target = Join-Path $commonDirLines[0].Trim() 'hooks\post-commit'
          if ($rc -ne 0) {
            Fail-Item "[5] install_post_commit.ps1 於 worktree 執行失敗（rc=${rc}；9=哨兵：腳本未被執行）"
            $step5Ok = $false
          } elseif (-not (Test-Path -LiteralPath $target)) {
            Fail-Item "[5] post-commit 未正確安裝於 ${target}"
            $step5Ok = $false
          } else {
            $content = [System.IO.File]::ReadAllText($target, [System.Text.Encoding]::UTF8)
            if ($content -notmatch 'post_commit_drift\.py') {
              Fail-Item '[5] post-commit 缺 drift hook 路徑'
              $step5Ok = $false
            } elseif ($content -notmatch 'closure_evidence_verify\.py') {
              Fail-Item '[5] post-commit 缺 closure hook 路徑'
              $step5Ok = $false
            }
          }
        }
        git -C $Fake worktree remove --force $wt
        # 2026-07-16 P1 回歸鎖（鏡射 windows-compat-ci 對應 step）：worktree 移除「後」
        # 重讀共享 hook，內嵌 .py 路徑必須仍存在於磁碟（--show-toplevel 舊 bug 會在此現形）。
        if ($step5Ok) {
          $content2 = [System.IO.File]::ReadAllText($target, [System.Text.Encoding]::UTF8)
          $driftPath = $null
          $closurePath = $null
          # R11：hook 內容改為 `"$PY" "<路徑>"`（python fallback，DEF-101 家族），擷取
          # 改抓「引號包住的 .py 路徑」本身、不再錨定 `python ` 前綴（新舊格式皆匹配）。
          if ($content2 -match '"([^"]*post_commit_drift\.py)"') { $driftPath = $Matches[1] }
          if ($content2 -match '"([^"]*closure_evidence_verify\.py)"') { $closurePath = $Matches[1] }
          if ([string]::IsNullOrEmpty($driftPath) -or [string]::IsNullOrEmpty($closurePath)) {
            Fail-Item '[5] worktree 移除後無法從 hook 擷取 drift/closure 路徑'
          } elseif (-not (Test-Path -LiteralPath $driftPath) -or -not (Test-Path -LiteralPath $closurePath)) {
            Fail-Item "[5] worktree 移除後 hook 內嵌路徑已不存在於磁碟（P1 回歸重現）：drift=${driftPath} closure=${closurePath}"
          } else {
            Pass-Item '[5] install_post_commit.ps1 worktree 實跑 + 移除後路徑仍有效（drift/closure）'
          }
        }
      }
    }

    # ── [6/9] 非 ASCII 路徑防護抽驗（中文目錄 clone + 安裝往返）───────────────────
    Write-Host ''
    Write-Host '--- [6/9] 非 ASCII 路徑防護抽驗（「煙霧測試」目錄 clone + install_git_hooks.ps1 往返）---'
    $cnParent = Join-Path $Work '煙霧測試'
    New-Item -ItemType Directory -Path $cnParent -ErrorAction SilentlyContinue | Out-Null
    $cnRepo = Join-Path $cnParent 'repo'
    git clone --quiet -c core.longpaths=true $Fake $cnRepo
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $cnRepo '.git'))) {
      Fail-Item '[6] 中文路徑 clone 失敗——非 ASCII 防護抽驗未能執行（非假 PASS）'
    } else {
      Test-InstallRoundtrip -TargetRepo $cnRepo -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
        -UninstallSwitch -NonAsciiProbe '煙霧測試' -Label '[6] 中文路徑（煙霧測試）install_git_hooks.ps1'
    }

    # ── [7/9] linked worktree 拒絕於非典型呼叫鏈（-Command 包裝）下仍生效 ────────
    Write-Host ''
    Write-Host '--- [7/9] install_git_hooks.ps1 於「-Command 非典型呼叫鏈」linked worktree 仍應拒絕 ---'
    Test-WorktreeRejectNestedCommand -BaseRepo $Fake -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
      -WorktreeName 'wt-install-git-hooks-reject-nested-command' -Label '[7] install_git_hooks.ps1'
  }

  # ── [8/9] check_ntfs_paths.py + check_script_parity.py（本 repo，唯讀）───────
  # R18 全面掃描補齊：這兩支純 Python、平台無關的檢查先前僅由 macos_smoke_local.sh
  # [5/7] 覆蓋，Windows 本機 smoke 從未在 Windows 環境下實際跑過（CI push gate
  # 另有覆蓋，但不是「Windows 本機 smoke」）。兩腳本皆以 `Path(__file__).resolve()`
  # 自行定位 repo 根，不依賴呼叫端 cwd，故不需 fake repo / Push-Location。
  Write-Host ''
  Write-Host '--- [8/9] check_ntfs_paths.py + check_script_parity.py（本 repo，唯讀）---'
  & python (Join-Path $RepoRoot 'tools\check_ntfs_paths.py')
  if ($LASTEXITCODE -eq 0) {
    Pass-Item 'tools\check_ntfs_paths.py'
  } else {
    Fail-Item "tools\check_ntfs_paths.py（rc=$LASTEXITCODE）"
  }
  & python (Join-Path $RepoRoot 'tools\check_script_parity.py')
  if ($LASTEXITCODE -eq 0) {
    Pass-Item 'tools\check_script_parity.py'
  } else {
    Fail-Item "tools\check_script_parity.py（rc=$LASTEXITCODE）"
  }

  # ── [9/9] install_windows_nightly.ps1 -WhatIf 預覽（本 repo，唯讀）───────────
  # R20 全面掃描補齊：R19 新增此安裝器後從未被任何 smoke 涵蓋（鏡射
  # macos_smoke_local.sh [6/7] 對 install_mac_nightly.sh --render-only 的精神）。
  # -WhatIf 不需 elevation、不真的呼叫 Register-ScheduledTask，可對本 repo 直跑
  # （不需 fake repo：預覽模式不變更任何系統狀態）。
  # R20 四方一審 SA 建議（非阻斷，本輪落地）：只斷言 exit=0 只驗到「不 crash」，
  # 沒驗到「-WhatIf 真的印出將執行的動作」這層內容——改用獨立子行程呼叫（ShouldProcess
  # 的 WhatIf 預覽訊息走 host-only 輸出、同行程內 `& script` 呼叫無法用一般串流重導向
  # 捕捉；真機實測獨立子行程呼叫可正確捕捉）並斷言輸出內容含 Register-ScheduledTask。
  Write-Host ''
  Write-Host '--- [9/9] tools\install_windows_nightly.ps1 -WhatIf 預覽（本 repo，唯讀）---'
  $whatIfOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $RepoRoot 'tools\install_windows_nightly.ps1') -WhatIf 2>&1 | Out-String
  $whatIfRc = $LASTEXITCODE
  if ($whatIfRc -eq 0 -and $whatIfOutput -match 'Register-ScheduledTask') {
    Pass-Item 'tools\install_windows_nightly.ps1 -WhatIf 預覽'
  } else {
    Fail-Item "tools\install_windows_nightly.ps1 -WhatIf（rc=${whatIfRc}；輸出未含預期的 Register-ScheduledTask 內容）"
  }
} finally {
  # cleanup：離開 temp 再整棵刪除；絕不對真 repo 做 git config 變更（所有 git config
  # 讀寫都發生在 fake repo / 中文 clone 內，見各 helper 的 Push-Location 守門）。
  Set-Location -LiteralPath $env:TEMP
  if (Test-Path -LiteralPath $Work) {
    try {
      Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction Stop
    } catch {
      Write-Host "⚠ temp 工作目錄清理未完全：${Work}（$($_.Exception.Message)）" -ForegroundColor Yellow
    }
  }
}

# ── 彙總 ─────────────────────────────────────────────────────────────────────
# R10 二審 QA 觀察項：PASS 下限釘選（比照 run_root_unittests MIN_TESTS 精神）——
# 只斷言 FAIL==0 時，驗證段落被整段刪除仍 exit 0（靜默縮面）；PASS 低於下限即紅。
# 刻意刪減驗證項時同步下修本值（現況滿版 PASS=12——R18 新增 [8/9] check_ntfs_paths.py
# + check_script_parity.py 兩項計點；R20 新增 [9/9] install_windows_nightly.ps1 -WhatIf 一項計點；
# R27 新增 [7/9] linked worktree 拒絕於「-Command 非典型呼叫鏈」下仍生效一項計點，
# 修復 DEF-101-263④ 訂正——原判定「全庫零命中、純理論性」經本輪實測推翻，見該列訂正）。
$MinPass = 12
if ($script:Pass -lt $MinPass) {
  Fail-Item "PASS 總數 $($script:Pass) 低於下限 ${MinPass}——驗證段落疑似被刪減（靜默縮面）"
}
Write-Host ''
Write-Host "===== 彙總：PASS=$($script:Pass) FAIL=$($script:Fail) ====="
if ($script:Fail -gt 0) {
  Write-Host '失敗項目：' -ForegroundColor Red
  foreach ($item in $script:FailList) {
    Write-Host "  - ${item}" -ForegroundColor Red
  }
  exit 1
}
Write-Host '全部通過 ✅（Windows PowerShell 5.1 為本腳本的目標載體）'
exit 0
