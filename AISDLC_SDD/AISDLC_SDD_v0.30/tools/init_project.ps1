# AISDLC 專案初始化腳本 (PowerShell 版本)
# 版本: v3.3-SDD
# 最後更新: 2026-04-15
# 適用於: Windows 11/10, PowerShell 5.1+
# 用途: 從 GitHub 下載並初始化 AISDLC / AISDLC-SDD 框架到專案目錄
# 支援: 公開倉庫 (HTTPS) / 私有倉庫 (SSH/PAT)
# 新增: SDD 模式（-SDD）、本地模式偵測

param(
    [Alias("v")]
    [string]$Version = "",

    [Alias("d")]
    [string]$Dir = ".",

    [Alias("s")]
    [switch]$SSH,

    [Alias("t")]
    [string]$Token = "",

    [Alias("l")]
    [string]$Local = "",

    [switch]$SDD,

    [Alias("h")]
    [switch]$Help
)

# ===== 配置 =====
$GITHUB_REPO = "wuweihungmobile/AISDLC"
$GITHUB_URL_HTTPS = "https://github.com/$GITHUB_REPO.git"
$GITHUB_URL_SSH = "git@github.com:$GITHUB_REPO.git"
$DEFAULT_VERSION = "0.09"
$DEFAULT_SDD_VERSION = "0.01"
$LocalSource = $Local
$UseSDD = $SDD.IsPresent

# 版本預設值：SDD 模式用 0.01，一般模式用 0.09
if ($Version -eq "") {
    $Version = if ($UseSDD) { $DEFAULT_SDD_VERSION } else { $DEFAULT_VERSION }
}

# 設定錯誤處理
$ErrorActionPreference = "Stop"

# ===== 輔助函數 =====

function Show-Banner {
    Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║       AISDLC 專案初始化工具 v3.2                      ║" -ForegroundColor Cyan
    Write-Host "║       AI-assisted Software Development Lifecycle       ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Usage {
    Write-Host "使用方式:" -ForegroundColor Blue
    Write-Host "  .\init_project.ps1 [選項]"
    Write-Host ""
    Write-Host "選項:" -ForegroundColor Blue
    Write-Host "  -Version, -v VERSION   指定 AISDLC 版本 (預設: $DEFAULT_VERSION)"
    Write-Host "  -Dir, -d DIRECTORY     指定安裝目錄 (預設: 當前目錄)"
    Write-Host "  -SSH, -s               使用 SSH 連線 (私有倉庫需要)"
    Write-Host "  -Token, -t TOKEN       使用 PAT Token 連線 (私有倉庫，無 SSH 時使用)"
    Write-Host "  -Local, -l PATH        指定本地框架路徑 (跳過下載)"
    Write-Host "  -Help, -h              顯示此說明"
    Write-Host ""
    Write-Host "🌐 遠端安裝 (從 GitHub 直接執行):" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  # 公開倉庫 - 一行安裝" -ForegroundColor Green
    Write-Host "  irm https://raw.githubusercontent.com/$GITHUB_REPO/main/AISDLC_v$DEFAULT_VERSION/tools/init_project.ps1 | iex"
    Write-Host ""
    Write-Host "  # 公開倉庫 - 指定版本和目錄 (需先下載)" -ForegroundColor Green
    Write-Host "  irm https://raw.githubusercontent.com/$GITHUB_REPO/main/AISDLC_v$DEFAULT_VERSION/tools/init_project.ps1 -OutFile init.ps1; .\init.ps1 -v 0.09 -d .\my-project"
    Write-Host ""
    Write-Host "  # 私有倉庫 - 使用 PAT Token 下載後執行" -ForegroundColor Green
    Write-Host '  $h = @{ Authorization = "token YOUR_PAT" }; Invoke-WebRequest -Uri "https://raw.githubusercontent.com/' + $GITHUB_REPO + '/main/AISDLC_v' + $DEFAULT_VERSION + '/tools/init_project.ps1" -Headers $h -OutFile init.ps1; .\init.ps1 -Token YOUR_PAT'
    Write-Host ""
    Write-Host "📁 本地安裝 (推薦，已 clone 後使用):" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  # 在已 clone 的框架目錄中執行（自動偵測本地框架，跳過下載）"
    Write-Host "  cd AISDLC"
    Write-Host "  .\AISDLC_v0.09\tools\init_project.ps1 -Dir C:\Projects\MyApp"
    Write-Host ""
    Write-Host "  # 手動指定本地框架路徑"
    Write-Host "  .\init_project.ps1 -Local C:\AISDLC -Dir C:\Projects\MyApp"
    Write-Host ""
    Write-Host "💡 提示:" -ForegroundColor Yellow
    Write-Host "  • 公開倉庫: 直接使用 HTTPS (預設)"
    Write-Host "  • 私有倉庫: 使用 -SSH 或 -Token YOUR_PAT"
    Write-Host "  • 最穩定方式: 先 git clone 到本地，再執行腳本（自動偵測，跳過下載）"
    Write-Host ""
}

