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
| Docker（選用） | 只有要跑 `run_act` / PG 契約測 / nightly mutation 時才需要。**Windows 須確認 Docker Desktop 啟用 WSL2 backend**（預設值；仍在用 Hyper-V backend 的舊機器/公司鎖定環境請切換，否則 `run_act` 等容器操作可能無法正常啟動）。macOS（Apple Silicon）執行 `run_act` 時，`.actrc` 的 `--container-architecture linux/amd64` 會強制走 QEMU 模擬（刻意設計，貼近雲端 amd64 runner），預期較慢屬正常代價。 |
| Java（選用） | 只有要跑 AISDLC_SDD 的 TLA+/TLC 形式化驗證時才需要。建議 **JRE/JDK ≥ 11**（本機以 OpenJDK 21 實測 `tla2tools.jar` 正常運作；未測試更舊版本相容性下限，若遇到問題請優先升級 Java）。 |
| PowerShell（Windows） | Windows 11 內建 **Windows PowerShell 5.1**（`powershell.exe`）可執行本文件日常指令；CI（`root-infra-ci.yml`）的 `.ps1` 語法檢查則用 **PowerShell 7**（`pwsh`）。若頻繁遇到 BOM／編碼類雷區（見 §5），建議 `winget install Microsoft.PowerShell` 額外裝 pwsh 7。 |

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

bootstrap 會：① 檢查 Python ≥3.11 → ② 建立 `.venv`（有 uv 就用 uv 加速）→ ③ 安裝 AutoClaude（editable, `[dev,notifications,lint]`，含 import-linter，`lint-imports` 出廠即可用）+ AISDLC_SDD CI 依賴 → ④ 印出後續指引。git hooks 另以 §6 對照表的安裝腳本設定（任一支即可，兩子專案閘門同時生效，見 §6 dispatcher 說明）。讀取 [.python-version](.python-version) 時，三段版號（如 `3.11.9`）會自動截為 major.minor 比對，新建 `.venv` 選定直譯器與 pinned 版本不一致時印警告（`.sh`/`.ps1` 兩版對等）；既有 `.venv` 沿用前會先驗證**平台形狀**（POSIX 需 `bin/python`、Windows 需 `Scripts\python.exe`；跨平台共用工作目錄時以對方平台建的 `.venv` 會被 fail-fast 擋下並提示刪除重建），版本不做檢查（需重建請先刪除 `.venv`）。

### 2.1 每日開工一鍵啟動（dev_start — 自動偵測環境＋切換＋GitHub 同步）

bootstrap 是「第一次」；之後每次開工改用 **dev_start**，不需手動判斷「上次是不是在另一個平台開發」。全新機器也可以**直接**執行 dev_start（`.venv` 不存在時第④步會自動觸發 §2 bootstrap，且額外自動裝妥 git hooks）——§2 bootstrap 保留給只想單純建 venv、不需同步/hooks 自動化的場合：

**macOS / Linux**
```bash
source tools/dev_start.sh    # 推薦：完成後自動啟用 .venv（bash tools/dev_start.sh 亦可，結尾印啟用指引）
```

> ℹ️ 本指令需要互動式 shell 為 bash 或 zsh（使用 `source` builtin 與 bash 專屬語法）；純 POSIX `sh`/`dash` 不支援，常見於部分 Linux 最小化映像的預設 `/bin/sh`。

**Windows（PowerShell）**
```powershell
. tools\dev_start.ps1        # 推薦：dot-source，完成後自動啟用 .venv
```

