<#
.SYNOPSIS
本地 nightly 排程腳本（SD_09 觀察期 #1/#2/#3 採集）

.DESCRIPTION
取代 GitHub Actions nightly cron job，於本地依序執行：
  - mutation-test (Docker / Linux mutmut) — 觀察期 #1（Docker 解 Windows 限制）
  - pg-e2e-nightly + AC4 collector        — 觀察期 #2
  - perf-baseline-nightly                  — 補強信號
  - drift_log 被動掃描                     — 觀察期 #3

容器策略：優先沿用既有 autoclaude_pg；若不存在才新建臨時 container。
既有 container 不在 Cleanup 中拆除。

對應 monorepo 根層 .github/workflows/autoclaude-ci.yml jobs，輸出與 CI artifact 同格式：
  .mutation_history.jsonl / .mutation_baseline.toml / mutation_backlog_token_guard.md
  .ac4_history.jsonl / .ac4_junit.xml
  perf_results.json / perf_regression_comment.md

執行紀錄寫入 logs/nightly_YYYY-MM-DD_HHMMSS.log（每次 run 獨立檔），
並 copy 至 logs/nightly_latest.log 供 retrieve；100% UTF-8 編碼。
Stage 失敗不中斷後續 stage（與 CI continue-on-error: true 一致）。

.NOTES
排程：schtasks /create /SC DAILY /ST 02:00 /TN "AutoClaude_Nightly" `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo>\tools\run_local_nightly.ps1"
🔴 排程後務必執行（elevated）：tools/fix_nightly_catchup.ps1
  schtasks.exe /create 建出的任務預設 WakeToRun=false + StartWhenAvailable=false，
  機器睡眠/休眠或關機時排程到點不喚醒、不補跑 → 觀察期 idle 漏跑（improving_102）。
  fix_nightly_catchup.ps1 啟用「喚醒啟動 WakeToRun + 開機補跑 StartWhenAvailable +
  電池不擋」三項；若睡眠仍漏跑，依該腳本提示用 powercfg 開啟電源計畫的喚醒計時器。
觀察期完成日：mutation #1 → 2026-06-01；AC4 #2 → 2026-06-02；drift #3 → 2026-06-17。

SD_09 W0 zero-trust audit 修復清單（2026-05-20）：
  P0-1  mutation-test 透過 tools/run_mutmut_in_docker.sh 執行，避免 here-string 截斷
        + 強制驗證 log 含 mutmut 統計或標記失敗
  P0-3  所有 native command 輸出走 Out-File -Encoding utf8（不再用 *>> 預設 UTF-16）
  P1-1  log 檔名含 RunId（HHMMSS）+ logs/nightly_latest.log pointer
  P1-2  Stopwatch 改 'hh\:mm\:ss\.fff' + stage 失敗主動 log ERROR
  P1-3  AC4 collector 真實門檻（外移至 tools/ac4_nightly_collector.py）
  P1-4  alembic 預設用 sync DSN；asyncpg DSN 改成 stage 內 lazy 設
#>

$ErrorActionPreference = 'Continue'
# SD_09 W3 Round 3 audit P2-2 修復：啟用 StrictMode 防止未定義變數 / 屬性錯誤靜默通過。
# 採用 3.0（涵蓋未初始化變數 + 不存在屬性 + 函數參數錯誤）；Latest 對 here-string / array
# 索引過於嚴格，risk 破壞既有正常 stage 流程。
Set-StrictMode -Version 3.0
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# SD_09 W0 二次 audit P0-C 修復：強制 console + Python 子程序統一 UTF-8
# 解決：Python sys.stdout 在 PS pipeline 下用 cp950 編碼 → Out-String 解 → 繁體中文破壞
# （例：「比對結果」→ "��ﵲ�G�G"；「跳過 seed」→ "���L seed"）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

# SD_09 W3 Round 19 audit P0-AUDIT-R18-1 修復（紀律 #14 schtasks PATH 補強）：
# 02:00 schtasks 第 14 跑（首次自動跑）pg-e2e stage 36ms 內 EXCEPTION crash：
#   「在此物件上找不到屬性 'Source'」(StrictMode 3.0 + $null.Source)
# 根因：schtasks 啟動的 powershell.exe 未經 pyenv 互動 hook → PATH 只含
#   `pyenv-win\shims` 但 shims 內無 alembic.bat → Get-Command alembic.exe 回 $null
#   → 後續 .Source 取屬性失敗。
# 修復：偵測 pyenv-win 存在但 Scripts/ 不在 PATH 時自動補入；確保 alembic.exe /
#   asyncpg / 等 Python entry-point exe 在 schtasks / 互動模式下行為一致。
try {
  $pyenvRoot = $env:PYENV
  if (-not $pyenvRoot -and $env:USERPROFILE) {
    $candidate = Join-Path $env:USERPROFILE '.pyenv\pyenv-win'
    if (Test-Path $candidate) { $pyenvRoot = $candidate }
  }
  if ($pyenvRoot -and (Test-Path $pyenvRoot)) {
    $versionsDir = Join-Path $pyenvRoot 'versions'
    if (Test-Path $versionsDir) {
      $pyVersion = Get-ChildItem $versionsDir -Directory -ErrorAction SilentlyContinue |
                   Sort-Object Name -Descending | Select-Object -First 1
      if ($pyVersion) {
        $scriptsPath = Join-Path $pyVersion.FullName 'Scripts'
        if ((Test-Path $scriptsPath) -and ($env:PATH -notlike "*$scriptsPath*")) {
          $env:PATH = "$scriptsPath;$env:PATH"
          Write-Host "[bootstrap] Added pyenv Scripts to PATH: $scriptsPath"
        }
      }
    }
  }
} catch {
  Write-Host "[bootstrap] WARN PATH augmentation failed: $_"
}

# ----- 日誌 -----
$LogDir = Join-Path $RepoRoot 'logs'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Today = Get-Date -Format 'yyyy-MM-dd'
$RunId = Get-Date -Format 'HHmmss'
$Log = Join-Path $LogDir ("nightly_{0}_{1}.log" -f $Today, $RunId)
$LatestLog = Join-Path $LogDir 'nightly_latest.log'

# 預先建立空檔（UTF-8，無 BOM）— 後續所有寫入均以 Out-File -Append -Encoding utf8 維持 UTF-8
[System.IO.File]::WriteAllText($Log, '', (New-Object System.Text.UTF8Encoding($false)))

# SD_09 W3 Round 2 audit P0-2 修復（紀律 #8 file locking）：
# Add-Content -Encoding utf8 內部以 FileShare.Read 開檔 → 與 tail -F / Less 同時讀取
# 時 Windows file lock 互卡 → 偶發「拋 IOException → ps1 stage crash」或「log 寫一半」。
# 改用 [System.IO.File]::Open + FileShare.ReadWrite + 5 次 retry（50/100/150/200/250ms
# 指數退避；上限 750ms）。失敗 stderr WARN 但不阻斷 stage rc。
function Add-LogLineSafe {
  param([string]$Path, [string]$Content)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $maxRetries = 5
  for ($i = 0; $i -lt $maxRetries; $i++) {
    try {
      $fs = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::Append,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::ReadWrite
      )
      try {
        $bytes = $utf8NoBom.GetBytes($Content + "`n")
        $fs.Write($bytes, 0, $bytes.Length)
        return $true
      } finally {
        $fs.Dispose()
      }
    } catch [System.IO.IOException] {
      Start-Sleep -Milliseconds (50 * ($i + 1))
      continue
    } catch {
      # 非 IO 例外不重試（如 UnauthorizedAccess），印 WARN 即返回 false
      [Console]::Error.WriteLine("[Add-LogLineSafe] non-IO error: $_")
      return $false
    }
  }
  [Console]::Error.WriteLine("[Add-LogLineSafe] WARN giving up after $maxRetries retries: $Path")
  return $false
}

