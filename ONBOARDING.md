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

bootstrap 會：① 檢查 Python ≥3.11 → ② 建立 `.venv`（有 uv 就用 uv 加速）→ ③ 安裝 AutoClaude（editable, `[dev,notifications,lint]`，含 import-linter，`lint-imports` 出廠即可用）+ AISDLC_SDD CI 依賴 → ④ 印出後續指引。git hooks 另以 §6 對照表的安裝腳本設定（任一支即可，兩子專案閘門同時生效，見 §6 dispatcher 說明）。讀取 [.python-version](.python-version) 時，三段版號（如 `3.11.9`）會自動截為 major.minor 比對，新建 `.venv` 選定直譯器與 pinned 版本不一致時印警告（`.sh`/`.ps1` 兩版對等）；既有 `.venv` 一律沿用、不做版本檢查（需重建請先刪除 `.venv`）。

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

- **CLI**：先在終端機 `source .venv/bin/activate`（Mac）或 `Activate.ps1`（Windows），**再**於 **monorepo 根目錄**啟動 `claude`。這樣 hooks 子行程才繼承到 venv 的 `python`；勿於子目錄啟動——根層 `.claude/settings.json` 的 hooks 以相對路徑解析（Windows cmd 不展開 `${VAR}` 的相容性取捨），cwd 非專案根時會靜默失效。
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
| Windows `git pull` 後 `AISDLC_SDD/.claude/settings.local.json` 從工作樹消失 | 該檔已出庫（gitignore），倉內僅留 example | 複製同目錄 `settings.local.json.example` 為 `settings.local.json`（本機個人設定，之後不會再被 git 動到） |
| cd 進 repo 後 pyenv shim 報 `version 3.11 is not installed` | [.python-version](.python-version) 只寫兩位版號 `3.11`：uv 與 Windows `py` launcher 原生支援，但 **pyenv 需 ≥ 2.4** 才支援前綴解析（pyenv-win 視版本而定） | 升級 pyenv ≥ 2.4；或先 `pyenv install 3.11.x` 並確保該版可被解析；或改用 uv |
| 全新 Windows 11 跑 `.venv\Scripts\Activate.ps1` 報「因為這個系統上已停用指令碼執行」 | Windows 預設 `ExecutionPolicy=Restricted` 擋所有 `.ps1`（bootstrap 本身以 `-ExecutionPolicy Bypass` 呼叫故能跑，**只有日常啟用 venv 會卡**） | 一次性放行：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
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

> ℹ️ **bash-only 工具（無 `.ps1` 對等）**：`AISDLC_SDD/scripts/act-ci.sh`、`AISDLC_SDD/scripts/copy_on_evolve.sh`、`AISDLC_SDD/scripts/pytest_passed_count.sh`、`AutoClaude/tools/run_mutmut_in_docker.sh`、`AutoClaude/tools/sd06_w3_staging_dryrun.sh`、各版 `tools/verify_traceability.sh` —— Windows 上以 Git Bash 執行（`bash xxx.sh`）。

※ **git hooks 注意（monorepo，根層 dispatcher 架構）**：本 repo 是單一 git repo，`core.hooksPath` 只有一個值——現統一指向**根層 `tools/git-hooks/`**（**三支 hook**：pre-commit + pre-push dispatcher ＋ post-commit advisory 委派器；以主 checkout 根解析為**絕對路徑**）。上表四支安裝腳本（AutoClaude 與 AISDLC_SDD 各 `.sh`/`.ps1`）**任一支皆設定同一個根層 dispatcher，兩子專案閘門同時生效**——裝一次即可，舊的「兩子專案互斥擇一」已廢除；安裝腳本會驗證三支 hook 檔齊備才回報成功。dispatcher 依 commit/push 涉及的路徑自動分流：`AutoClaude/` 變更 → AutoClaude hooks；`AISDLC_SDD/` 變更 → AISDLC_SDD pre-push。