> 🔴 **全新 Windows 首次前置**：預設 `ExecutionPolicy=Restricted` 會擋所有 `.ps1`（**含上行 dot-source**）。**唯一建議的一次性前置動作**：執行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`（詳見 §5 對照表；此操作**不需要**以系統管理員身分開啟 PowerShell，一般使用者權限即可）。
>
> `powershell -ExecutionPolicy Bypass -File tools\dev_start.ps1` **不是**上述放行的替代方案，僅適合單次、非互動、CI 風格執行（例如只是想立刻跑一次整備看結果）：此形態可跑整備但**不會自動啟用 venv**，而且**不會解除 ExecutionPolicy=Restricted 本身**——選這條路之後，日常要用的 `. tools\dev_start.ps1`（dot-source）與 §3 的 `.venv\Scripts\Activate.ps1` 仍會被同樣的「已停用指令碼執行」錯誤擋下，必須之後還是補做上面的一次性放行才能使用日常指令。
>
> 若已執行放行仍被擋：用 `Get-ExecutionPolicy -List` 檢查各 Scope——企業機器可能被 Group Policy 設定的 `MachinePolicy` 鎖定覆蓋，此時 `-Scope CurrentUser` 對此無效，需洽 IT 協助調整。

dev_start 七步驟（邏輯集中於 `tools/dev_start.py` 跨平台單一核心，`.sh`/`.ps1` 僅薄殼）：
① **環境偵測**（讀 gitignored 狀態檔 `.dev_env_state.json` 的上次開發平台 Developing vs 當前 Now）→ ② **GitHub 同步**（fetch + `--ff-only` pull；髒工作樹／分叉／離線一律明示不硬做，**絕不自動 stash／rebase／push**；未追蹤檔不擋同步）→ ③ **平台切換**（Developing≠Now 時清除含絕對路徑的 `.pytest_cache`/`.ruff_cache`）→ ④ **venv／依賴整備**（另一平台形狀的 `.venv` **換手保留**至 `.venv-cache-<flavor>/`，本平台快取存在則**秒級換回**；缺 `.venv` 或依賴檔（`pyproject.toml`/`requirements-ci.txt`）hash 變動 → 自動重跑 §2 bootstrap）→ ⑤ **git hooks 檢核**（`core.hooksPath` 未設／漂移 → 自動重跑安裝腳本，治 §6「搬移後 hooks 靜默全滅」）→ ⑥ **平台健檢**（Windows 自動設 `core.longpaths=true`）→ ⑦ **狀態寫回＋摘要**。

適用兩種拓撲：**共用工作目錄**（外接碟／同步資料夾，macOS ⇄ Windows 輪開同一份）由 ③④ 吸收全部切換成本；**雙機各自 clone** 則 ①③ 恆為「無切換」，由 ②④ 把另一台 push 的變更同步進來並保持依賴新鮮。旗標：`--no-sync`（離線跳過 ②）、`--force-bootstrap`（強制重裝依賴）。

> ⚠️ **mac⇄linux 例外**（Linux 為 macOS/Windows 之外自行延伸支援的第三平台）：venv 快取鍵僅分 `windows`/`posix` 兩桶，mac 與 Linux 同屬 `posix` 但二進位不相容，彼此切換時**無法秒級換手**，每次都會完整重跑一次 bootstrap（安全但較慢）；此例外不影響本節主要訴求的 macOS ⇄ Windows 雙平台切換。

補充：狀態檔 `.dev_env_state.json` 損毀時自動視為首次執行（可隨時安全刪除重生，只多付一次依賴基準記錄）；VSCode 使用者在**整合終端機**執行同指令即可（或把指令掛進 shell profile，開終端機即自動整備）。

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

**為什麼一定要啟用**：本 repo 的 Claude Code hooks 與大量腳本使用裸 `python` 指令。macOS 系統只有 `python3`、沒有 `python`；啟用 `.venv` 後 `python` 在**兩平台都存在於 PATH**，所有 hooks / 腳本（含全部 SDD 版本目錄的 hooks——版本清單／最新版號見 `AISDLC_SDD/FRAMEWORK_STATUS.md` 唯一真相源）才能原樣運作。

---

## 4. 啟動 Claude Code（重要）

- **CLI**：先在終端機 `source .venv/bin/activate`（Mac）或 `Activate.ps1`（Windows），**再**於 **monorepo 根目錄**啟動 `claude`。這樣 hooks 子行程才繼承到 venv 的 `python`，且根層 `.claude/settings.json` 的治理 hooks 才會載入（於子目錄啟動則根層 hooks 整組不載入）。hooks 指令已改以 python -c shim 錨定 `CLAUDE_PROJECT_DIR`（四方複審第四輪 P0 修復）：session 中即使 shell cwd 移到子目錄，hooks 仍正確解析；環境變數缺失時缺檔 fail-open（靜默失效，不再誤觸 PreToolUse deny 鎖死全部工具）。契約鎖：`AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py`。
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
| 全新 Windows 11 跑 `.venv\Scripts\Activate.ps1` 報「因為這個系統上已停用指令碼執行」 | Windows 預設 `ExecutionPolicy=Restricted` 擋所有 `.ps1`（bootstrap／dev_start 以 `-ExecutionPolicy Bypass -File` 呼叫可跑，但**日常啟用 venv 與 `. tools\dev_start.ps1` dot-source 都會被擋**，見 §2.1 前置） | 一次性放行：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| 文件裡的路徑是 `d:\CursorProject\...` | 文件在 Windows 上撰寫 | 純說明性路徑，忽略即可；實際指令請用相對路徑 |
| GUI 發起的 git commit（如 VSCode Source Control 按鈕）被 hooks 擋下：`python: command not found`（mac）或缺 ruff 的系統 Python（Windows） | GUI App 不繼承終端機 venv PATH，hooks fail-loud 擋下 | 從已啟用 venv 的終端機啟動編輯器（如 `code .`），或改用終端機 commit |
| Windows 上首次 `pip install`／`pytest` 異常緩慢 | Windows Defender 即時掃描大量小型 Python 檔案（`.venv`、`__pycache__`） | 非必要但建議：把 `.venv` 與本 repo 目錄加入 Defender 排除清單，可顯著加速 |
| 手動補裝套件時 `python -m pip ...` 報 `No module named pip` | `.venv` 是 bootstrap 偵測到 `uv` 時走 `uv venv` + `uv pip install` 建的，這種 venv **內部本來就沒有 `pip` 模組**（Mac/Windows 四方複審實機驗證重現） | 改用 `uv pip install -e .[...]`（uv 已安裝時對任何已啟用的 venv 皆可用）；完整警語見 [CLAUDE.md](CLAUDE.md)「AutoClaude — 常用指令與架構」§安裝/執行 與 [docs/AISDLC_Agent_UserGuide.md](docs/AISDLC_Agent_UserGuide.md) §1.2 |

---

## 6. 工具腳本雙平台對照

| 用途 | Windows | macOS / Linux |
|------|---------|---------------|
| 環境設定 | `tools\bootstrap.ps1` | `tools/bootstrap.sh` |
| 每日開工自動啟動（§2.1） | `. tools\dev_start.ps1` | `source tools/dev_start.sh` |
| AutoClaude 本機 CI 閘門 | `AutoClaude\tools\local_ci_gate.ps1` | `AutoClaude/tools/local_ci_gate.sh` |
| 裝 AutoClaude git hooks ※ | `AutoClaude\tools\install_git_hooks.ps1` | `AutoClaude/tools/install_git_hooks.sh` |
| act 跑真 CI（Docker） | `AutoClaude\tools\run_act.ps1` | `AutoClaude/tools/run_act.sh` |
| 整合層閘門 | `tools\integration_gate.ps1` | `tools/integration_gate.sh` |
| AISDLC_SDD 本機閘門 | `AISDLC_SDD\scripts\ci-gate.ps1`（偵測到 Git Bash 即薄委派 `ci-gate.sh`＝完整對等；無 Git Bash 才退回 v0.01 3-stage fallback 並警告，見下） | `AISDLC_SDD/scripts/ci-gate.sh`（既有） |
| 裝 AISDLC_SDD git hooks ※ | `AISDLC_SDD\scripts\install-hooks.ps1` | `AISDLC_SDD/scripts/install-hooks.sh`（既有） |

> ⚠️ **`ci-gate.ps1` 的覆蓋範圍取決於有無 Git Bash**：找得到 bash.exe（排除 WSL `System32\bash.exe`）時薄委派 `bash scripts/ci-gate.sh`，覆蓋與 `.sh` 完整對等（凍結基線 v0.01 ＋ LATEST 動態最高版 ＋ `scripts/tests/` 共享 infra ＋ 多項 lint 硬閘）；找不到才退回僅測 v0.01 的 3-stage fallback 並印黃色警告。Git for Windows 內建 Git Bash，正常安裝下皆走完整對等路徑。

> ℹ️ **bash-only 工具（無 `.ps1` 對等）**：`AISDLC_SDD/scripts/act-ci.sh`、`AISDLC_SDD/scripts/copy_on_evolve.sh`、`AISDLC_SDD/scripts/pytest_passed_count.sh`、`AutoClaude/tools/run_mutmut_in_docker.sh`、`AutoClaude/tools/sd06_w3_staging_dryrun.sh`、各版 `tools/verify_traceability.sh` —— Windows 上以 Git Bash 執行（`bash xxx.sh`）。

※ **git hooks 注意（monorepo，根層 dispatcher 架構）**：本 repo 是單一 git repo，`core.hooksPath` 只有一個值——現統一指向**根層 `tools/git-hooks/`**（**三支 hook**：pre-commit + pre-push dispatcher ＋ post-commit advisory 委派器；以主 checkout 根解析為**絕對路徑**）。上表四支安裝腳本（AutoClaude 與 AISDLC_SDD 各 `.sh`/`.ps1`）**任一支皆設定同一個根層 dispatcher，兩子專案閘門同時生效**——裝一次即可，舊的「兩子專案互斥擇一」已廢除；安裝腳本會驗證三支 hook 檔齊備才回報成功。dispatcher 依 commit/push 涉及的路徑自動分流：`AutoClaude/` 變更 → AutoClaude hooks；`AISDLC_SDD/` 變更 → AISDLC_SDD pre-push；**任何非兩子專案的根層路徑**（`tools/`、`docs/`、`.github/` 等）變更 → pre-push 另跑 **root-infra leg**（`py_compile` 全根層 Python（R10 起含 `.claude/hooks/`）＋`tools/tests` unittest（R10 起經 `tools/run_root_unittests.py`，含測試數量下限釘選——裸 discover 對「發現 0 個測試」回 rc=0 的 fail-open 已堵）＋四支守門工具 parity／NTFS／crossref／wrapper-thinness，R9 補上、R10 擴充，對齊 `root-infra-ci.yml` 的本地接線——先前純根層變更 push 一個閘門都不跑，CI 帳單停擺期間即為零防護）；另外，push 若命中**根層消費檔**（`aisdlc-sdd-ci.yml` paths 承認的非 `AISDLC_SDD/` 條目：NTFS 閘、根層 pre-commit、兩份 `.claude/settings.json`、`sdd_hook_router.py`——其回歸鎖住在 `AISDLC_SDD/scripts/tests/`）且 SDD leg 未觸發，pre-push 會補跑該回歸鎖（R10 ARCH-1：清單機械讀取該 yml，勿手抄第二份；功能行為由 `tools/tests/test_pre_push_dispatcher.py` 六情境鎖住、CI↔本地守門清單對應由 `test_root_infra_parity.py` 鎖住）。

- **※ repo 搬移／改名後 hooks 靜默失效（QA 實證）**：`core.hooksPath` 寫的是絕對路徑，整個 repo 目錄搬移或改名後 git 找不到 dispatcher，**不會報錯、閘門直接全滅**。搬移後**必須重跑任一支安裝腳本**。四支閘門腳本（`local_ci_gate.sh/.ps1`、`integration_gate.sh/.ps1`）開頭已內建 **hooks liveness 偵測**：hooksPath 未設定／與預期不符／目錄不存在時印醒目警告（不 fail；CI 環境自動跳過）。
- **linked worktree**：四支安裝腳本在 linked worktree 內執行（含 `--uninstall`）一律**拒絕並 exit 1**——`core.hooksPath` 寫入共享 `.git/config`，在 worktree 內安裝會毒化主 checkout。請在**主 checkout** 安裝一次；hooks 執行期以 `git rev-parse --show-toplevel` 動態定位，之後在任何 worktree 內 commit/push 都自動對該 worktree 的樹生效。**注意**：`.venv`／bootstrap 不隨 git worktree 共用——每個新建的 linked worktree 第一次執行本指令（`dev_start`）仍需完整跑一次 bootstrap（裝全部依賴），不是「一個指令、隨開隨用」的秒級體驗；僅 git hooks 設定會如實跳過並沿用主 checkout。
- **post-commit 委派器**：`core.hooksPath` 一經設定，git 對所有 hook 種類只查 dispatcher 目錄，原裝在 `.git/hooks/post-commit` 的機制（如 AISDLC_SDD 框架 R-9.17.1 drift 告警）會整族靜默失效——故 dispatcher 第三支 `post-commit` 轉呼叫共享 `.git/hooks/post-commit`，advisory 語意（無論結果 exit 0）。
- **fail-safe / fail-loud 語意**：pre-push 收到**空 stdin**（如被 pre-commit 框架 shim 吃掉）＝fail-safe **兩子專案閘門全跑**；pre-commit 的 `git diff` 失敗亦 fail-safe 全跑；刪除遠端分支（zero push）維持跳過。分流**命中**但對應子 hook 檔缺失 → **fail-loud rc=1 擋下**（不靜默放行）。大型 commit/push（>64KB 變更清單）已修復 SIGPIPE 缺陷，不再靜默漏跑。
- **已知縫隙**：merge / rebase 自動產生的 commit 天然繞過 pre-commit 家族（git 行為，非本 repo 缺陷），由 pre-push 兜底把關。另一縫隙「rename 移出子專案 fail-open」（`git mv AutoClaude/x docs/x` 時 rename 偵測只列新路徑、來源子專案閘門靜默漏跑）已於四方複審第三輪修復——dispatcher diff 加 `--no-renames`（DEF-101-008）。
- **pre-commit 新增兩道閘（四方複審第三輪，commit 可能因此被攔的新原因）**：① **NTFS 檔名閘**——新增檔名含 Windows 不允許字元（`< > : " | ? *`／控制字元）、保留裝置名（CON/PRN/AUX/NUL/COM0~9/LPT0~9，COM0/LPT0 比照業界防禦性實作採保守納入）、尾隨空白/句點、或與既有路徑僅大小寫不同（NTFS 碰撞）會被 rc=1 擋下，改名後重新暫存即可（DEF-101-011）；repo 相對路徑 **>200 字元**（code point 計，locale 無關）亦 rc=1 擋下、>180 預警——Windows MAX_PATH=260 保守閘，縮短檔名或目錄層級即可（DEF-101-039，四方複審第五輪）；② **根層基建 leg**——commit 涉及根層 `tools/`、`.github/`、`.gitattributes`、`.editorconfig` 時，對變更到的 `.sh`／無副檔名 hook 檔跑 `bash -n` 語法檢查，語法錯誤擋下（DEF-101-012）。
- **執行權限政策**：「755 入庫」範圍**僅指 `tools/git-hooks/` 的 hook 檔**（git 直接執行）；其他 `.sh` 工具一律以 `bash xxx.sh` 呼叫，不依賴 executable bit。
- **雙腳本對等機械守護**：上表四對 `.sh`/`.ps1`（bootstrap／integration_gate／local_ci_gate／run_act）的 step 標籤清單由 `tools/check_script_parity.py` 於 `root-infra-ci` 機械比對——改任一邊的 step 須同步另一邊，否則 CI 紅（R9 起標籤抽取同時接受單/雙引號，並釘選各對標籤數量下限，防「兩側同步改寫致標籤同時消失」的靜默縮面）。其餘兩對（install_git_hooks、AISDLC_SDD install-hooks）判定邏輯已收斂至 `tools/git_hooks_install_common.py` 單一真相源、殼層無可抽取的標籤錨點，**暫無標籤比對**——改任一邊須人工同步另一邊（明文侷限，見 check_script_parity.py docstring）。`dev_start` 對不在上述任一類——七步驟業務邏輯集中於跨平台單一核心 `tools/dev_start.py`，**無業務邏輯漂移面**；兩薄殼仍各有直譯器選擇／venv 啟用等樣板（無標籤錨點、暫無機械比對），改任一邊須人工同步另一邊。**薄殼退化守門**：`tools/check_wrapper_thinness.py`（`root-infra-ci` 步驟 10 具名執行＋步驟 8 unittest 覆蓋）守住「兩薄殼不再長回業務邏輯」——R10 改制為**正規化內容 hash 釘選**（權威判定：剝註解/空行後 sha256 對表，任何實質變動一律紅燈、指路更新釘選；黑名單曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過，降級為 hash 紅燈時的診斷輔助）＋行數上限第二訊號（拍板案(a)，DEF-101-134）。**成對腳本註冊完整性（enrollment 發現鎖，R10 同案）**：`check_script_parity.py` 掃描 `tools/`、`AutoClaude/tools/`、`AISDLC_SDD/scripts/` 下同名 `.sh`/`.ps1` 對，斷言每對必屬 {parity 標籤比對, thinness hash 釘選, 明文豁免（附帳本依據）} 之一且註冊清單無 stale——「新增成對腳本繞過守門」自此為機械攔截，不再只靠人工記得。

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
| `root-infra-ci.yml` | （四方複審第三輪新增，非遷移）根層基建守門：**全變更觸發**（NTFS 檔名閘須守任意路徑，paths 白名單必留盲區），現行**十道**輕量檢查（詳細內容以 workflow 檔頭註解為準，避免每次擴充都要同步改動兩處）——1. `bash -n`（根層 `tools/git-hooks/`＋`tools/*.sh`）；2. pwsh parse＋UTF-8 BOM（active `.ps1`：根層 `tools/`＋`AutoClaude/tools/`＋`AISDLC_SDD/scripts/`＋LATEST 版，凍結版排除）；3. EOL 守門（`.sh`，須為 LF）；4. EOL 守門（`.ps1`，反方向須為 CRLF，2026-07-13 補洞）；5. NTFS 檔名閘（`tools/check_ntfs_paths.py`，pre-commit NTFS 閘的 CI 對等）；6. 腳本對等閘（`tools/check_script_parity.py`：四對 `.sh`/`.ps1` step 標籤清單＋pytest 釘選三處同版）；7. `py_compile`（根層 `tools/` 下所有 `*.py` 語法檢查，dev_start 四方審查 P2）；8. `unittest`（`tools/tests/`，R10 起經 `tools/run_root_unittests.py` 執行、含測試數量下限釘選——裸 discover 對 0 個測試回 rc=0 的 fail-open 已堵；收斂 py_compile 守不到的邏輯回歸落差）；9. 缺陷帳本跨文件狀態一致（`tools/check_defect_log_crossref.py`）；10. wrapper 薄殼守門（`tools/check_wrapper_thinness.py`）（DEF-101-012、四方複審第四／五輪＋R8 擴充） |

