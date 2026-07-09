# ONBOARDING — 雙平台（macOS ⇄ Windows）開發環境設定

> 本檔是「剛從 GitHub clone 下來、要開始用 Claude Code 開發」的第一站。
> 目標：**同一份 repo 在 macOS 與 Windows 都能零隔閡開發**。回覆語言規範見 [CLAUDE.md](CLAUDE.md)（一律繁體中文）。

本 repo 是**雙專案 monorepo**：`AutoClaude`（Python 執行引擎）+ `AISDLC_SDD`（SDD 方法論框架）。詳見 [CLAUDE.md](CLAUDE.md)。

---

## 1. 前置需求（兩平台共通）

| 需求 | 說明 |
|------|------|
| **Python ≥ 3.11** | 版本鎖定於 [.python-version](.python-version)（`3.11`，對齊 CI 與 Docker）。**系統內建的舊 Python（如 macOS 的 3.9）不夠**。 |
| **Git** | 已 clone 本 repo。行尾政策由 [.gitattributes](.gitattributes) 自動處理（見 §5）。 |
| Docker（選用） | 只有要跑 `run_act` / PG 契約測 / nightly mutation 時才需要。 |
| Java（選用） | 只有要跑 AISDLC_SDD 的 TLA+/TLC 形式化驗證時才需要。 |