- **※ repo 搬移／改名後 hooks 靜默失效（QA 實證）**：`core.hooksPath` 寫的是絕對路徑，整個 repo 目錄搬移或改名後 git 找不到 dispatcher，**不會報錯、閘門直接全滅**。搬移後**必須重跑任一支安裝腳本**。四支閘門腳本（`local_ci_gate.sh/.ps1`、`integration_gate.sh/.ps1`）開頭已內建 **hooks liveness 偵測**：hooksPath 未設定／與預期不符／目錄不存在時印醒目警告（不 fail；CI 環境自動跳過）。
- **linked worktree**：四支安裝腳本在 linked worktree 內執行（含 `--uninstall`）一律**拒絕並 exit 1**——`core.hooksPath` 寫入共享 `.git/config`，在 worktree 內安裝會毒化主 checkout。請在**主 checkout** 安裝一次；hooks 執行期以 `git rev-parse --show-toplevel` 動態定位，之後在任何 worktree 內 commit/push 都自動對該 worktree 的樹生效。
- **post-commit 委派器**：`core.hooksPath` 一經設定，git 對所有 hook 種類只查 dispatcher 目錄，原裝在 `.git/hooks/post-commit` 的機制（如 AISDLC_SDD 框架 R-9.17.1 drift 告警）會整族靜默失效——故 dispatcher 第三支 `post-commit` 轉呼叫共享 `.git/hooks/post-commit`，advisory 語意（無論結果 exit 0）。
- **fail-safe / fail-loud 語意**：pre-push 收到**空 stdin**（如被 pre-commit 框架 shim 吃掉）＝fail-safe **兩子專案閘門全跑**；pre-commit 的 `git diff` 失敗亦 fail-safe 全跑；刪除遠端分支（zero push）維持跳過。分流**命中**但對應子 hook 檔缺失 → **fail-loud rc=1 擋下**（不靜默放行）。大型 commit/push（>64KB 變更清單）已修復 SIGPIPE 缺陷，不再靜默漏跑。
- **已知縫隙**：merge / rebase 自動產生的 commit 天然繞過 pre-commit 家族（git 行為，非本 repo 缺陷），由 pre-push 兜底把關。另一縫隙「rename 移出子專案 fail-open」（`git mv AutoClaude/x docs/x` 時 rename 偵測只列新路徑、來源子專案閘門靜默漏跑）已於四方複審第三輪修復——dispatcher diff 加 `--no-renames`（DEF-101-008）。
- **pre-commit 新增兩道閘（四方複審第三輪，commit 可能因此被攔的新原因）**：① **NTFS 檔名閘**——新增檔名含 Windows 不允許字元（`< > : " | ? *`／控制字元）、保留裝置名（CON/PRN/AUX/NUL/COM1~9/LPT1~9）、尾隨空白/句點、或與既有路徑僅大小寫不同（NTFS 碰撞）會被 rc=1 擋下，改名後重新暫存即可（DEF-101-011）；② **根層基建 leg**——commit 涉及根層 `tools/`、`.github/`、`.gitattributes`、`.editorconfig` 時，對變更到的 `.sh`／無副檔名 hook 檔跑 `bash -n` 語法檢查，語法錯誤擋下（DEF-101-012）。
- **執行權限政策**：「755 入庫」範圍**僅指 `tools/git-hooks/` 的 hook 檔**（git 直接執行）；其他 `.sh` 工具一律以 `bash xxx.sh` 呼叫，不依賴 executable bit。

### 6.1 CI workflows（GitHub Actions，根層接線）

兩子專案的 workflows 已全數集中於 **monorepo 根層 `.github/workflows/`**（接線已完成，push 後於 GitHub 生效）：

| 根層新檔名 | 原位置（已 git mv） |
|-----------|--------------------|
| `autoclaude-ci.yml` | `AutoClaude/.github/workflows/ci.yml` |
| `autoclaude-mutation-on-change.yml` | `AutoClaude/.github/workflows/mutation-on-change.yml` |
| `autoclaude-pg-e2e-on-label.yml` | `AutoClaude/.github/workflows/pg-e2e-on-label.yml` |
| `aisdlc-sdd-ci.yml` | `AISDLC_SDD/.github/workflows/ci.yml` |
| `aisdlc-sdd-arch-fitness.yml` | `AISDLC_SDD/.github/workflows/arch-fitness.yml` |
| `aisdlc-sdd-artifact-cleanup.yml` | `AISDLC_SDD/.github/workflows/artifact-cleanup.yml` |
| `aisdlc-sdd-drift-daily.yml` | `AISDLC_SDD/.github/workflows/drift-daily.yml` |
| `aisdlc-sdd-fsm-chaos-nightly.yml` | `AISDLC_SDD/.github/workflows/fsm-chaos-nightly.yml` |
| `root-infra-ci.yml` | （四方複審第三輪新增，非遷移）根層基建守門：paths＝`tools/**`、`.gitattributes`、`.editorconfig`、`.github/workflows/**`、`.github/dependabot.yml` 觸發，bash -n＋pwsh parse＋EOL 三道檢查（DEF-101-012） |

`dependabot.yml` 與 `.actrc` 亦已上移根層；`run_act`（AutoClaude 側）與 `act-ci.sh`（AISDLC_SDD 側）現於 **monorepo 根**執行、讀根層 `.actrc`。

---

## 7. 常用驗證指令