| `windows-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）Windows 側執行級驗證：windows-smoke（bootstrap/dev_start/install 腳本/PS 5.1 專測/dispatcher 真實 commit 觸發）＋ windows-nightly-full（深度回歸）；本地補償對等＝`tools/windows_smoke_local.ps1`（R10） |
| `macos-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）macOS 側執行級驗證：macos-smoke（bash 3.2 直呼/安裝腳本/worktree/ci-gate 雙軌）＋ macos-nightly-full；本地補償對等＝`tools/macos_smoke_local.sh`（R9）。詳見 §8/§10 |

`.actrc` 亦已上移根層；`run_act`（AutoClaude 側）與 `act-ci.sh`（AISDLC_SDD 側）現於 **monorepo 根**執行、讀根層 `.actrc`。（Dependabot 已於 2026-07-12 完全停用並移除根層 `dependabot.yml`——單人 main-only 工作流不採自動相依 PR；GitHub 端 security updates／vulnerability alerts 亦為停用。相依更新改為日後手動盯版或重新啟用。）

---

## 7. 常用驗證指令

```bash
# AutoClaude（在 AutoClaude/ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試
PYTHONUTF8=1 lint-imports             # 架構約束（8 kept / 0 broken）

# AISDLC_SDD（在 AISDLC_SDD/ 下）
bash scripts/ci-gate.sh               # 本機 CI 閘門（pytest + arch_fitness）
```