function Test-Dependencies {
    Write-Host "⏳ 檢查必要工具..." -ForegroundColor Yellow

    $missingDeps = @()

    # Check for Git
    try {
        $null = Get-Command git -ErrorAction Stop
    } catch {
        $missingDeps += "git"
    }

    if ($missingDeps.Count -ne 0) {
        Write-Host "❌ 缺少必要工具: $($missingDeps -join ', ')" -ForegroundColor Red
        Write-Host "   請先安裝缺少的工具後再執行此腳本" -ForegroundColor Yellow
        Write-Host "   Git 下載: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "✅ 所有必要工具已安裝" -ForegroundColor Green
    Write-Host ""
}

function Find-LocalFramework {
    # 自動偵測：腳本所在目錄的上層是否就是框架版本目錄
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = Split-Path -Parent $PSCommandPath }

    $parentDir = Split-Path -Parent $scriptDir
    $grandParentDir = Split-Path -Parent $parentDir

    # 檢查: 腳本位於 AISDLC_vX.XX/tools/ 內
    $agentDir = Join-Path $parentDir "agent"
    $docsTemplateDir = Join-Path $parentDir "docs_template"
    $initFile = Join-Path $parentDir "AISDLC_INIT.md"

    if ((Test-Path $agentDir) -and (Test-Path $docsTemplateDir) -and (Test-Path $initFile)) {
        $script:LocalSource = $grandParentDir
        Write-Host "🔍 偵測到本地框架: $($script:LocalSource)" -ForegroundColor Green
        return $true
    }

    return $false
}

