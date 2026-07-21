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
# 涵蓋（對照 windows-compat-ci.yml windows-smoke 各 step；預期 PASS 總數 = 8）：
#   [1] PowerShell parse 檢查：根層 tools/（含 tools/lib/）全部 active .ps1 以
#       [System.Management.Automation.Language.Parser]::ParseFile 驗 0 error
#       （對本 repo 直跑、唯讀。凍結版 AISDLC_SDD/AISDLC_SDD_v0.01~v0.29 位於
#       AISDLC_SDD/ 之下、依凍結紀律不回改，本就不在根層 tools/ 掃描範圍。
#       鏡射 root-infra-ci.yml「pwsh 語法解析」step 的根層子集）
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
#
# 限制（如實揭露）：
#   - fake repo 以 git clone 自本 repo HEAD 建立 → 未 commit 的變更不在驗證範圍
#     （worktree/clone 隔離盲區：驗證前先 commit）。
#   - 無法（或不宜）本地化的 windows-compat-ci step 不在本腳本範圍：
#     bootstrap.ps1／dev_start.ps1 實跑、integration_gate.ps1 -SkipFull、ci-gate.ps1、
#     tools/tests pytest、「根層 dispatcher hooks 真實 git commit 觸發」step（需 bash
#     載體＋probe commit）、install_post_commit.ps1 中文 clone 的逐字編碼斷言
#     （本檔 [6] 以安裝往返 + .git/config 直讀做精神抽驗，未逐字鏡射該 step）。
#   - check_ntfs_paths.py / check_script_parity.py 未納入本檔記點（macos_smoke_local.sh
#     [5] 已本地涵蓋同款唯讀檢查；Windows 側需要時可直接 `python tools/check_ntfs_paths.py`
#     與 `python tools/check_script_parity.py` 手跑）。
#   - [6] 的編碼斷言直讀 .git/config 位元組（UTF-8），不依賴主控台解碼；若在傳統
#     cp950 主控台下 FAIL，反映的是該環境下安裝腳本對非 ASCII 路徑的真實缺陷，
#     而非本載具誤報。
#   - 🔴 載具要求：請以「原生 PowerShell」執行（PowerShell 視窗／schtasks／
#     Windows Terminal）。經 Git Bash 間接呼叫 powershell.exe 時，msys→Win32
#     引數/主控台編碼轉換會弄壞 [6] 中文路徑情境（R10 實測：Git Bash 載具
#     PASS=7 假紅、原生 PowerShell PASS=8 全綠）——載具問題非生產缺陷。
#
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File tools\windows_smoke_local.ps1
# Exit：0＝全部 PASS；1＝任一 FAIL（結尾彙總）或前置守門失敗。

# 控制流全靠顯式 rc / 狀態檢查（鏡射 .sh 版 set -u 精神），不用例外中斷：
# 刻意不設 $ErrorActionPreference = 'Stop'——受測腳本自帶 exit 慣例，用
# $LASTEXITCODE 斷言比例外傳播可預期（見 windows-compat-ci.yml 同款手法註解）。

$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))

# ── 前置守門：git / python 缺席 fail-fast（比照 .sh 版與共用層訊息）─────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host '❌ 找不到 git — 請先安裝 Git for Windows（見 ONBOARDING.md §2）' -ForegroundColor Red
  exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

$script:Pass = 0
$script:Fail = 0
$script:FailList = @()

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
    $hp = git config --get core.hooksPath
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
      # 直讀共享 .git/config 的 UTF-8 位元組，不經主控台解碼——編碼損毀（cp950
      # 誤讀成 mojibake / '?'）會在此現形（R9 修復主題）。
      $cfgPath = Join-Path $TargetRepo '.git\config'
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
    $hp2 = git config --get core.hooksPath
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
  # ── [1/6] PowerShell parse 檢查（根層 tools/ 全部 active .ps1，唯讀）──────────
  Write-Host ''
  Write-Host '--- [1/6] Parser 解析檢查（根層 tools/ 含 tools/lib/ 全部 .ps1，對本 repo 直跑）---'
  $ps1Files = @(Get-ChildItem -Path (Join-Path $RepoRoot 'tools') -Recurse -Filter *.ps1 -File)
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
  if ($ps1Files.Count -eq 0) {
    Fail-Item '根層 tools/ 下找不到任何 .ps1（掃描異常，非假 PASS）'
  } elseif ($parseBad -eq 0) {
    Pass-Item "Parser 解析全數通過（$($ps1Files.Count) 檔）"
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
    # ── [2/6] install_git_hooks.ps1 安裝／解除往返（fake repo）───────────────────
    Write-Host ''
    Write-Host '--- [2/6] AutoClaude/tools/install_git_hooks.ps1 安裝／解除往返（fake repo）---'
    Test-InstallRoundtrip -TargetRepo $Fake -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
      -UninstallSwitch -Label '[2] install_git_hooks.ps1'

    # ── [3/6] install_git_hooks.ps1 linked worktree 拒絕 ─────────────────────────
    Write-Host ''
    Write-Host '--- [3/6] install_git_hooks.ps1 於 linked worktree 應拒絕（fail-loud）---'
    Test-WorktreeReject -BaseRepo $Fake -InstallerRel 'AutoClaude\tools\install_git_hooks.ps1' `
      -WorktreeName 'wt-install-git-hooks-reject' -Label '[3] install_git_hooks.ps1'

    # ── [4/6] install-hooks.ps1 安裝往返 + linked worktree 拒絕 ──────────────────
    Write-Host ''
    Write-Host '--- [4/6] AISDLC_SDD/scripts/install-hooks.ps1 往返 + worktree 拒絕（fake repo）---'
    Test-InstallRoundtrip -TargetRepo $Fake -InstallerRel 'AISDLC_SDD\scripts\install-hooks.ps1' `
      -CheckSeparators -Label '[4] install-hooks.ps1'
    Test-WorktreeReject -BaseRepo $Fake -InstallerRel 'AISDLC_SDD\scripts\install-hooks.ps1' `
      -WorktreeName 'wt-install-hooks-reject' -Label '[4] install-hooks.ps1'

    # ── [5/6] LATEST install_post_commit.ps1 worktree 實跑 + 移除後路徑斷言 ───────
    Write-Host ''
    Write-Host '--- [5/6] install_post_commit.ps1 worktree 實跑 + 移除後路徑斷言（fake repo）---'
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
        $commonDirRaw = git -C $Fake rev-parse --path-format=absolute --git-common-dir
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($commonDirRaw)) {
          Fail-Item '[5] git rev-parse --git-common-dir 失敗（需 git >= 2.31）'
          $step5Ok = $false
        } else {
          $target = Join-Path ([string]$commonDirRaw).Trim() 'hooks\post-commit'
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

    # ── [6/6] 非 ASCII 路徑防護抽驗（中文目錄 clone + 安裝往返）───────────────────
    Write-Host ''
    Write-Host '--- [6/6] 非 ASCII 路徑防護抽驗（「煙霧測試」目錄 clone + install_git_hooks.ps1 往返）---'
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
# 刻意刪減驗證項時同步下修本值（現況滿版 PASS=8）。
$MinPass = 8
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