> 註：bootstrap 出廠環境（未裝 `[postgres]` 等選配）full pytest 實測基線約 **3,566 passed / 196 skipped**（總數 3,762；passed/skipped 邊界差 ±個位數，視外部工具與選配依賴現況而定；另一獨立變因：**巢狀 Claude Code session（`CLAUDECODE=1`）**下 `requires_claude_cli` 測試條件 skip（DEF-101-089/091 修復），實測 **3,557 passed / 206 skipped**（−9／＋10），屬預期非退化；與根層 CLAUDE.md 記載的 2026-07-13 乾淨 bootstrap 實測基線 3,566 / 196 一致；Wave 1 相容性修復包（macOS CI 安全網、worktree hook 回歸測試等）新增測試後校正，取代先前 2026-07-11 之 3,543/181 舊基線。**方法論澄清**：本欄先前一版誤標為 3,664/132，經 SA 複審抓出根因是量測時用了主目錄既有、已裝 `[postgres]` 選配（`psycopg2-binary`/`SQLAlchemy`）的 `.venv`，PG-gated 測試從 skip 轉 pass 造成數字虛高，不符本節自稱的「出廠環境」方法論；已改用全新乾淨 venv〔`pip install -e AutoClaude[dev,notifications,lint]`，不含 postgres 選配〕重新量測校正）；skipped 中屬選配依賴缺席者（PG DSN 未設／sqlalchemy 與 `[postgres]` 未裝／claude_agent_sdk 未裝）為預期，非測試退化。AISDLC_SDD `ci-gate.sh` 的逐軌 passed 計數對 **docker daemon 可用性**敏感（daemon 停用時 v0.01／v0.30 各 -3＝`test_phase_h` 的 docker 場景 SKIP），±3 屬環境因素非退化。