安裝 Python 3.11：
- **macOS**：`brew install python@3.11`
- **Windows**：`winget install Python.Python.3.11`（或用 pyenv-win）
- 兩平台皆可改用 [uv](https://docs.astral.sh/uv/)（bootstrap 會自動偵測並加速）：
  - macOS：`curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows：`winget install astral-sh.uv`

---

## 2. 一鍵設定（bootstrap）

在 repo 根目錄執行：

**macOS / Linux**
```bash
bash tools/bootstrap.sh
```

**Windows（PowerShell）**
```powershell
powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
```

bootstrap 會：① 檢查 Python ≥3.11 → ② 建立 `.venv`（有 uv 就用 uv 加速）→ ③ 安裝 AutoClaude（editable, `[dev,notifications,lint]`，含 import-linter，`lint-imports` 出廠即可用）+ AISDLC_SDD CI 依賴 → ④ 印出後續指引。git hooks 另以 §6 對照表的安裝腳本設定（任一支即可，兩子專案閘門同時生效，見 §6 dispatcher 說明）。

---

## 3. 啟用 venv（🔴 每個新終端機、每次開發前）

**macOS / Linux**
```bash
source .venv/bin/activate
```

**Windows（PowerShell）**
```powershell
.venv\Scripts\Activate.ps1
```

**為什麼一定要啟用**：本 repo 的 Claude Code hooks 與大量腳本使用裸 `python` 指令。macOS 系統只有 `python3`、沒有 `python`；啟用 `.venv` 後 `python` 在**兩平台都存在於 PATH**，所有 hooks / 腳本（含 30 個凍結版 SDD hooks）才能原樣運作。

---

## 4. 啟動 Claude Code（重要）

- **CLI**：先在終端機 `source .venv/bin/activate`（Mac）或 `Activate.ps1`（Windows），**再**啟動 `claude`。這樣 hooks 子行程才繼承到 venv 的 `python`。
- **VSCode 擴充**：右下角 Python 直譯器選 `.venv`；整合終端機會自動啟用 venv。

驗證 hooks 正常（未報 `python not found`）：重開一個 session，SessionStart 若印出 `[SDD-ROUTER] SDD 治理 hooks 休眠中…` 即為正常（純 AutoClaude 工作時 hooks 本應休眠）。要對 SDD 框架做 dogfooding 時才 `export SDD_ACTIVE_VERSION=<版本號>`（值＝當前最新版號，一律以 [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md) 為唯一真相源；本文撰寫時為 `0.30`）。

---

## 5. 常見雷區對照（Windows 開發者初到 macOS，或反向）

| 現象 | 原因 | 解法 |
|------|------|------|
| 每個工具呼叫都報 `python: command not found` | macOS 無 `python`，只有 `python3` | 啟用 `.venv`（§3）；勿改 hooks 的裸 `python` |
| `pip install` 失敗、要求 ≥3.11 | 系統 Python 太舊 | 裝 Python 3.11（§1），重跑 bootstrap |
| `.sh` 腳本報 `$'\r': command not found` | Windows 曾把 `.sh` 存成 CRLF | [.gitattributes](.gitattributes) 已強制 `.sh=LF`；重新 checkout 或 `git add --renormalize <file>` |
| `tools\xxx.ps1` 在 macOS 跑不了 | PowerShell 腳本是 Windows 專屬 | 用對應的 `.sh`（見 §6 對照表） |
| cd 進 repo 後 pyenv shim 報 `version 3.11 is not installed` | [.python-version](.python-version) 只寫兩位版號 `3.11`：uv 與 Windows `py` launcher 原生支援，但 **pyenv 需 ≥ 2.4** 才支援前綴解析（pyenv-win 視版本而定） | 升級 pyenv ≥ 2.4；或先 `pyenv install 3.11.x` 並確保該版可被解析；或改用 uv |
| 文件裡的路徑是 `d:\CursorProject\...` | 文件在 Windows 上撰寫 | 純說明性路徑，忽略即可；實際指令請用相對路徑 |

---

## 6. 工具腳本雙平台對照

| 用途 | Windows | macOS / Linux |
|------|---------|---------------|
| 環境設定 | `tools\bootstrap.ps1` | `tools/bootstrap.sh` |
| AutoClaude 本機 CI 閘門 | `AutoClaude\tools\local_ci_gate.ps1` | `AutoClaude/tools/local_ci_gate.sh` |
| 裝 AutoClaude git hooks ※ | `AutoClaude\tools\install_git_hooks.ps1` | `AutoClaude/tools/install_git_hooks.sh` |
| act 跑真 CI（Docker） | `AutoClaude\tools\run_act.ps1` | `AutoClaude/tools/run_act.sh` |
| 整合層閘門 | `tools\integration_gate.ps1` | `tools/integration_gate.sh` |
| AISDLC_SDD 本機閘門 | `AISDLC_SDD\scripts\ci-gate.ps1` ⚠️（僅 v0.01 基線，見下） | `AISDLC_SDD/scripts/ci-gate.sh`（既有） |
| 裝 AISDLC_SDD git hooks ※ | `AISDLC_SDD\scripts\install-hooks.ps1` | `AISDLC_SDD/scripts/install-hooks.sh`（既有） |

> ⚠️ **`ci-gate.ps1` 不是 `ci-gate.sh` 的完整對等**：ps1 僅測 v0.01 凍結基線（3 stage）；`.sh` 測「凍結基線 v0.01 ＋ LATEST（動態最高版）＋ `scripts/tests/` 共享 infra ＋ 多項 lint 硬閘」。Windows 上要拿完整閘門綠燈，請於 Git Bash（Git for Windows 內建）執行 `bash scripts/ci-gate.sh`。

※ **git hooks 注意（monorepo，根層 dispatcher 架構）**：本 repo 是單一 git repo，`core.hooksPath` 只有一個值——現統一指向**根層 `tools/git-hooks/`**（pre-commit + pre-push dispatcher；以 worktree 根解析為**絕對路徑**）。上表四支安裝腳本（AutoClaude 與 AISDLC_SDD 各 `.sh`/`.ps1`）**任一支皆設定同一個根層 dispatcher，兩子專案閘門同時生效**——裝一次即可，舊的「兩子專案互斥擇一」已廢除。dispatcher 依 commit/push 涉及的路徑自動分流：`AutoClaude/` 變更 → AutoClaude hooks；`AISDLC_SDD/` 變更 → AISDLC_SDD pre-push；判定不了則 fail-safe 全跑。

---

## 7. 常用驗證指令

```bash
# AutoClaude（在 AutoClaude/ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試
PYTHONUTF8=1 lint-imports             # 架構約束（8 kept / 0 broken）

# AISDLC_SDD（在 AISDLC_SDD/ 下）
bash scripts/ci-gate.sh               # 本機 CI 閘門（pytest + arch_fitness）
```

> 註：bootstrap 出廠環境（未裝 `[postgres]` 等選配）full pytest 實測基線約 **3,528~3,529 passed / 181~182 skipped**（總數 3,710；passed/skipped 邊界差 ±個位數，視外部工具與選配依賴現況而定）；skipped 比 AutoClaude/CLAUDE.md 基線 122 多出的部分全為選配依賴缺席（PG DSN 未設／sqlalchemy 與 `[postgres]` 未裝／claude_agent_sdk 未裝），屬預期，非測試退化。

---

## 8. Nightly 排程層（跨平台現況與後續）

AutoClaude 有一套 nightly 取證流程（mutation / pg-e2e / perf / drift）。**目前排程自動化僅實作 Windows 版**：

- **Windows（既有，可用）**：`AutoClaude/tools/run_local_nightly.ps1` 由 Windows 工作排程器 `schtasks` 每日 02:00 觸發（任務名 `AutoClaude_Nightly`）。設定校正見 `AutoClaude/tools/fix_nightly_catchup.ps1`。
- **macOS（尚未自動化，本輪擱置）**：`schtasks` 在 macOS 無對應；等價機制是 `launchd`（推薦）或 `cron`。762 行的 `run_local_nightly.ps1` 尚未移植成 `.sh`。

> ⚠️ **明確標示未完成**：macOS nightly 自動化（`run_local_nightly.sh` + launchd/cron）為**後續工作**，本輪未實作。開發迴圈本身（測試 / lint / ci-gate / 整合閘門）在 macOS 已完全對等。整個 ops 排程家族（`g0_gate_check.ps1`、`reschedule_g0_gatecheck.ps1`、`fix_nightly_catchup.ps1`、`run_local_nightly.ps1`）皆屬 Windows-only、無 `.sh` 對等，均涵蓋於本節「排程自動化僅 Windows」的明示缺口。

macOS 若要手動或半自動跑 nightly，可先參考以下 `launchd` 範本（待 `.sh` 版就緒後啟用）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- ~/Library/LaunchAgents/com.autoclaude.nightly.plist（範本；待 run_local_nightly.sh 就緒）-->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.autoclaude.nightly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/absolute/path/to/AISDCL_Agent/AutoClaude/tools/run_local_nightly.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/autoclaude_nightly.log</string>
  <key>StandardErrorPath</key><string>/tmp/autoclaude_nightly.err</string>
</dict>
</plist>
```
安裝（範本）：`launchctl load ~/Library/LaunchAgents/com.autoclaude.nightly.plist`

或 cron：`0 2 * * * /bin/bash /absolute/path/.../run_local_nightly.sh`