function Get-AISDLC {
    param(
        [string]$TargetVersion,
        [string]$TargetDir,
        [bool]$UseSSH
    )

    # SDD 模式使用 AISDLC_SDD_v{version}，一般模式使用 AISDLC_v{version}
    $aisdlcDir = if ($UseSDD) { "AISDLC_SDD_v$TargetVersion" } else { "AISDLC_v$TargetVersion" }
    $sourceDir = ""
    $tempDir = ""

    # === 本地模式：優先使用本地框架 ===
    if ($LocalSource) {
        $sourceDir = $LocalSource

        $versionPath = Join-Path $sourceDir $aisdlcDir
        if (-not (Test-Path $versionPath)) {
            Write-Host "❌ 本地路徑找不到版本 v$TargetVersion" -ForegroundColor Red
            Write-Host "   可用版本:" -ForegroundColor Yellow
            # SDD 模式目錄命名為 AISDLC_SDD_v*，非 SDD 模式為 AISDLC_v*——固定用後者
            # 過濾會使 -SDD 模式印出空清單（R16 相容性掃描）
            $fallbackFilter = if ($UseSDD) { "AISDLC_SDD_v*" } else { "AISDLC_v*" }
            Get-ChildItem $sourceDir -Directory -Filter $fallbackFilter | ForEach-Object {
                $vName = $_.Name -replace $fallbackFilter.TrimEnd('*'), ""
                Write-Host "   - v$vName"
            }
            exit 1
        }

        Write-Host "✅ 偵測到本地 AISDLC v$TargetVersion，跳過網路下載" -ForegroundColor Green
    } else {
        # === 遠端模式：從 GitHub 下載 ===
        $tempDir = Join-Path $env:TEMP "aisdlc_temp_$(Get-Random)"
        $sourceDir = Join-Path $tempDir "repo"

        # 選擇 URL
        if ($UseSSH) {
            $gitUrl = $GITHUB_URL_SSH
            Write-Host "⏳ 從 GitHub 下載 AISDLC v$TargetVersion (SSH)..." -ForegroundColor Yellow
        } elseif ($Token) {
            $gitUrl = "https://$Token@github.com/$GITHUB_REPO.git"
            Write-Host "⏳ 從 GitHub 下載 AISDLC v$TargetVersion (HTTPS + PAT)..." -ForegroundColor Yellow
        } else {
            $gitUrl = $GITHUB_URL_HTTPS
            Write-Host "⏳ 從 GitHub 下載 AISDLC v$TargetVersion (HTTPS)..." -ForegroundColor Yellow
        }
        Write-Host "   倉庫: $GITHUB_REPO" -ForegroundColor Blue

        # R16（DEF-101-124 同款病灶；比照 fsm_runtime/formal/run_tlc.ps1 R9 D-1 /
        # arch_fitness/run_self_evolution.ps1 R13 SH-2）：`2>&1 | Out-Null` 在
        # Windows PowerShell 5.1 + 上方全域 $ErrorActionPreference="Stop" 下，git clone
        # 只要對 stderr 寫入任何一行（即使 clone 本身成功，git 仍常態性印進度到 stderr）
        # 就會被包成 ErrorRecord 拋出 NativeCommandError，被下方 catch 誤判為連線失敗。
        # PS 5.1 改用不合併串流的 2>$null，直接以 $LASTEXITCODE 判斷成敗，不再依賴
        # try/catch 攔截 stderr 觸發的例外（pwsh 7+ 維持原行為不變）。
        # 註記：此守衛僅在 PS 5.1 環境重現，本機為 pwsh 7+ 無法實測，留待下一輪真機驗證。
        if ($PSVersionTable.PSVersion.Major -lt 6) {
            git clone --depth 1 --quiet $gitUrl $sourceDir 2>$null
        } else {
            git clone --depth 1 --quiet $gitUrl $sourceDir 2>&1 | Out-Null
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ 無法連線到 GitHub 倉庫" -ForegroundColor Red
            if (-not $UseSSH -and -not $Token) {
                Write-Host "   若為私有倉庫，請使用 -SSH 或 -Token YOUR_PAT 選項" -ForegroundColor Yellow
            } elseif ($UseSSH) {
                Write-Host "   請確認 SSH Key 已正確設定" -ForegroundColor Yellow
            } else {
                Write-Host "   請確認 PAT Token 是否有效且具有 repo 權限" -ForegroundColor Yellow
            }
            if ($tempDir -and (Test-Path $tempDir)) { Remove-Item -Recurse -Force $tempDir }
            exit 1
        }

        # Check if version directory exists
        $versionPath = Join-Path $sourceDir $aisdlcDir
        if (-not (Test-Path $versionPath)) {
            Write-Host "❌ 找不到版本 v$TargetVersion" -ForegroundColor Red
            Write-Host "   可用版本:" -ForegroundColor Yellow
            # SDD 模式目錄命名為 AISDLC_SDD_v*，非 SDD 模式為 AISDLC_v*——固定用後者
            # 過濾會使 -SDD 模式印出空清單（R16 相容性掃描）
            $fallbackFilter = if ($UseSDD) { "AISDLC_SDD_v*" } else { "AISDLC_v*" }
            Get-ChildItem $sourceDir -Directory -Filter $fallbackFilter | ForEach-Object {
                $vName = $_.Name -replace $fallbackFilter.TrimEnd('*'), ""
                Write-Host "   - v$vName"
            }
            Remove-Item -Recurse -Force $tempDir
            exit 1
        }

        Write-Host "✅ 下載完成" -ForegroundColor Green
    }

    # Copy to target directory
    Write-Host "⏳ 複製 AISDLC v$TargetVersion 到專案目錄..." -ForegroundColor Yellow

    # Create target directory if not exists
    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }

    # Copy AISDLC version directory
    $destPath = Join-Path $TargetDir $aisdlcDir
    $srcVersionPath = Join-Path $sourceDir $aisdlcDir
    Copy-Item -Path $srcVersionPath -Destination $destPath -Recurse -Force

    # Copy PROJECT_CLAUDE_Template.md as project CLAUDE.md
    $claudeTemplatePath = Join-Path $sourceDir (Join-Path $aisdlcDir "tools\PROJECT_CLAUDE_Template.md")
    $claudeDestPath = Join-Path $TargetDir "CLAUDE.md"
    if (Test-Path $claudeTemplatePath) {
        Copy-Item -Path $claudeTemplatePath -Destination $claudeDestPath -Force
        Write-Host "   ✅ 產生 CLAUDE.md (from PROJECT_CLAUDE_Template.md)" -ForegroundColor Green
    } elseif (Test-Path (Join-Path $sourceDir "CLAUDE.md")) {
        Copy-Item -Path (Join-Path $sourceDir "CLAUDE.md") -Destination $TargetDir -Force
        Write-Host "   ⚠️  複製 CLAUDE.md (fallback: root CLAUDE.md)" -ForegroundColor Yellow
    }

    # Copy .claude/skills/ to project root (Claude Code Skills discovery)
    $skillsSrcPath = Join-Path $destPath ".claude\skills"
    if (Test-Path $skillsSrcPath) {
        $skillsDestPath = Join-Path $TargetDir ".claude\skills"
        New-Item -ItemType Directory -Path $skillsDestPath -Force | Out-Null
        Copy-Item -Path "$skillsSrcPath\*" -Destination $skillsDestPath -Recurse -Force
        Write-Host "   ✅ 複製 .claude/skills/ (Claude Code Skills)" -ForegroundColor Green
    }

    Write-Host "✅ 複製完成" -ForegroundColor Green

    # Cleanup temp directory if used
    if ($tempDir -and (Test-Path $tempDir)) {
        Remove-Item -Recurse -Force $tempDir
    }

    Write-Host ""
}