function Log {
  param([string]$Msg, [string]$Level = 'INFO')
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  $line = "[$ts][$Level] $Msg"
  [void](Add-LogLineSafe -Path $Log -Content $line)
  Write-Host $line
}

# 將 native command 的 stdout + stderr 轉為文字流並 append 至 $Log（UTF-8）
# - 用 Out-String -Stream 把 record stream 攤平成字串，避免 NativeCommandError 物件被序列化成 UTF-16
# - SD_09 W3 Round 2 audit P0-2 修復：改 Add-LogLineSafe（FileShare.ReadWrite + retry）
function Invoke-Native {
  param([scriptblock]$Block)
  # SD_09 W2 audit P0-AUDIT-09 修復：保護 native exit code（紀律 #1）
  # PowerShell 5.1 pipeline 末段 cmdlet (Add-Content) 會覆寫 $LASTEXITCODE。
  # 解法：執行 block 後立刻 capture，跑完 pipeline 再寫回 $global:LASTEXITCODE。
  $output = & $Block 2>&1
  $capturedExitCode = $LASTEXITCODE
  $output | Out-String -Stream | ForEach-Object {
    if ($null -ne $_ -and $_ -ne '') {
      [void](Add-LogLineSafe -Path $Log -Content $_)
    }
  }
  # 還原 native 真實 exit code（不被 Add-Content 蓋掉）
  if ($null -ne $capturedExitCode) {
    $global:LASTEXITCODE = $capturedExitCode
  }
}

function Invoke-Stage {
  param([string]$Name, [scriptblock]$Block)
  Log "===== Stage start: $Name ====="
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $rc = 0
  try {
    & $Block
    # SD_09 W3 Round 7 audit P2-B 修復（紀律 #1 防禦性語意）：
    # 原 `if ($LASTEXITCODE)` PS truthy 對負值（如 SKIP_RC=-1）為 true → 若未來內部
    # scriptblock 顯式設 $global:LASTEXITCODE=-1 會誤入 fail 分支；改 `-ne 0` 明示語意。
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { $rc = $LASTEXITCODE }
  } catch {
    Log "EXCEPTION in $Name : $_" 'ERROR'
    $rc = 99
  }
  $sw.Stop()
  $elapsed = $sw.Elapsed.ToString('hh\:mm\:ss\.fff')
  Log ("===== Stage end:   $Name (exit={0}, elapsed={1}) =====" -f $rc, $elapsed)
  # SD_09 W3 Round 2 audit P0-6 修復：rc=2 視為 WARN（不算 fail，但保留至 summary）
  # 區分真綠 (rc=0) / 觀察期等待 (rc=2 WARN) / 真實失敗 (rc=1 / rc>=3)
  if ($rc -eq 2) {
    Log ("Stage WARN: name={0} exit=2 (e.g. perf undersampled BLOCK->WARN downgrade)" -f $Name) 'WARN'
  } elseif ($rc -ne 0) {
    Log ("Stage failed: name={0} exit={1}" -f $Name, $rc) 'ERROR'
  }
  return $rc
}

# SD_09 W3 Round 4 audit P1-AUDIT-R3-2 修復（紀律 #1 / #5）：
#   SKIP 哨兵 -1（取代字串 'SKIP'）→ summary type 統一為整數，下游 parser 不需 cast 字串。
#   保留 ToLabel helper 給人類 log 仍印 'SKIP' 字面值。
$SKIP_RC = -1
function Format-Rc {
  param([int]$Rc)
  if ($Rc -eq $SKIP_RC) { return 'SKIP' }
  return [string]$Rc
}

# SD_09 W2 nightly audit P0-1 修復（紀律 #1）：
# 原 `& git ... 2>&1 | Select-Object -First 1 -as [string]` 在 PS 5.1 觸發 NativeCommandError
# pipeline 物件 → 強制轉型 [string] 拿到空字串，導致 log header `branch=` `commit=` 全空 +
# .perf_history.jsonl 外層 git_sha 寫 "unknown"。
# 解法：stderr → $null（不走 2>&1 record stream），stdout via Out-String + Trim()。
try {
  $branch = (& git rev-parse --abbrev-ref HEAD 2>$null | Out-String).Trim()
} catch { $branch = '' }
try {
  $sha = (& git rev-parse --short HEAD 2>$null | Out-String).Trim()
} catch { $sha = '' }
$global:LASTEXITCODE = 0
Log "BEGIN nightly run host=$env:COMPUTERNAME branch=$branch commit=$sha run_id=$RunId log=$Log"
# 顯式驗證（修復後 branch / sha 應非空；空字串時印 WARN 便於人工排查）
if (-not $branch -or -not $sha) {
  Log "git context capture FAILED: branch='$branch' sha='$sha' — 請檢查 git 可用性 / PS 編碼" 'WARN'
} else {
  Log "git context: branch=$branch sha=$sha (verified non-empty)"
}

# SD_09 W3 Round 19 audit P1-AUDIT-R18-2 修復（紀律 #13 觀察期 jsonl 進度可見 + delta 取證）：
# 跑前 snapshot 各 jsonl 行數；跑後比對 delta，明示「本次 run 是否進帳」。
# 避免 stage exception 但 jsonl 凍結時，「END observation progress: ac4=4/14」誤導 user
# 以為進帳（實則 5/26 與 5/25 同筆 unchanged）。
function Get-JsonlCount {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return 0 }
  return @(Get-Content -Path $Path -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne '' }).Count
}
$script:PreMutationCount = Get-JsonlCount (Join-Path $RepoRoot '.mutation_history.jsonl')
$script:PreAc4Count = Get-JsonlCount (Join-Path $RepoRoot '.ac4_history.jsonl')
$script:PreObsCount = Get-JsonlCount (Join-Path $RepoRoot '.observability_history.jsonl')
$script:PreDriftCount = Get-JsonlCount (Join-Path $RepoRoot '.drift_log_history.jsonl')
Log ("BEGIN observation pre-snapshot: mutation={0} ac4={1} obs={2} drift={3} (jsonl records before this run; delta will be printed at END)" -f $script:PreMutationCount, $script:PreAc4Count, $script:PreObsCount, $script:PreDriftCount)

