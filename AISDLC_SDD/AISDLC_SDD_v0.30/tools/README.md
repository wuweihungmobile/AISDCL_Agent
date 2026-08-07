# AISDLC 工具目錄
# Tools Directory

**版本**: v0.01
**最後更新**: 2026-04-17
**安裝腳本版本**: v3.3-SDD

---

## 📂 目錄結構

```
tools/
├── README.md                        # 本文件
├── init_project.sh                  # 專案初始化腳本 (Mac/Linux) v3.2
├── init_project.ps1                 # 專案初始化腳本 (Windows PowerShell) v3.2
├── verify_traceability.sh           # 追溯鏈驗證工具 v1.0
├── AISDLC_CLAUDE_RULES.md           # AISDLC Claude Code 自動化規則配置
└── PROJECT_CLAUDE_Template.md       # 專案 CLAUDE.md 範本
```

---

## 🛠️ 現有工具說明

### 1. `init_project.sh` / `init_project.ps1` — 專案初始化腳本

**版本**: v3.3-SDD | **狀態**: ✅ 已完成

從 GitHub 下載並初始化 AISDLC-SDD 框架到目標專案目錄，自動完成以下工作：
- 下載 AISDLC-SDD 框架（指定版本）
- 建立 `docs/` 八大目錄結構（01-08）含 SDD 子目錄（adr/, api/, contracts/ 等）
- 部署 `.claude/skills/`（39 個 Claude Code Skills，含 6 個 SDD 新增）
- 生成專案 `CLAUDE.md`

**SDD 模式（v3.3 新增）**：
```bash
# SDD 模式：建立完整 SDD 目錄結構 + SDD 範本 + SCG 閘門文件
bash init_project.sh --sdd -d ~/my-project
```

**Windows PowerShell**：
```powershell
.\init_project.ps1 -SDD -Dir C:\Projects\MyApp
```

### 2. `verify_traceability.sh` — 追溯鏈驗證工具

**版本**: v1.0 | **狀態**: ✅ 已完成

掃描 `docs/` 目錄中的文檔，驗證 US/AC/AT/API ID 引用的完整性與一致性。

```bash
# 驗證 docs/ 追溯鏈
bash tools/verify_traceability.sh docs/

# 指定路徑
bash tools/verify_traceability.sh /path/to/docs/
```

### 3. `AISDLC_CLAUDE_RULES.md` — Claude Code 自動化規則

**狀態**: ✅ 已完成

AISDLC 框架的 Claude Code 強制規則配置。當 `AISDLC_INIT.md` 載入時自動套用，包含：
- 溝通語言規範（繁體中文）
- 文檔寫檔強制檢查清單
- 開發-編譯-測試循環規則
- Agent 自動載入規則

> 🔴 本檔案由 `tools/init_project.sh` 自動引用，**不可直接修改**（除非升版）。

### 4. `PROJECT_CLAUDE_Template.md` — 專案 CLAUDE.md 範本

**狀態**: ✅ 已完成

`init_project.sh` 在初始化時使用本範本生成目標專案的 `CLAUDE.md`，內含 AISDLC-SDD v0.01 的完整 Claude Code 指引，包含 SDD 三大支柱與 SCG 閘門說明。

---

## 🚀 快速安裝 AISDLC

### 方法 1：一行安裝（推薦）🌟

#### Mac / Linux

```bash
# 安裝到當前目錄
curl -fsSL https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.sh | bash

# 指定目標目錄
curl -fsSL https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.sh | bash -s -- -d ./my-project
```

#### Windows (PowerShell)

```powershell
# 安裝到當前目錄
irm https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.ps1 | iex

# 指定目標目錄
irm https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.ps1 -OutFile init.ps1
.\init.ps1 -Dir .\my-project
```

---

### 方法 2：私有倉庫安裝（SSH Key 或 PAT Token）

#### 使用 SSH Key (Mac/Linux)

```bash
bash init.sh --ssh -d ~/my-project
```

#### 使用 PAT Token (Mac/Linux)

```bash
curl -H "Authorization: token YOUR_GITHUB_PAT" -fsSL \
  https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.sh -o init.sh
bash init.sh --token YOUR_GITHUB_PAT -d ~/my-project
```

#### 使用 PAT Token (Windows PowerShell)