function New-DocsDirectories {
    param(
        [string]$BaseDir
    )

    Write-Host "⏳ 建立 docs/ 標準子目錄..." -ForegroundColor Yellow

    # 定義標準子目錄（開發專注版）
    $docsDirs = @(
        "docs\01_requirements",
        "docs\02_architecture",
        "docs\03_testing",
        "docs\04_planning",
        "docs\05_development",
        "docs\06_quality",
        "docs\07_design",
        "docs\08_deployment"
    )

    $createdCount = 0
    $existingCount = 0
    $targetPath = $BaseDir

    foreach ($dir in $docsDirs) {
        $fullPath = Join-Path $targetPath $dir
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Host "   ✅ 建立 $dir\" -ForegroundColor Green
            $createdCount++
        } else {
            Write-Host "   ℹ️  $dir\ 已存在" -ForegroundColor Blue
            $existingCount++
        }
    }

    Write-Host ""
    Write-Host "📊 統計結果:" -ForegroundColor Green
    Write-Host "   - 已存在: $existingCount 個目錄"
    Write-Host "   - 新建立: $createdCount 個目錄"
    Write-Host ""
}

function Show-CompletionMessage {
    param(
        [string]$TargetDir,
        [string]$TargetVersion
    )

    $aisdlcDir = if ($UseSDD) { "AISDLC_SDD_v$TargetVersion" } else { "AISDLC_v$TargetVersion" }
    $claudeMdExists = Test-Path (Join-Path $TargetDir "CLAUDE.md")

    Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ✅ 初始化完成！                           ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 已完成的工作:" -ForegroundColor Blue
    if ($LocalSource) {
        Write-Host "   ✅ 從本地複製 AISDLC v$TargetVersion"
    } else {
        Write-Host "   ✅ 從 GitHub 下載 AISDLC v$TargetVersion"
    }
    Write-Host "   ✅ 複製框架到 $TargetDir\$aisdlcDir\"
    Write-Host "   ✅ 建立 docs\ 標準子目錄"
    if ($claudeMdExists) {
        Write-Host "   ✅ 複製 CLAUDE.md 設定檔"
    }
    $skillsExists = Test-Path (Join-Path $TargetDir ".claude\skills")
    if ($skillsExists) {
        Write-Host "   ✅ 部署 .claude/skills/ (Claude Code Skills)"
    }
    Write-Host ""
    Write-Host "📝 下一步:" -ForegroundColor Yellow
    Write-Host "   1. 使用 Claude Code 開啟目錄: $TargetDir"
    if ($UseSDD) {
        Write-Host "   2. 閱讀 $aisdlcDir\AISDLC_SDD_INIT.md 了解 SDD 框架使用"
        Write-Host "   3. 選擇場景：greenfield / brownfield / refactoring / documentation"
        Write-Host "   4. 確認 SCG 閘門：參考 $aisdlcDir\workflow\sdd-spec-first-gate\"
        Write-Host "   5. 開始規格設計（PRD 先行）：docs\01_requirements\"
    } else {
        Write-Host "   2. 閱讀 $aisdlcDir\AISDLC_INIT.md 了解框架使用"
        Write-Host "   3. PRD 寫入 docs\01_requirements\"
        Write-Host "   4. SRD 寫入 docs\02_architecture\"
        Write-Host "   5. 參考: $aisdlcDir\guides\user\onboarding\QUICK_START_GUIDE.md"
    }
    Write-Host ""
    Write-Host "🔗 專案結構:" -ForegroundColor Cyan
    Write-Host "   $TargetDir\"
    Write-Host "   ├── $aisdlcDir\          # AISDLC 框架"
    Write-Host "   │   ├── agent\              # AI Agent 定義"
    Write-Host "   │   ├── workflow\           # 工作流程"
    Write-Host "   │   ├── docs_template\      # 文件模板"
    Write-Host "   │   ├── guides\             # 參考指南"
    Write-Host "   │   └── AISDLC_INIT.md      # 框架入口"
    Write-Host "   ├── docs\                   # 📄 您的專案文件放這裡"
    Write-Host "   │   ├── 01_requirements\"
    Write-Host "   │   ├── 02_architecture\"
    Write-Host "   │   └── ..."
    Write-Host "   ├── .claude/skills/         # Claude Code Skills"
    Write-Host "   └── CLAUDE.md               # Claude Code 設定"
    Write-Host ""
}