---

## 8. Nightly 排程層（跨平台現況與後續）

AutoClaude 有一套 nightly 取證流程（7 stage：local_ci_gate / mutation / pg-e2e / perf / drift / obs / sdd-fsm-chaos）。**目前排程自動化僅實作 Windows 版**：

- **Windows（既有，可用）**：`AutoClaude/tools/run_local_nightly.ps1` 由 Windows 工作排程器 `schtasks` 每日 02:00 觸發（任務名 `AutoClaude_Nightly`）。設定校正見 `AutoClaude/tools/fix_nightly_catchup.ps1`。R9 三項強化：①前置新增 local_ci_gate 全套 stage（對齊 `windows-nightly-full` 深度回歸，push 空窗期也有每日全套訊號）；②pg-e2e stage 加跑 PG contract 測試（`tests/contract/test_pg_state_repository_contract.py`，CI 硬閘的本地對等）；③終端 exit code 帶訊號（任一 stage 失敗→exit 1；SKIP/WARN 不計）——schtasks「上次結果」從此可反映 stage 健康，不再恆 0x0。R10 五項強化：④新增 **sdd-fsm-chaos stage**（鏡射 `aisdlc-sdd-fsm-chaos-nightly.yml` 兩步：pytest `-m chaos`＋100 輪 chaos_runner sweep，CI 停擺期間 Rule 9.9.4 的本地補償，實測 <1 分鐘）；⑤pgvector recall pytest rc 以 `[ref]` 捕捉（先前被 collector 覆蓋，單日真紅假綠）；⑥mutmut log 驗證失敗改 rc=1（先前誤設 WARN 級 rc=2，「防假 pass 守門自身觸發」反而綠出場）；⑦Docker 連續 ≥3 次不可用升級為 exit 1（`.docker_skip_streak` 累計；單次 SKIP 仍屬合理）；⑧END 進度 mutation 軌改印 unique-sha 計數（ADR-SD09-011 語意，原始列數會虛報）。全部強化由 `tests/tools/test_run_local_nightly_static.py` 24 個靜態錨點鎖住。
- **macOS（尚未自動化，本輪擱置）**：`schtasks` 在 macOS 無對應；等價機制是 `launchd`（推薦）或 `cron`。`run_local_nightly.ps1` 尚未移植成 `.sh`；過渡期可先用 `tools/macos_smoke_local.sh`（見下方 R9 補償控制）。