```powershell
$headers = @{ Authorization = "token YOUR_GITHUB_PAT" }
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/wuweihungmobile/AISDLC/main/AISDLC_SDD_v0.01/tools/init_project.ps1" `
  -Headers $headers -OutFile init.ps1
.\init.ps1 -Token YOUR_GITHUB_PAT -Dir C:\Projects\MyApp
```

---

### 方法 3：Clone 後安裝

```bash
git clone https://github.com/wuweihungmobile/AISDLC.git
cd AISDLC
```

#### Mac / Linux

```bash
# 🔴 用 `bash <script>` 而非裸跑 `./<script>`（與本檔第 39 行一致）：該檔在 git 索引裡
#    是 100644（非 100755），mac/Linux 上裸跑會得到 `Permission denied`（rc=126）。
#    在 Windows 上這件事看不見——`core.filemode=false` 讓檔案模式從不出現在
#    git status/diff 裡，所以這份文件在製造它的那台機器上永遠讀起來是對的。
bash AISDLC_SDD_v0.01/tools/init_project.sh -d ~/my-project        # 公開倉庫
bash AISDLC_SDD_v0.01/tools/init_project.sh -d ~/my-project --ssh  # 私有倉庫 SSH
bash AISDLC_SDD_v0.01/tools/init_project.sh -h                     # 查看說明
```

#### Windows (PowerShell)

```powershell
.\AISDLC_SDD_v0.01\tools\init_project.ps1 -Dir C:\Projects\MyApp         # 公開倉庫
.\AISDLC_SDD_v0.01\tools\init_project.ps1 -Dir C:\Projects\MyApp -SSH    # 私有倉庫 SSH
.\AISDLC_SDD_v0.01\tools\init_project.ps1 -Help                          # 查看說明
```

> 💡 **提示**: 方法 3 最穩定（本地已有框架，腳本自動偵測並跳過下載）

---

### 安裝完成後的目錄結構

```
您的專案目錄/
├── AISDLC_SDD_v0.01/              # AISDLC 框架（即專案工作目錄）
│   ├── AISDLC_INIT.md          # 框架入口，開始前必讀
│   ├── CLAUDE.md               # Claude Code 設定檔
│   ├── .claude/skills/         # 33 個 Claude Code Skills
│   ├── agent/                  # AI Agent 定義（21個）
│   ├── workflow/               # 工作流程（8核心+13情境）
│   ├── scenarios/              # 十大情境 SOP
│   ├── docs_template/          # 文檔模板
│   ├── guides/                 # 參考指南
│   └── docs/                   # 📄 您的專案文件放這裡
│       ├── 01_requirements/    # PRD, FRD, User Stories
│       ├── 02_architecture/    # SRD, API Specification
│       ├── 03_testing/         # Test Plan, Test Cases, Reports
│       ├── 04_planning/        # Roadmap, Estimation
│       ├── 05_development/     # Iteration Plans, Progress Logs
│       ├── 06_quality/         # Code Quality, Security, Performance
│       ├── 07_design/          # UI/UX, Database Design
│       └── 08_deployment/      # CI/CD, Release Notes
└── （其他專案檔案）
```

---

## 📋 規劃中工具 (v0.02+)

以下工具規劃於未來版本實作，目前均有對應的手動替代方案：

| 工具 | 說明 | 手動替代方案 | 計畫版本 |
|------|------|------------|---------|
| `aisdlc-lint` | 文檔完整性與 ID 格式檢查 | Document_Quality_Checklist.md | v0.10+ |
| `template-validator` | 驗證文檔是否符合模板結構 | docs_template/ 手動對照 | v0.10+ |
| `checkpoint-manager` | Session Checkpoint 儲存與恢復 | 手動記錄 | v0.10+ |
| `workflow-selector` | 互動式情境與 Workflow 選擇 | SCENARIO_SELECTOR.md | v0.10+ |

---

## 🔗 相關文檔

- [AISDLC_INIT.md](../AISDLC_INIT.md) - 框架入口（init_project.sh 安裝後的起點）
- [guides/user/onboarding/QUICK_START_GUIDE.md](../guides/user/onboarding/QUICK_START_GUIDE.md) - 5分鐘快速上手
- [FILE_DIRECTORY_RULES.md](../FILE_DIRECTORY_RULES.md) - 目錄與文件分類規則

---

**維護者**: AISDLC Framework Team