# ===== 主程式 =====

function Main {
    # Show help if requested
    if ($Help) {
        Show-Banner
        Show-Usage
        exit 0
    }

    # Resolve target directory to absolute path
    $targetDir = $Dir
    if ($targetDir -eq ".") {
        $targetDir = Get-Location
    } else {
        # Create if not exists for path resolution
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        $targetDir = Resolve-Path $targetDir
    }

    Show-Banner

    # 自動偵測本地框架（如果未手動指定 -Local）
    if (-not $LocalSource) {
        Find-LocalFramework | Out-Null
    }

    Write-Host "📦 安裝配置:" -ForegroundColor Blue
    Write-Host "   版本: v$Version"
    Write-Host "   目錄: $targetDir"
    if ($LocalSource) {
        Write-Host "   來源: 本地 ($LocalSource)"
    } elseif ($SSH.IsPresent) {
        Write-Host "   來源: GitHub (SSH)"
    } elseif ($Token) {
        Write-Host "   來源: GitHub (HTTPS + PAT)"
    } else {
        Write-Host "   來源: GitHub (HTTPS)"
    }
    Write-Host ""

    Test-Dependencies
    Get-AISDLC -TargetVersion $Version -TargetDir $targetDir -UseSSH $SSH.IsPresent
    New-DocsDirectories -BaseDir $targetDir
    Show-CompletionMessage -TargetDir $targetDir -TargetVersion $Version
}

# 執行主程式
Main