> ⚠️ **本機排程自動化仍未完成**：macOS nightly **本機**自動化（`run_local_nightly.sh` + launchd/cron，比照 Windows `schtasks` 的個人開發機定期背景任務）為**後續工作**，本輪未實作。整個 ops 排程家族（`g0_gate_check.ps1`、`reschedule_g0_gatecheck.ps1`、`fix_nightly_catchup.ps1`、`run_local_nightly.ps1`）皆屬 Windows-only、無 `.sh` 對等，均涵蓋於本節「排程自動化僅 Windows」的明示缺口。
>
> ✅ **不同軌的另一層已補上：雲端機械化 CI 安全網（`.github/workflows/macos-compat-ci.yml`）**：上面講的是「開發者個人機器上的排程自動化」缺口；與此無關的是——在本輪之前，macOS 端**完全沒有任何機械化 CI 驗證**（全部 workflow 的 `runs-on` 只有 `ubuntu-latest`／`windows-latest`，macOS 側長期僅靠人工對照與文件宣稱）。Mac/Windows 相容性修復輪新增了 `macos-compat-ci.yml`，補上先前完全沒有的 macOS 機器化覆蓋：**`macos-smoke`**（PR/push 閘門，觸及平台敏感路徑才觸發，實際「執行」而非僅語法解析）涵蓋 `bootstrap.sh`／`dev_start.sh`（含 mac 專屬的 `cross_same_flavor` 分支）、`install_git_hooks.sh`／`install-hooks.sh`（含 linked worktree 拒絕情境）、`install_post_commit.sh` 在 **git worktree** 下的寫入情境、根層 `tools/git-hooks/` 三支 dispatcher 在 macOS **系統內建 bash 3.2**（非 Homebrew 新版）下的直接執行、`AISDLC_SDD/scripts/ci-gate.sh`（凍結基線 v0.01 + LATEST 雙軌）；**`macos-nightly-full`**（`schedule`/`workflow_dispatch`）另跑兩子專案完整測試套件在 `macos-latest` 上的深度回歸。因此「開發迴圈（測試／lint／ci-gate／整合閘門）在 macOS 已對等」現在**有機器驗證佐證**，不再只是文件宣稱——但仍有限制須如實揭露：① `macos-nightly-full` 為 `continue-on-error: true` 非阻斷 job，失敗不擋 PR、僅供事後觀察；② GitHub-hosted `macos-latest` runner 與開發者個人 Mac 的實際硬體／OS 版本仍可能有落差；③ 此 CI 與本節開頭的「本機排程自動化」（launchd/cron）屬不同層次缺口，未被本次新增的 CI 覆蓋，該缺口依然存在。
>
> ✅ **R9 補償控制（DEF-101-081 CI 帳單停擺期間）**：上段 CI 安全網停擺期間，macOS 專屬回歸（bash 3.2 語法、`.sh` 安裝腳本 worktree 防護等）在任何機器上都不會自動跑——R9 新增 `tools/macos_smoke_local.sh`（本地聚合驗證：`bash -n` 全量＋dispatcher 直呼煙霧＋兩支安裝腳本往返/worktree 拒絕＋LATEST `install_post_commit.sh` worktree 與移除後路徑斷言＋NTFS/parity 兩支守門，與 `macos-compat-ci.yml` 對應 step 同步維護），Mac 開發者可手動（或 launchd 排程）執行補位。已於 Windows Git Bash 實跑全綠（PASS=10 FAIL=0）；**真 macOS `/bin/bash` 3.2 實跑待 Mac 機器或 CI 恢復後補驗**（腳本已通過 bash 3.2／BSD 工具相容性靜態自查：無 declare -A/mapfile/`${var,,}`、無 sed -i/readlink -f/grep -P/BRE 交替）。
>
> ✅ **R10 Windows 側對等補償（DEF-101-139）**：對稱地，`windows-compat-ci.yml` 的「執行級」`.ps1` 驗證（install 兩腳本 worktree 拒絕、LATEST `install_post_commit.ps1` worktree 實跑＋移除後路徑斷言、非 ASCII 路徑安裝）同樣只活在停擺的雲端、SDD 回歸測試明文只鎖 `.sh` 版——R10 新增 `tools/windows_smoke_local.ps1`（本地聚合驗證，PASS=8：active `.ps1` Parser 全量＋fake repo＋`install_git_hooks.ps1`／`install-hooks.ps1` 往返與 worktree 拒絕＋LATEST `install_post_commit.ps1` worktree 實跑＋中文路徑（`煙霧測試`）安裝抽驗；PowerShell 5.1 實跑全綠；LATEST 解析走 `AISDLC_SDD/scripts/sdd_version.py` 單一真相源）。兩平台 smoke 自此對稱：macOS＝`macos_smoke_local.sh`、Windows＝`windows_smoke_local.ps1`。

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
| **AutoClaude PTY 模式在 macOS 無 POSIX 實作**（`wexpect` 為 win32 專屬，無 pexpect 分支） | 引擎在 mac 一律走 subprocess fallback，部分互動提示可能無法自動回應 | 改用 `executor.backend="sdk"`（Claude Agent SDK，opt-in），或接受 subprocess 模式 |
| **凍結版 v0.01 `post_commit_drift.py` 在 Windows 無 SIGALRM、亦無 thread guard**（docstring 宣稱 thread guard 但實作缺席，docstring 與實作不符） | 該 hook 在 Windows 無 2s 預算保護（advisory hook 卡住時無界） | v0.30 已補 thread guard；凍結版依紀律不回改 |
| **macOS 桌面通知 plyer 後端需 `pyobjus`**（`notifications` extra 未宣告，刻意不加重依賴） | plyer 在 mac 必然 `ModuleNotFoundError` 失敗 | **已支援**：notifier 內建 darwin `osascript` fallback 自動承接（ESCALATION 通知不再靜默降級 log-only）；log 仍為最後手段 |
| **凍結版 v0.01~v0.29 settings.json 無 `PYTHONUTF8` env、hook command 仍為裸相對路徑**（僅 v0.30／根層已改 shim；凍結版依紀律不回改，DEF-101 凍結版豁免家族） | 直啟凍結版子專案 session 時：① hooks 在 zh-TW Windows（cp950）的 stdin/stdout 解碼風險不受 env 保護；② cwd 漂移時裸相對路徑同樣有 exit-2 deny-lock 風險（DEF-101-028 同場景） | 根層 router 路由情境已由根層／v0.30 覆蓋；直啟凍結版屬 dogfooding 邊角情境，必要時先手動設 `PYTHONUTF8=1` 並保持 cwd 於版本根 |
| **凍結版 v0.01~v0.29 `install_post_commit.ps1` 用 `-Encoding ascii` 寫 hook，非 ASCII 路徑會被靜默替換為 `?`**（v0.30 已修：改 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)`） | 手動 cd 進舊版目錄執行 hook 安裝（非官方流程）時，含中文字元的使用者路徑會讓 drift/closure advisory hook 內嵌路徑損毀、靜默失效；`v0.12~v0.29`（18 支）另因缺 BOM 會先 parser 斷裂根本跑不到此行 | hook 安裝流程動態解析 LATEST 版（現為 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.ps1`；R9 訂正：本欄舊文誤植為 `AutoClaude/tools/install_hooks/...`，該路徑全 repo 歷史從未存在），正常安裝流程不會觸及舊版；凍結版依紀律不回改 |
| **`AutoClaude/pyproject.toml` 的 `hypothesis` 已於 R3 精確鎖版**（`hypothesis==6.156.6`；此前 `>=6.0` 未鎖上限曾於 Wave 1 全新環境 `pip install` 下被懷疑導致約 19 個測試連鎖失敗，後經 SA/SD 兩方獨立以全新 venv 重驗**無法重現**，原始診斷已訂正為未經證實的記事，見 DEF-101-058） | 全新環境 `pip install -e ".[dev]"` 解析依賴版本的跨平台漂移風險，不因鎖版而完全消除——`pyproject.toml` 另有 ~18 條相依（`pydantic`／`sqlalchemy`／`httpx` 等）仍未鎖版本上限，屬同類風險（見 DEF-101-060，尚未處理） | 已修：`pyproject.toml` 鎖定為經本機全新 venv 驗證綠燈的 `hypothesis==6.156.6`（DEF-101-058，fixed@Mac/Windows 四方複審 2026-07-14）。其餘 ~18 條未鎖依賴為 DEF-101-060，記事存證待後續輪逐一評估鎖版 |