```bash
# AutoClaude（在 AutoClaude/ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試
PYTHONUTF8=1 lint-imports             # 架構約束（8 kept / 0 broken）

# AISDLC_SDD（在 AISDLC_SDD/ 下）
bash scripts/ci-gate.sh               # 本機 CI 閘門（pytest + arch_fitness）
```

> 註：bootstrap 出廠環境（未裝 `[postgres]` 等選配）full pytest 實測基線約 **3,528~3,529 passed / 181~182 skipped**（總數 3,710；passed/skipped 邊界差 ±個位數，視外部工具與選配依賴現況而定；與根層 CLAUDE.md 記載的 2026-07-09 實測基線 3,529 / 181 一致）；skipped 中屬選配依賴缺席者（PG DSN 未設／sqlalchemy 與 `[postgres]` 未裝／claude_agent_sdk 未裝）為預期，非測試退化。

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

---

## 9. 已知缺口（known-gap，凍結版豁免與平台限制）

| 缺口 | 影響 | 緩解 |
|------|------|------|
| **凍結版 47 支 ps1 無 UTF-8 BOM**：`AISDLC_SDD_v0.01~v0.29` 的 `run_tlc.ps1`（29 支）+ `v0.12~v0.29` 的 `install_post_commit.ps1`（18 支） | 含非 ASCII 字元且無 BOM，zh-TW Windows PowerShell 5.1 直跑會 parser 斷裂 | 改用 **v0.30 對應檔**（已補 BOM）；凍結版依紀律不回改 |
| **凍結版 `verify_traceability.sh` 用 `declare -A`**（v0.01~v0.29） | macOS 內建 bash 3.2 不支援關聯陣列，**必炸** | 用 **v0.30 同檔**（已改 bash 3.2 相容），或 `brew install bash` 後以新 bash 執行 |
| **macOS `keyboard` 套件熱鍵（ESC+F12）需「輔助使用」權限** | 未授權時 hotkey 背景執行緒**靜默失效**（無錯誤訊息） | 系統設定 → 隱私權與安全性 → 輔助使用，把執行 AutoClaude 的終端機 App 加入允許清單（平台限制，無對應 DEF 條目） |
| **凍結版 v0.01 `sandbox_runner.py:252`／`tlc_runner.py:69` subprocess 無 encoding** | zh-TW Windows（cp950）下子程序輸出含中文可能 UnicodeDecodeError（v0.30 已補 `encoding="utf-8"`） | ci-gate `.sh`/`.ps1` 已設 `PYTHONUTF8=1`；凍結版依紀律不回改（DEF-101-019） |
| **v0.12~v0.29 中間凍結版 `test_closure_evidence.py` fixture 未清洗 GIT_DIR/GIT_WORK_TREE** | 僅「人工在中間版目錄帶敵意 env 手跑 pytest」的邊角情境可能誤操作真 repo（v0.30 已補 `_clean_git_env()`） | 閘門路徑不執行中間版＋hook 層已 `env -u` 清洗；凍結版依紀律不回改（DEF-101-020） |
| **mutation artifact 累積鏈 90 天上限**（GitHub retention 上限） | 連續 90 天無 token_guard 源碼變動觸發 → GitHub 側 `mutation-history` 過期、累積歸零重累 | Windows 本機 nightly 為另一獨立累積點（兩者互不同步）；限制已註記於 workflow 檔頭（DEF-101-021） |
| **`closure_evidence._run_git` 自身繼承呼叫端 env** | read-only git 查詢，理論上可被敵意 GIT_DIR 導向；實害受限 | 防線＝hook 層 `env -u` 清洗；縱深防禦（函式內自清）留待後續（DEF-101-022） |
| **根層基建 bash -n leg 檢查「工作樹版本」而非 staged blob** | staged 壞＋工作樹好的罕見組合會本機假綠入庫 | 雲端 `root-infra-ci.yml` 對 push 後內容機械攔回；與既有 ruff-on-worktree 慣例一致（DEF-101-025） |

> 對應缺陷帳本：前兩條＝[AutoSDD_Defect_Log.md](docs/06_quality/AutoSDD_Defect_Log.md) DEF-101-003／DEF-101-004（wontfix＋凍結版紀律）；末五條＝DEF-101-019／DEF-101-020（wontfix＋凍結版紀律）與 DEF-101-021／DEF-101-022／DEF-101-025（open）。另有 **DEF-101-005**（`verify_traceability.sh` 的 `set -e`＋grep 零命中提前靜默退出，所有 bash 版本皆然、v0.30 亦未修，**open** 待 RFC）與 **DEF-101-018**（ruff 存量 baseline 1,339 筆待分批清理，open；其「未鎖版跨機器漂移」根因 DEF-101-006 已 fixed@四方複審第三輪）非平台缺口、不列本表。