# ----- Stage L: local_ci_gate 全套（R9 複審 (b)；對齊 windows-compat-ci.yml 的
# windows-nightly-full job「執行 AutoClaude/tools/local_ci_gate.ps1」深度回歸步驟）-----
# 刻意放在最前：PG DSN / SD07_REAL_PG_E2E_ENABLED 等 env 於 Stage 0 之後才設，
# 此處環境等同開發者手動跑 tools/local_ci_gate.ps1，不受 nightly PG env 污染。
# 失敗不中斷後續 stage（Invoke-Stage 既有 continue-on-error 精神），rc 進
# summary 與終端 exit code。
$rcGate = Invoke-Stage 'local-ci-gate full (對齊 windows-nightly-full)' {
  Invoke-Native { powershell -NoProfile -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 }
}

# ----- Stage 0: Docker / PG 準備（優先沿用既有 autoclaude_pg）-----
# SD_09 W3 Round 4 audit P1-AUDIT-R3-4 修復：所有跨 scope 變數統一 $script: 前綴。
# 避免未來重構為 function 時，內層 $script:DockerOK 寫入 vs 外層裸 $DockerOK 讀
# 取造成永遠 $false（mutation/pg-e2e/drift stage 全 SKIP 假象）。
$script:ExistingContainer = 'autoclaude_pg'   # AutoClaude 既有 staging container
$script:EphemeralContainer = 'autoclaude_nightly_pg'  # 找不到既有時的退路
$script:UsedContainer = $null
$script:ContainerOwned = $false   # 我們建的才能在 Cleanup 拆掉
$script:DockerOK = $false
$null = Invoke-Stage 'Docker-PG-bring-up' {
  Invoke-Native { docker info }
  if ($LASTEXITCODE -ne 0) {
    Log 'Docker daemon 未啟動；跳過 PG 相依 stage' 'WARN'
    $global:LASTEXITCODE = 0
    return
  }
  # SD_09 W2 nightly audit P2-B 修復：原本未走 Invoke-Native，stderr 沒入 log；
  # 改 try/catch + 2>$null 把 stdout 收進變數（stderr 落空，不污染回傳）。失敗時為空字串。
  # SD_09 W3 Round 7 audit P2-A 修復（紀律 #1 一致性）：補 $script: 前綴統一 Round 4 R3-4 修復範圍
  # （原 R3-4 只修 DockerOK/UsedContainer/ContainerOwned，漏 ExistingContainer/EphemeralContainer 唯讀變數
  # 7 處讀取點 → 違反「跨 scope 變數統一 $script: 前綴」一致性紀律，後續若抽 function 會壞）
  try {
    $running = (& docker ps --filter "name=^$($script:ExistingContainer)$" --format '{{.Names}}' 2>$null | Out-String).Trim()
  } catch { $running = '' }
  Log "docker ps existing container check: running='$running' (expect '$($script:ExistingContainer)')"
  if ($running -eq $script:ExistingContainer) {
    Log "沿用既有 container: $($script:ExistingContainer)"
    $script:UsedContainer = $script:ExistingContainer
  } else {
    Log "未偵測到 $($script:ExistingContainer) ；新建臨時 container $($script:EphemeralContainer)"
    Invoke-Native { docker rm -f $script:EphemeralContainer }
    Invoke-Native {
      docker run -d --name $script:EphemeralContainer `
        -e POSTGRES_USER=autoclaude `
        -e POSTGRES_PASSWORD=autoclaude `
        -e POSTGRES_DB=autoclaude `
        -p 5432:5432 `
        pgvector/pgvector:pg17
    }
    if ($LASTEXITCODE -ne 0) { Log 'docker run 失敗' 'ERROR'; return }
    $script:UsedContainer = $script:EphemeralContainer
    $script:ContainerOwned = $true
  }
  # SD_09 W2 audit P0-AUDIT-05 修復：保留 docker exec 失敗訊息（紀律 #1 / #9）
  # 原 `*> $null` 全吞 stderr+stdout — 30 次 retry 全失敗時看不到原因
  $lastPgError = ''
  for ($i = 0; $i -lt 30; $i++) {
    $pgOut = docker exec $script:UsedContainer pg_isready -U autoclaude -d autoclaude 2>&1
    if ($LASTEXITCODE -eq 0) { $script:DockerOK = $true; break }
    $lastPgError = ($pgOut | Out-String).Trim()
    Start-Sleep -Seconds 2
  }
  if (-not $script:DockerOK) {
    Log "PG 60 秒內未就緒；最後一次 pg_isready 輸出：$lastPgError" 'WARN'
  }
  $global:LASTEXITCODE = 0
}

# DSN 預設策略（P1-4 修復）：預設用 sync DSN，避免 alembic 第一次跑就 MissingGreenlet。
# pg-e2e stage 內 alembic 完成後再 swap 為 asyncpg DSN。
$env:AUTOCLAUDE_TEST_PG_DSN          = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
$env:AUTOCLAUDE_DB_DSN               = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
$env:AUTOCLAUDE_ALLOW_INSECURE_DB    = '1'
$env:SD07_REAL_PG_E2E_ENABLED        = 'true'
# Windows + Docker Desktop 連線 overhead ~50ms；nightly 採集允許 80ms（Linux CI 維持 50ms）
# SD_09 W2 audit P0-AUDIT-08 修復（紀律 #6）：採集寬鬆 + 升級嚴格雙軌 — 兩條獨立 env，不再 swap
# SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地，2026-05-25）：
#   升級門檻自 50ms 改為 60ms tolerant；原 strict 50ms 軌降為觀察軌指標
#   - 採集（pytest + ac4_nightly_collector）AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS=80
#   - 升級判定（ac4_progress_check）AUTOCLAUDE_STRICT_P95_THRESHOLD_MS=60（ADR v0.4 ACCEPTED）
#   - 觀察軌指標（ac4_progress_check）AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS=50（向上相容）
# pytest 透過共用 AUTOCLAUDE_TEST_P95_THRESHOLD_MS（採集寬鬆同值）；下游兩工具各自讀獨立 env。
$env:AUTOCLAUDE_TEST_P95_THRESHOLD_MS = '80'
$env:AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS = '80'
$env:AUTOCLAUDE_STRICT_P95_THRESHOLD_MS = '60'
$env:AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS = '50'

# ----- Stage 1: mutation-test (透過 Docker / Linux container 跑 mutmut) -----
# Reason: mutmut 3.x 不支援 Windows 原生 (issue #397) → 改在 Linux container 內跑。
# 解析: 容器內 pip install -e .[dev] + mutmut；本地 Python 跑 baseline_lock + analysis（不需 mutmut）。
# pip cache 掛載至宿主 ~/.cache/pip 避免每次重抓依賴。
# P0-1 修復：不再用 bash -c "<bashCmd>"（here-string 被截斷），改用獨立 shell script
#          + 結束時驗證 mutation_token_guard.log 是否含真實 mutmut 統計。
# Round 4 P1-AUDIT-R3-2 修復：SKIP 統一為整數哨兵 -1（避免字串混雜整數）
$rc1 = $SKIP_RC
if ($script:DockerOK) {
  $PipCache = Join-Path $env:USERPROFILE '.cache\pip'
  if (-not (Test-Path $PipCache)) { New-Item -ItemType Directory -Force -Path $PipCache | Out-Null }
  $MutLog = Join-Path $RepoRoot 'mutation_token_guard.log'
  if (Test-Path $MutLog) { Remove-Item $MutLog -Force }
  $rc1 = Invoke-Stage 'mutation-test (Docker / Linux mutmut)' {
    Invoke-Native {
      docker run --rm `
        -v "${RepoRoot}:/workspace" -w /workspace `
        -v "${PipCache}:/root/.cache/pip" `
        -e LOG_FILE=mutation_token_guard.log `
        -e MODULE_PATH=autoclaude/plugins/token_guard `
        -e TESTS_DIR=tests/plugins/token_guard `
        python:3.11-slim bash /workspace/tools/run_mutmut_in_docker.sh
    }
    $dockerRc = $LASTEXITCODE
    # 驗證 mutmut log 真實性：呼叫 tools/validate_mutmut_log.py（可單元測試的 helper）。
    # graceful degradation：mutmut 全 survived 仍算真實 run（exit=0）；
    # 只有 log 全空 / 不存在 / 僅 help fallback / 0 mutant 時才算未跑（exit=2）。
    # 修補 SD_09 觀察期 #2 殘留缺陷：先前 regex 含 'mutmut' / 'to apply a mutant'
    # 過寬，會把 mutmut help fallback（90 bytes）誤判通過 → 假 pass。
    # TD-N02 修復（2026-06-12）：--require-version-marker — log 必須含
    # run_mutmut_in_docker.sh 版本守門通過標記（mutmut version OK: 2.4.3），
    # 防衛 mutmut 換版後輸出格式漂移仍假 pass（exit=3 取證可區分）。
    Invoke-Native { python tools/validate_mutmut_log.py $MutLog --require-version-marker }
    $validateRc = $LASTEXITCODE
    if ($validateRc -ne 0) {
      Log "mutation_token_guard.log 未含真實 mutmut 統計（validate_rc=$validateRc）— 標記 stage 失敗（避免假 pass）" 'ERROR'
      $global:LASTEXITCODE = 2
      return
    }
    Log "mutation_token_guard.log 通過真實性驗證（docker_rc=$dockerRc）"
    # SD_09 W1 QA #4：bitmask 判定改委派至 tools/mutmut_exit_code.py（SSOT），有完整單元測試。
    #   bit 0 (1) = exception / baseline crash（**真 fail**）
    #   bit 1 (2) = surviving > 0（預期）
    #   bit 2 (4) = surviving timeout > 0（容忍）
    #   bit 3 (8) = suspicious > 0（容忍）
    # 退出碼：0=正常結束 / 1=real_fail（bit0=1）
    Invoke-Native { python tools/mutmut_exit_code.py classify $dockerRc }
    $exitClassifyRc = $LASTEXITCODE
    if ($exitClassifyRc -eq 1) {
      Log "mutmut 真實失敗（rc=$dockerRc，bit0=exception/baseline-crash）— 標記 stage fail" 'ERROR'
      $global:LASTEXITCODE = $dockerRc
      return
    }
    if ($dockerRc -ne 0) {
      Log "mutmut exit=$dockerRc 為 bitmask（survived/timeout/suspicious）— 屬觀察期預期狀態，不視為 stage fail"
    }
    # 清零避免 baseline_lock / analysis 後 stage rc 仍是非零被外層 Invoke-Stage 抓到當 fail
    $global:LASTEXITCODE = 0
    # SD_09 W3 Round 2 audit P1-2 修復（紀律 #7 cache fresh）：
    # require log mtime 在 1 小時內，避免讀到 stale mutation log（如前次 crash 殘留）
    Invoke-Native {
      python tools/mutation_baseline_lock.py token_guard `
        --log mutation_token_guard.log `
        --history .mutation_history.jsonl `
        --baseline .mutation_baseline.toml `
        --require-log-mtime-within-seconds 3600
    }
    # SD_09 W2 nightly audit P0-2 修復：mutation_analysis.py 已移入 docker 內（mutmut 可用）
    # → 不再於 PS host 重複呼叫（Windows 上 subprocess "mutmut" FileNotFoundError → 全 "other"）。
    # backlog 由 docker container 產出，已寫入 mutation_backlog_token_guard.md。

    # SD_09 W3 Round 3 audit P2-4 修復：回流 mutation 5 行 counts 至主 nightly log。
    # SD_09 W3 Round 4 audit P0-AUDIT-R3-3 修復（紀律 #2 / #5）：
    #   原 `\([0-9]+\)` pattern 過寬 — 會抓 backlog 路徑（如 `compactor.py (13)`）+
    #   results 表頭 `Survived ?? (38)` → 主 log 回流 11 行雜訊污染統計。
    #   改用 marker section 擷取：以 `--- mutmut full counts (from cache; ...) ---` /
    #   `--- mutmut full counts (end) ---` 為邊界，僅擷取 5 行 Killed/Survived/...
    # SD_09 W1 ADR-SD09-010 §5 W1 修復（紀律 #4 SSOT 同構 + #5 跨工具對齊）：
    #   原 inline PowerShell 邏輯（4 分支 + regex marker section）改呼叫
    #   tools/mutmut_counts_parser.py Python helper（97 LOC + 7 case unit test 覆蓋）。
    #   helper 為 SSOT；本 ps1 區塊退化為 thin wrapper。任何邏輯變動同步更新 helper +
    #   重跑 tests/tools/test_mutmut_counts_parser.py（紀律 #4 鏡子被驗證）。
    if (Test-Path $MutLog) {
      $parserOutput = & python tools/mutmut_counts_parser.py $MutLog 2>&1
      $parserRc = $LASTEXITCODE
      foreach ($line in @($parserOutput)) {
        if ($null -ne $line -and "$line".Trim() -ne '') {
          if ("$line" -like '*WARN*' -or "$line" -like '*ERROR*') {
            Log "$line" 'WARN'
          } else {
            Log "$line"
          }
        }
      }
      if ($parserRc -ne 0) {
        Log "mutmut_counts_parser rc=$parserRc (non-zero)" 'WARN'
      }
      $global:LASTEXITCODE = 0
    }
  }
} else {
  Log 'Skip mutation-test（Docker 不可用）' 'WARN'
}

# ----- Stage 2: pg-e2e + AC4 collector (觀察期 #2) -----
# Round 4 P1-AUDIT-R3-2 修復：SKIP 統一為整數哨兵 -1
$rc2 = $SKIP_RC
if ($script:DockerOK) {
  $rc2 = Invoke-Stage 'pg-e2e + AC4 collector' {
    # SD_09 W3 Round 19 audit P0-AUDIT-R18-1 修復（紀律 #1 / #14 StrictMode 3.0 $null.Property）：
    # 原 `(Get-Command alembic.exe -ErrorAction SilentlyContinue).Source` 在 schtasks 自動跑
    # 場景下 PATH 不含 pyenv shims → Get-Command 回 $null → `.Source` 拋 PropertyNotFoundException
    # （StrictMode 3.0 對 $null.Property 嚴格）→ 整個 stage 36ms 內 crash。
    # 修復：兩步式拆解 — 先 Get-Command 賦值至變數，再 if 判斷後取 .Source。
    # 同 line 376 fallback path（-ErrorAction Stop）也對齊兩步式（避免 cmdlet exception 走 catch）。
    # alembic：必須走 alembic.exe（sys.path[0]=Scripts/）；用 `python -c` 會被 repo `alembic/` 目錄 import-shadow
    $alembicCmd = Get-Command alembic.exe -ErrorAction SilentlyContinue
    $alembicExe = $null
    if ($alembicCmd) { $alembicExe = $alembicCmd.Source }
    if (-not $alembicExe) {
      $pyCmd = Get-Command python -ErrorAction SilentlyContinue
      if ($pyCmd) {
        $pyExe = $pyCmd.Source
        try {
          $realPy = & $pyExe -c "import sys; print(sys.executable)" 2>$null
          if ($realPy) {
            $alembicExe = Join-Path (Split-Path $realPy -Parent) 'Scripts\alembic.exe'
          }
        } catch {
          Log "python 解析 sys.executable 失敗：$_" 'WARN'
        }
      } else {
        Log 'python 命令在 PATH 上找不到（schtasks SYSTEM 帳號需檢查 PATH）' 'ERROR'
      }
    }
    if (Test-Path $alembicExe) {
      # P1-4：DSN 預設已是 sync，alembic 跑完後 swap 為 asyncpg
      $syncDsn  = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
      $asyncDsn = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
      $env:AUTOCLAUDE_DB_DSN = $syncDsn
      Invoke-Native { & $alembicExe upgrade head }
      $env:AUTOCLAUDE_DB_DSN = $asyncDsn
    } else {
      Log "alembic.exe 找不到（嘗試: $alembicExe）；跳過 alembic upgrade" 'ERROR'
    }
    # seed 100 筆 1024-dim mock 向量（idempotent；已有資料時自動跳過）
    $syncDsn = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
    Invoke-Native { python tools/seed_kb.py --mock-pg-seed --pg-dsn $syncDsn }
    # SD_09 W3 nightly audit P1-CACHE-1 修復（紀律 #7 cache fresh）：
    # 跑前移除舊 .ac4_junit.xml 避免 pytest 中途 crash 留下舊 junit →
    # ac4_nightly_collector 解出舊資料 → 假 pass
    if (Test-Path '.ac4_junit.xml') {
      Remove-Item '.ac4_junit.xml' -Force -ErrorAction SilentlyContinue
      Log '.ac4_junit.xml 移除（強制 fresh）'
    }
    Invoke-Native {
      python -m pytest tests/integration/test_pgvector_real_recall.py `
        -v --tb=short -m pg_real --junitxml=.ac4_junit.xml
    }
    # R9 複審 (a)：pg-e2e stage 補 PG contract 測試（AUTOCLAUDE_TEST_PG_DSN 於本
    # stage 前已設好）。刻意獨立呼叫、不併入上面的 recall pytest：① 該檔無
    # pg_real marker，併入 `-m pg_real` 會被整檔 deselect（假接線）；② 不寫
    # .ac4_junit.xml，避免 contract 結果污染 ac4_nightly_collector 的 AC4 觀察期
    # 取證（collector 對 junit 內任一 failure/skip 都會降級 status）。
    # rc 以 [ref] 捕捉（D-10 模式），stage 末端還原，不被 collector /
    # progress_check 的 rc 蓋掉（紀律 #1 真實 rc）。
    $contractRcRef = [ref] 0
    Invoke-Native {
      python -m pytest tests/contract/test_pg_state_repository_contract.py `
        -v --tb=short
    }
    $contractRcRef.Value = $LASTEXITCODE
    Invoke-Native {
      python tools/ac4_nightly_collector.py `
        --junit-xml .ac4_junit.xml `
        --history .ac4_history.jsonl
    }
    # SD_09 W2 audit P0-AUDIT-08 修復：不再 swap，progress_check 已綁定 AUTOCLAUDE_STRICT_P95_THRESHOLD_MS
    # 雙軌 env 在 ps1 開頭已分別設定（80 採集 / 50 升級）
    Invoke-Native {
      python tools/ac4_progress_check.py `
        --history .ac4_history.jsonl --json
    }
    # SD_09 W3 zero-trust audit F2 修復（2026-05-24）：當 ready_for_labeled_pr 首次達標時，
    # 主動發告警提示需 PM 拍板啟用 AC4 workflow（autoclaude-pg-e2e-on-label.yml 雖技術上 active，
    # 但 PM approval ceremony 為議題 C 升級的硬性程序）。
    # 紀律 #3「PASS 聲稱必須引用 RunId log 行號」— 此告警同步寫入 nightly_latest.log 留下取證軌跡。
    try {
      # SD_09 W3 Round 8 audit P2-NEW-2 修復（紀律 #1 取證可見性）：
      # 原 `2>$null` 抑制 ac4_progress_check.py stderr → legacy_lenient 等 warning 被吃掉，
      # 違反「fallback 路徑必須留證」精神。改 `2>&1` 把 stderr 與 stdout 合流；
      # warning 行（非 JSON）被 ConvertFrom-Json 跳過前，先 Log 為 INFO 留入 nightly_latest.log。
      #
      # SD_09 W3 Round 9 audit P2-R9-1 修復（紀律 #4「驗證鏡子自身要被驗證」）：
      # 本區塊 F2 OK / F2 ALERT / F2 stderr / F2 WARN 4 條分支邏輯與
      # tools/ac4_nightly_alert_parser.py 同構（SSOT 樣板）。任一邏輯變動須同步：
      #   1. tools/ac4_nightly_alert_parser.py
      #   2. tests/tools/test_ac4_nightly_alert_parser.py（16 cases）
      # 否則 nightly 端與 helper 端 drift → audit 取證錯位。
      #
      # SD_09 W3 Round 10 audit P2-R10-1 修復（紀律 #4 SSOT 同構嚴格對齊）：
      # 原 `StartsWith('{') -or StartsWith('[')` 接受兩種 JSON 起點，但 helper 只接受 `{`
      # （理由：stderr warning 常以 `[ac4_progress_check] WARN:` 開頭，若接受 `[` 會誤判
      # 為 JSON array 起點 → ConvertFrom-Json 失敗走 catch → 假 F2 WARN）。
      # 現對齊 helper line 51：僅接受 `{` 為 JSON 起點；以 `[` 開頭的行進 stderr 攔截。
      # ac4_progress_check.py --json 永遠回 dict（非 list），故拒絕 `[` 不影響合法 JSON。
      $ac4Raw = python tools/ac4_progress_check.py --history .ac4_history.jsonl --json 2>&1 | Out-String
      $ac4Lines = $ac4Raw -split "`n"
      $ac4JsonLines = @()
      foreach ($line in $ac4Lines) {
        $trim = $line.Trim()
        if ($trim -eq '') { continue }
        if ($trim.StartsWith('{') -or $ac4JsonLines.Count -gt 0) {
          $ac4JsonLines += $line
        } else {
          Log "[F2 stderr] $trim"
        }
      }
      $ac4Out = ($ac4JsonLines -join "`n")
      $ac4Json = $ac4Out | ConvertFrom-Json
      if ($ac4Json.ready_for_labeled_pr -eq $true) {
        Log "[F2 ALERT] AC4 觀察期 #2 已達標 ready_for_labeled_pr=true (tolerant<60ms streak=$($ac4Json.tolerant_streak)/14 observation<50ms streak=$($ac4Json.observation_streak)/14; ADR-SD09-008 v0.4 ACCEPTED) — 需 PM 確認啟用 autoclaude-pg-e2e-on-label.yml workflow 並紀錄至 docs/06_quality/SD09_AC4_Activation_Approval.md" 'WARN'
      } else {
        Log "[F2 OK] AC4 觀察期 #2 累計中 status=$($ac4Json.status) tolerant<60ms streak=$($ac4Json.tolerant_streak) observation<50ms streak=$($ac4Json.observation_streak) days=$($ac4Json.observation_days) reasons=$($ac4Json.reasons -join '; ')"
      }
    } catch {
      Log "[F2 WARN] AC4 readiness 解析失敗：$_" 'WARN'
    }
    # R9 複審 (a)：contract 測試失敗必須反映到 stage rc（不被 F2 區塊尾端的
    # $LASTEXITCODE 蓋掉；紀律 #1 真實 rc）
    if ($contractRcRef.Value -ne 0) {
      Log "PG contract 測試失敗 rc=$($contractRcRef.Value) — 標記 stage fail" 'ERROR'
      $global:LASTEXITCODE = $contractRcRef.Value
    }
  }
} else {
  Log 'Skip pg-e2e（Docker 不可用）' 'WARN'
}