> 對應缺陷帳本：前兩條＝[AutoSDD_Defect_Log.md](docs/06_quality/AutoSDD_Defect_Log.md) DEF-101-003／DEF-101-004（wontfix＋凍結版紀律）；第 4~8 條＝DEF-101-019／DEF-101-020（wontfix＋凍結版紀律）與 DEF-101-021／DEF-101-022／DEF-101-025（open）；倒數第三條（凍結版 settings 兩面向）＝DEF-101-040（wontfix＋凍結版紀律）；倒數第二條（`install_post_commit.ps1` ASCII 編碼）＝DEF-101-056（wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正）；末條（`hypothesis` 版本鎖定）＝DEF-101-058（**fixed@Mac/Windows 四方複審 2026-07-14**；R3 複審發現本文件先前敘述與此已修復實況不同步，已訂正）。另有 **DEF-101-005**（`verify_traceability.sh` 的 `set -e`＋grep 零命中提前靜默退出，所有 bash 版本皆然、v0.30 亦未修，**open** 待 RFC）、**DEF-101-018**（ruff 存量 baseline 1,339 筆待分批清理，open；其「未鎖版跨機器漂移」根因 DEF-101-006 已 fixed@四方複審第三輪）、**DEF-101-057**（`install_post_commit.{sh,ps1}` worktree 路徑解析 bug 在 v0.01~v0.29 之殘留，wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正；不佔本表列，因與上方 DEF-101-056 同源議題已合併敘述於缺陷帳本本身）與 **DEF-101-060**（`pyproject.toml` 另有 ~18 條相依未鎖版本上限，open，記事存證，見上表 hypothesis 列）非平台缺口、不列本表。

