<#
.SYNOPSIS
monorepo 一鍵開發環境整備（Windows）。macOS/Linux 對等腳本：tools/bootstrap.sh

.DESCRIPTION
  1. 若 .venv 已存在 → 直接沿用（免選直譯器）
  2. 否則檢查 Python 直譯器 >= 3.11（讀 .python-version 為目標版，截為 major.minor）
  3. 建立 .venv（偵測到 uv 則用 uv 加速，否則 python -m venv + pip）
  4. 安裝 AutoClaude（editable, [dev,notifications,lint]）+ AISDLC_SDD CI 依賴
  5. 印出啟用指引與 git-hooks 安裝選項（不自動改 core.hooksPath）

  Windows 上 `python` 通常已存在（py launcher / Store），啟用 .venv 後更明確；
  與 macOS 對齊後，所有裸 python 呼叫（含凍結版 SDD hooks）兩平台原樣可運作。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VenvDir = Join-Path $Root '.venv'

# 讀 .python-version 並截斷為 major.minor 兩段（防 `py -3.11.9` 非法旗標）
$PyTarget = (Get-Content (Join-Path $Root '.python-version') -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $PyTarget) { $PyTarget = '3.11' }
$PyTarget = $PyTarget.Trim()
$verParts = $PyTarget -split '\.'
if ($verParts.Length -gt 2) { $PyTarget = "$($verParts[0]).$($verParts[1])" }

Write-Host "===== AISDCL_Agent bootstrap（Windows）=====" -ForegroundColor Cyan
Write-Host "repo 根：$Root"
Write-Host "目標 Python：>= $PyTarget（.python-version）"

# --- 偵測 uv ---
$UseUv = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)
if ($UseUv) { Write-Host "偵測到 uv → 使用 uv 建立/安裝（加速）" -ForegroundColor Green }

# --- 選一個 >=3.11 的直譯器（僅 .venv 不存在且 uv 未裝時需要）---
function Select-Python {
  # 優先用 py launcher 指定版本，再回退各命名。
  # 探測段以 try/finally 局部設 EAP=Continue：PS5.1 下 native 指令 stderr 重導（2>$null）
  # 遇 $ErrorActionPreference='Stop' 會直接 throw（NativeCommandError），必須局部放寬。
  $candidates = @("py -$PyTarget", "py -3.12", "py -3.11", "python", "python3")
  $prevEAP = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    foreach ($c in $candidates) {
      $parts = $c -split '\s+'
      $exe = $parts[0]
      # 反向切片防呆：單 token（如 "python"）時 $parts[1..0] 會回捲取出錯誤元素
      $exeArgs = if ($parts.Length -gt 1) { @($parts[1..($parts.Length-1)]) } else { @() }
      if (Get-Command $exe -ErrorAction SilentlyContinue) {
        $null = & $exe @exeArgs -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return $c }
      }
    }
    return $null
  } finally {
    $ErrorActionPreference = $prevEAP
  }
}

# --- 1. 建立 .venv（存在檢查先行：venv 已存在就不需選直譯器）---
if (Test-Path $VenvDir) {
  Write-Host "偵測到既有 .venv → 沿用（如需重建請先 Remove-Item -Recurse -Force .venv）"
} else {
  $BasePy = $null
  if (-not $UseUv) {
    $BasePy = Select-Python
    if (-not $BasePy) {
      Write-Host ""
      Write-Host "❌ 找不到 Python >= $PyTarget。" -ForegroundColor Red
      Write-Host "   Windows 安裝建議：winget install Python.Python.3.11（或用 pyenv-win）" -ForegroundColor Yellow
      Write-Host "   或安裝 uv：winget install astral-sh.uv" -ForegroundColor Yellow
      exit 1
    }
    Write-Host "使用直譯器：$BasePy"
  }
  Write-Host "建立虛擬環境：.venv"
  if ($UseUv) {
    uv venv --python $PyTarget $VenvDir
  } else {
    $parts = $BasePy -split '\s+'
    # 同 Select-Python 的反向切片防呆
    $exeArgs = if ($parts.Length -gt 1) { @($parts[1..($parts.Length-1)]) } else { @() }
    & $parts[0] @exeArgs -m venv $VenvDir
  }
}

$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'

# --- 2. 安裝依賴 ---
function Install-Deps {
  param([string[]]$PipArgs)
  if ($UseUv) { uv pip install --python $VenvPy @PipArgs }
  else { & $VenvPy -m pip install @PipArgs }
}

Write-Host "`n----- 安裝依賴 -----" -ForegroundColor Cyan
if (-not $UseUv) { & $VenvPy -m pip install --upgrade pip | Out-Null }

Write-Host "[1/2] AutoClaude（editable, [dev,notifications,lint]）"
Install-Deps @("-e", "$Root\AutoClaude\.[dev,notifications,lint]")

$SddReq = Join-Path $Root 'AISDLC_SDD\AISDLC_SDD_v0.01\requirements-ci.txt'
if (Test-Path $SddReq) {
  Write-Host "[2/2] AISDLC_SDD CI 依賴（requirements-ci.txt）"
  Install-Deps @("-r", $SddReq)
} else {
  Write-Host "[2/2] 略過：找不到 $SddReq"
}

# --- 3. 完成指引 ---
Write-Host @"

✅ bootstrap 完成。

下一步（每個新終端機都要做，或設進 profile / VSCode 直譯器）：
    .venv\Scripts\Activate.ps1

啟用後驗證：
    Get-Command python      # 應指向 .venv\Scripts\python.exe
    cd AutoClaude; python -m pytest tests/ -q
    cd AISDLC_SDD; bash scripts/ci-gate.sh   # 需 Git Bash

git hooks（選用）：安裝根層 dispatcher hooks — 兩子專案閘門同時生效
（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，依 commit/push
涉及路徑自動分流），不再互斥；任一支安裝腳本皆指向同一 dispatcher，跑一次即可：
    powershell -ExecutionPolicy Bypass -File AutoClaude/tools/install_git_hooks.ps1
    （或 AISDLC_SDD/scripts/install-hooks.ps1，效果相同）
"@ -ForegroundColor Green