# ----- Stage 3: perf-baseline-nightly -----
# SD_09 W2 audit P1-AUDIT-17 修復：紀律 #7 cache fresh
# 跑前移除舊 perf_results.json 避免「舊 results + 當次 crash → 老資料騙過驗證」
if (Test-Path 'perf_results.json') {
  Remove-Item -Path 'perf_results.json' -Force -ErrorAction SilentlyContinue
  Log 'perf_results.json 移除（強制 fresh）'
}
$rc3 = Invoke-Stage 'perf-baseline' {
  Invoke-Native { python -m pytest tests/perf/ -v --tb=short -m perf }
  # TD-N01 修復（2026-06-12，AutoClaude_Improving_012 Phase 0）：
  # 對齊 ci.yml「Verify perf_results.json present」step — pytest 跑完後強制驗證
  # perf_results.json 確實由 tests/perf/conftest.py pytest_sessionfinish hook 產出。
  # 缺檔 = 本次採集無效（紀律 #1 真實失敗，不可讓後續 regression check 的
  # 「baseline 或 results 不存在」WARN 分支把 stage 染綠）→ stage rc=1。
  if (-not (Test-Path 'perf_results.json')) {
    Log 'perf_results.json 缺失 — tests/perf/conftest.py pytest_sessionfinish hook 應產生此檔（對齊 ci.yml Verify perf_results.json present；TD-N01）— 標記 stage fail' 'ERROR'
    $global:LASTEXITCODE = 1
    return
  }
  Log 'perf_results.json present（TD-N01 強制驗證通過）'
  # SD_09 W2 D-10 修復：使用 [ref] 變數 capture regression rc，避免 baseline_lock 跑完後 LASTEXITCODE 被覆蓋
  $regressionRcRef = [ref] 0
  $baselineLockRcRef = [ref] 0
  if ((Test-Path .perf_baseline.toml) -and (Test-Path perf_results.json)) {
    Invoke-Native {
      python tools/perf_regression_check.py perf_results.json .perf_baseline.toml `
        --comment-out perf_regression_comment.md
    }
    $regressionRcRef.Value = $LASTEXITCODE
  } else {
    Log 'baseline 或 results 不存在；首次跑請手動 perf_baseline_lock' 'WARN'
  }
  # SD_09 W2-#1：samples=20 累積；連續 7 次達標自動 lock .perf_baseline.toml
  # 紀律 #1：baseline_lock 是觀察期工具（不影響 stage rc）；保留 regression_check rc 作 stage rc
  if (Test-Path perf_results.json) {
    $shortSha = if ($sha) { $sha } else { 'unknown' }
    Invoke-Native {
      python tools/perf_baseline_lock.py `
        --results perf_results.json `
        --history .perf_history.jsonl `
        --baseline .perf_baseline.toml `
        --git-sha $shortSha
    }
    $baselineLockRcRef.Value = $LASTEXITCODE
    # SD_09 W2 D-10 雙印佐證：明確 log 兩個 rc 來源，避免 nightly summary 之 perf=0 與內部 BLOCK 信號矛盾
    Log "[perf] regression_check_rc=$($regressionRcRef.Value), baseline_lock_rc=$($baselineLockRcRef.Value)" 'INFO'
    # 紀律 #1：保留 regression_check 的真實 fail 信號，不被 lock rc 覆蓋
    $global:LASTEXITCODE = $regressionRcRef.Value
  }
}

# ----- 觀察期 #3 drift_log 被動掃描（每次 < 1 sec）-----
# SD_09 W3 nightly audit P0-DRIFT-1 修復（紀律 #1 / #3 / 跨 stage 一致性）：
#   Docker 不可用時與 mutation/pg-e2e stage 模式對齊 — 外層先賦值 'SKIP'，僅
#   Docker 可用時才走 Invoke-Stage；不可用時 WARN log + 呼叫 drift_log_snapshot
#   寫一筆 table_missing=True 的 N/A record（passed=False，不計入觀察期 #3 天數）。
#   原本 Docker 不可用時 stage 跑 15ms 跳過 if 區塊 → rc=0 → summary `drift=0`
#   給人「綠燈 = 觀察期 #3 進帳一天」假象，違反紀律 #1（stage rc 必須區分真實
#   成功 vs 工具標準回報）+ 紀律 #3（PASS 必須引取證）。
# Round 4 P1-AUDIT-R3-2 修復：SKIP 統一為整數哨兵 -1
$rc4 = $SKIP_RC
if ($script:DockerOK) {
  $rc4 = Invoke-Stage 'drift_log-scan (觀察期 #3)' {
    # SD_09 W0 二次 audit P1-I 修復：先驗證 drift_log 表存在
    # SD_09 W2 audit P1-AUDIT-22 修復：保留 psql stderr（紀律 #1）
    $tableQuery = docker exec $script:UsedContainer psql -U autoclaude -d autoclaude -t -c `
      "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='drift_log');" 2>&1
    $psqlRc = $LASTEXITCODE
    $tableExistsClean = ($tableQuery | Out-String).Trim()
    if ($psqlRc -ne 0) {
      Log "drift_log 表存在性查詢失敗 (rc=$psqlRc): $tableExistsClean — 標記 stage fail（紀律 #1）" 'ERROR'
      $global:LASTEXITCODE = $psqlRc
      return
    }
    if ($tableExistsClean -ne 't') {
      Log 'drift_log 表不存在（alembic_version 落後 0013_drift_log）— 標記 N/A 並回 rc=2 (WARN)，不計入觀察期 #3 天數' 'WARN'
      # SD_09 W2 nightly audit P1-5 修復：寫入 jsonl 持久化（table_missing=True → passed=False）
      Invoke-Native {
        python tools/drift_log_snapshot.py --severity-count 0 --table-missing `
          --history .drift_log_history.jsonl
      }
      # SD_09 W3 Round 3 audit P1-3 修復：table_missing 不可回 rc=0（語意衝突 — snapshot 標
      # passed=False 但 stage 回綠 → summary 「drift=0」假象綠燈）。改回 rc=2 (WARN)，
      # Invoke-Stage rc=2 視為 WARN 不算 fail（紀律 #1 / line 145）。
      $global:LASTEXITCODE = 2
      return
    }
    $cntQuery = docker exec $script:UsedContainer psql -U autoclaude -d autoclaude -t -c `
      "SELECT COUNT(*) FROM drift_log WHERE severity != 'info';" 2>&1
    $cntRc = $LASTEXITCODE
    if ($cntRc -eq 0) {
      $n = ($cntQuery | Out-String).Trim()
      Log "drift_log severity!='info' rows = $n"
      if ([int]$n -gt 0) { Log "drift_log 非零！觀察期 #3 違反" 'ERROR' }
      # SD_09 W2 nightly audit P1-5 修復：持久化累計（紀律 #2 — 完整證據）
      # 觀察期 #3「30 天零事件」需 jsonl 累計可審計，不能只靠 ps1 log 末筆
      Invoke-Native {
        python tools/drift_log_snapshot.py --severity-count $n `
          --history .drift_log_history.jsonl
      }
    } else {
      Log "drift_log 查詢失敗 (rc=$cntRc): $(($cntQuery | Out-String).Trim())" 'ERROR'
    }
    # 預期分支 → 清 $LASTEXITCODE 避免污染後續 stage rc
    $global:LASTEXITCODE = 0
  }
} else {
  Log 'Skip drift_log-scan（Docker 不可用）— 寫 N/A jsonl，不計入觀察期 #3 天數' 'WARN'
  # P0-DRIFT-1：Docker 不可用時也持久化一筆 table_missing record（passed=False），
  # 確保 .drift_log_history.jsonl 累計可審計 = mutation/pg-e2e SKIP 對稱語意。
  Invoke-Native {
    python tools/drift_log_snapshot.py --severity-count 0 --table-missing `
      --history .drift_log_history.jsonl
  }
  # SD_09 W3 Round 3 audit P1-3 修復：rc=0 → rc4 由 'SKIP' 變綠 → summary `drift=SKIP`
  # 已正確；無需改變外層 rc4='SKIP'（已在 line 425 設定）。本分支不寫入 rc，保持 SKIP 語意。
}

# ----- Stage 5: observability-snapshot（D-16 / W5 雙條件 (1a) 30 天取證）-----
# 每日寫 1 筆至 .observability_history.jsonl；同日去重；30 天起算 2026-05-22
$rc5 = Invoke-Stage 'observability-snapshot' {
  Invoke-Native { python tools/observability_snapshot.py }
  $snapRc = $LASTEXITCODE
  if ($snapRc -ne 0) { return }   # 保留 snapshot 真實 rc（紀律 #1）
  # TD-N03 修復（2026-06-12，AutoClaude_Improving_012 Phase 0）：整合驗證 —
  # observability_snapshot.py 以 UTC ISO timestamp 寫入並同 UTC 日去重後 append 至末行，
  # 故 stage 成功後 .observability_history.jsonl 最後一筆 ts 的 UTC 日期必須等於今日；
  # 否則 snapshot「印 OK 但實際未落盤」假綠（紀律 #4 鏡子被驗證）→ stage rc=1。
  $histPath = Join-Path $RepoRoot '.observability_history.jsonl'
  if (-not (Test-Path $histPath)) {
    Log ".observability_history.jsonl 不存在 — snapshot 宣稱成功但未落盤 — 標記 stage fail（TD-N03）" 'ERROR'
    $global:LASTEXITCODE = 1
    return
  }
  # 已知接受風險：跨 UTC 午夜秒級窗口可能 false fail（fail-loud 方向，重跑即解）。
  $todayUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
  $lastDate = ''
  $lastTs = ''
  try {
    $obsLines = @(Get-Content -Path $histPath -ErrorAction Stop | Where-Object { $_.Trim() -ne '' })
    if ($obsLines.Count -gt 0) {
      $lastRecord = $obsLines[$obsLines.Count - 1] | ConvertFrom-Json
      # StrictMode 3.0：PSCustomObject 缺 ts 屬性會拋 PropertyNotFoundException → 由 catch 接住
      $lastTs = [string]$lastRecord.ts
      $lastDate = [datetime]::Parse($lastTs).ToUniversalTime().ToString('yyyy-MM-dd')
    }
  } catch {
    Log "observability 整合驗證：jsonl 末筆解析失敗：$_ — 標記 stage fail（TD-N03）" 'ERROR'
    $global:LASTEXITCODE = 1
    return
  }
  if ($lastDate -eq $todayUtc) {
    Log "observability 整合驗證通過：末筆 ts=$lastTs（UTC date=$lastDate = today）（TD-N03）"
    $global:LASTEXITCODE = 0
  } else {
    Log "observability 整合驗證失敗：末筆 UTC date='$lastDate' != today '$todayUtc'（ts='$lastTs'）— 標記 stage fail（TD-N03）" 'ERROR'
    $global:LASTEXITCODE = 1
  }
}

# ----- Cleanup（僅清掉本次新建的臨時 container；既有的不動）-----
# SD_09 W3 Round 21 audit QA P1-R21-2 修復（紀律 #1 真實 rc）：
#   舊版 `$global:LASTEXITCODE = 0` 強制清零會吞掉 docker rm 失敗的真實 rc，
#   下次跑可能因 port conflict 失敗但無告警。改為保留真實 rc 並印 WARN（不阻斷）。
$null = Invoke-Stage 'Cleanup' {
  if ($script:ContainerOwned -and $script:UsedContainer) {
    Invoke-Native { docker rm -f $script:UsedContainer }
    $rmRc = $global:LASTEXITCODE
    if ($rmRc -ne 0) {
      Log "已清除臨時 container 失敗 rc=$rmRc container=$script:UsedContainer（保留真實 rc 供取證；不阻斷後續 stage）" 'WARN'
    } else {
      Log "已清除臨時 container: $script:UsedContainer"
    }
  } else {
    Log "保留既有 container: $script:UsedContainer（非本腳本建立）"
    $global:LASTEXITCODE = 0
  }
}

# SD_09 W3 Round 4 audit P1-AUDIT-R3-2 修復（紀律 #5）：
#   人類可讀 summary 仍印 'SKIP' / 數字字面，但同時印 JSON 一行供下游 parser 解析。
#   SKIP 在 JSON 是整數 -1（type 統一）；下游不需處理字串混雜整數。
$rc1Label = Format-Rc $rc1
$rc2Label = Format-Rc $rc2
$rc3Label = Format-Rc $rc3
$rc4Label = Format-Rc $rc4
$rc5Label = Format-Rc $rc5
$rcGateLabel = Format-Rc $rcGate
# R9 複審 (b)：local_ci_gate 欄位附加於既有五欄之後（不動既有欄位順序，下游以
# 具名欄位解析不受影響）
Log "END nightly summary: mutation=$rc1Label pg-e2e=$rc2Label perf=$rc3Label drift=$rc4Label obs=$rc5Label local_ci_gate=$rcGateLabel"
$summaryJson = ConvertTo-Json -Compress -InputObject @{
  mutation = [int]$rc1
  'pg-e2e' = [int]$rc2
  perf = [int]$rc3
  drift = [int]$rc4
  obs = [int]$rc5
  local_ci_gate = [int]$rcGate
  skip_sentinel = $SKIP_RC
}
Log "END nightly summary json: $summaryJson"

# SD_09 W3 Round 5 audit P1-2 修復（紀律 #3 取證可見性）：
#   印觀察期累計進度供人類即時判斷。jsonl 同 UTC date dedup（M-05 設計）→
#   同日多 run 不會增加 record；本段讓 user 看到「N/門檻」避免「user 以為進帳實際被覆寫」失準。
# SD_09 W3 Round 19 audit P1-AUDIT-R18-2 修復（紀律 #13 觀察期 jsonl delta 取證）：
#   新增 pre/post delta 與 stage rc 對照，明示「本次 run 是否真進帳」。
#   例：mutation=4/7 (delta=0; stage=0) → stage 成功但 dedup 同日覆寫，未進帳新天數
#       ac4=4/14 (delta=0; stage=99 EXCEPTION) → stage crash, jsonl 凍結（首次自動跑 P0 BUG 場景）
$mutCount = Get-JsonlCount (Join-Path $RepoRoot '.mutation_history.jsonl')
$ac4Count = Get-JsonlCount (Join-Path $RepoRoot '.ac4_history.jsonl')
$obsCount = Get-JsonlCount (Join-Path $RepoRoot '.observability_history.jsonl')
$driftCount = Get-JsonlCount (Join-Path $RepoRoot '.drift_log_history.jsonl')
$mutDelta = $mutCount - $script:PreMutationCount
$ac4Delta = $ac4Count - $script:PreAc4Count
$obsDelta = $obsCount - $script:PreObsCount
$driftDelta = $driftCount - $script:PreDriftCount
Log ("END observation progress: mutation={0}/7 (delta={1}; stage={2}) ac4={3}/14 (delta={4}; stage={5}) obs={6}/30 (delta={7}; stage={8}) drift={9}/30 (delta={10}; stage={11}) — same UTC-date dedup per M-05; delta=0 with stage!=0 表示本次未進帳" -f $mutCount, $mutDelta, $rc1Label, $ac4Count, $ac4Delta, $rc2Label, $obsCount, $obsDelta, $rc5Label, $driftCount, $driftDelta, $rc4Label)

# R9 複審 (c)：終端 exit code 帶訊號（schtasks Last Result 取證；原本恆 0）。
# 失敗判定與 Invoke-Stage 既有語意一致：SKIP（$SKIP_RC=-1，Docker 不可用等）與
# WARN（rc=2，見 Invoke-Stage 的 P0-6 註解「不算 fail」）不計失敗；其餘非零＝失敗。
# 判定先於 pointer 更新寫入 log（取證），實際 exit 置於 pointer 更新之後——
# 不破壞「stage 失敗不中斷後續 stage」設計（所有 stage 此時已跑完）。
$finalFailures = @()
foreach ($pair in @(
    @('local_ci_gate', $rcGate), @('mutation', $rc1), @('pg-e2e', $rc2),
    @('perf', $rc3), @('drift', $rc4), @('obs', $rc5))) {
  $stageRc = [int]$pair[1]
  if ($stageRc -ne $SKIP_RC -and $stageRc -ne 0 -and $stageRc -ne 2) {
    $finalFailures += ('{0}={1}' -f $pair[0], $stageRc)
  }
}
if ($finalFailures.Count -gt 0) {
  Log ("END exit decision: exit=1 (failed stages: {0})" -f ($finalFailures -join ', ')) 'ERROR'
} else {
  Log 'END exit decision: exit=0 (no failed stages; SKIP/WARN 不計失敗)'
}

# P1-1：更新 latest pointer，並 echo 給人工 retrieve
try {
  Copy-Item -Path $Log -Destination $LatestLog -Force -ErrorAction Stop
  Log "Latest log pointer 已更新: $LatestLog"
} catch {
  Log "Latest log pointer 更新失敗：$_" 'WARN'
}
Write-Host ("Nightly log: {0}" -f $Log)
Write-Host ("Nightly latest pointer: {0}" -f $LatestLog)
if ($finalFailures.Count -gt 0) { exit 1 }
exit 0