---

## 10. 跨平台測試 fixture 撰寫紀律（強制檢查點）

**規則**：任何新增的跨平台測試 fixture（涉及檔案系統／直譯器／symlink／subprocess 等
平台假設，例如 mock `sys.platform`、複製 `sys.executable` 偽裝健康 venv、建立
symlink 模擬快取等），**在合入前必須至少於一次目標平台的真實 CI run 驗證過，mock
`sys.platform` 不算數**。

**理由（血淚教訓，見 [AutoSDD_Defect_Log.md](docs/06_quality/AutoSDD_Defect_Log.md)
DEF-101-064／DEF-101-069）**：`tools/tests/test_dev_start.py` 這批平台邏輯測試長期
只在 `ubuntu-latest`（靠 mock `sys.platform` 模擬）跑過；`windows-compat-ci.yml` 補上
真正在 windows-latest 執行後，**第一次真跑就一口氣揪出 16 個真實失敗**
（`UnicodeEncodeError`／shebang 腳本非合法 PE 格式／唯讀 git 物件檔無法用 POSIX
語意刪除等）——證明「本機或 CI mock 綠燈」不能代表「目標平台真的能跑」，這類假設
只有真的在對應作業系統上執行一次才會顯形。

**落地方式**：
- PR 觸及 `tools/tests/**`、`AutoClaude/tests/**` 等含平台假設的測試檔時，
  `windows-compat-ci.yml` / `macos-compat-ci.yml` 的 paths 白名單須涵蓋（見
  DEF-101-064 修復），且對應 smoke job 須有實際「執行」該測試檔的 step，非僅語法
  解析。
- 新增測試若需要「健康的既有 venv/直譯器」或「symlink」等平台敏感 fixture，優先重用
  `tools/tests/_platform_helpers.py`（`copy_functional_interpreter()` /
  `create_symlink_or_skip()`），不要重新手刻——這兩個 helper 本身就是
  DEF-101-064／DEF-101-069 修復的產物，內含完整踩雷紀錄；`AutoClaude/tests/`
  若有對等需求，比照同一邏輯在 `conftest.py` 撰寫對稱 fixture（見該檔說明）。
- 合入前至少手動觸發一次對應平台的 `workflow_dispatch`（或等待該 PR/nightly 真跑），
  不可只憑本機同平台或 `ubuntu-latest` mock 的綠燈就視為「跨平台已驗證」。
