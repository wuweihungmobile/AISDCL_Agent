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
- **Windows**：`winget install Python.Python.3.11`（即官方 python.org 安裝器版型；或用 pyenv-win）
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
| 手動補裝套件時 `python -m pip ...` 報 `No module named pip` | `.venv` 是 bootstrap 偵測到 `uv` 時走 `uv venv` + `uv pip install` 建的，這種 venv **內部本來就沒有 `pip` 模組**（Mac/Windows 四方複審實機驗證重現） | 改用 `uv pip install -e '.[...]'`（uv 已安裝時對任何已啟用的 venv 皆可用；**extras 的引號不可省，理由見下一列**）；完整警語見 [CLAUDE.md](CLAUDE.md)「AutoClaude — 常用指令與架構」§安裝/執行 與 [docs/AISDLC_Agent_UserGuide.md](docs/AISDLC_Agent_UserGuide.md) §1.2 |
| macOS 上跑 `uv pip install -e .[dev,notifications]` 報 `zsh: no matches found: .[dev,notifications]`（R57 新增） | macOS 自 Catalina 起預設 shell 是 **zsh**，`.[...]` 未加引號會被當成 glob 做 filename generation；repo 內無匹配檔名時 zsh **在執行前就中止整條指令**（uv／pip 根本沒被叫到，所以錯誤訊息看起來與套件無關）。同一行在 bash 與 PowerShell 下正常，故 Windows 開發者不會遇到 | extras 一律加單引號：`uv pip install -e '.[dev,notifications]'`（三種 shell 皆正確）。權威指令站點見 [CLAUDE.md](CLAUDE.md)「AutoClaude — 常用指令與架構」§安裝/執行；本列因必須引述壞形態才說得清症狀，於 `tools/tests/test_extras_quoting_zsh_safety.py` 取得行內豁免 |<!-- zsh-glob-ok: 雷區對照表必須原樣引述未加引號的壞形態才能說明症狀，此處非教學指令 -->
| pytest 在 Windows 上報 DLL not found／`rc=0xC0000135`（`STATUS_DLL_NOT_FOUND`） | 未啟用 `.venv` 就直接用裸系統直譯器（pyenv-win／winget／python.org 安裝器版型）跑測試，`tools/tests` 部分 fixture 會複製當前直譯器模擬健康 venv，缺同層 DLL 導致複製出的 exe 啟動失敗（DEF-101-256） | 先啟用專案 `.venv`（對照 §3）再跑 pytest |

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

※ **git hooks 注意（monorepo，根層 dispatcher 架構）**：本 repo 是單一 git repo，`core.hooksPath` 只有一個值——現統一指向**根層 `tools/git-hooks/`**（**三支 hook**：pre-commit + pre-push dispatcher ＋ post-commit advisory 委派器；以主 checkout 根解析為**絕對路徑**）。上表四支安裝腳本（AutoClaude 與 AISDLC_SDD 各 `.sh`/`.ps1`）**任一支皆設定同一個根層 dispatcher，兩子專案閘門同時生效**——裝一次即可，舊的「兩子專案互斥擇一」已廢除；安裝腳本會驗證三支 hook 檔齊備才回報成功。dispatcher 依 commit/push 涉及的路徑自動分流：`AutoClaude/` 變更 → AutoClaude hooks；`AISDLC_SDD/` 變更 → AISDLC_SDD pre-push；**任何非兩子專案的根層路徑**（`tools/`、`docs/`、`.github/` 等）變更 → pre-push 另跑 **root-infra leg**（`py_compile` 全根層 Python（R10 起含 `.claude/hooks/`）＋`tools/tests` unittest（R10 起經 `tools/run_root_unittests.py`，含測試數量下限釘選——裸 discover 對「發現 0 個測試」回 rc=0 的 fail-open 已堵）＋六支守門工具 parity／NTFS／crossref／wrapper-thinness／pytest-baseline-sites（R13 增）／gha-action-versions（R55 增），R9 補上、R10 擴充，對齊 `root-infra-ci.yml` 的本地接線——先前純根層變更 push 一個閘門都不跑，CI 帳單停擺期間即為零防護）；另外，push 若命中**根層消費檔**（`aisdlc-sdd-ci.yml` paths 承認的非 `AISDLC_SDD/` 條目：NTFS 閘、根層 pre-commit、兩份 `.claude/settings.json`、`sdd_hook_router.py`——其回歸鎖住在 `AISDLC_SDD/scripts/tests/`）且 SDD leg 未觸發，pre-push 會補跑該回歸鎖（R10 ARCH-1：清單機械讀取該 yml，勿手抄第二份；功能行為由 `tools/tests/test_pre_push_dispatcher.py` 六情境鎖住、CI↔本地守門清單對應由 `test_root_infra_parity.py` 鎖住）。

- **※ repo 搬移／改名後 hooks 靜默失效（QA 實證）**：`core.hooksPath` 寫的是絕對路徑，整個 repo 目錄搬移或改名後 git 找不到 dispatcher，**不會報錯、閘門直接全滅**。搬移後**必須重跑任一支安裝腳本**。四支閘門腳本（`local_ci_gate.sh/.ps1`——R12 起偵測位於其 Python 核心 `local_ci_gate.py`，薄殼不再自帶；`integration_gate.sh/.ps1`——仍於腳本開頭）已內建 **hooks liveness 偵測**：hooksPath 未設定／與預期不符／目錄不存在時印醒目警告（不 fail；CI 環境自動跳過）。
- **linked worktree**：四支安裝腳本在 linked worktree 內執行（含 `--uninstall`）一律**拒絕並 exit 1**——`core.hooksPath` 寫入共享 `.git/config`，在 worktree 內安裝會毒化主 checkout。請在**主 checkout** 安裝一次；hooks 執行期以 `git rev-parse --show-toplevel` 動態定位，之後在任何 worktree 內 commit/push 都自動對該 worktree 的樹生效。**注意**：`.venv`／bootstrap 不隨 git worktree 共用——每個新建的 linked worktree 第一次執行本指令（`dev_start`）仍需完整跑一次 bootstrap（裝全部依賴），不是「一個指令、隨開隨用」的秒級體驗；僅 git hooks 設定會如實跳過並沿用主 checkout。
- **post-commit 委派器**：`core.hooksPath` 一經設定，git 對所有 hook 種類只查 dispatcher 目錄，原裝在 `.git/hooks/post-commit` 的機制（如 AISDLC_SDD 框架 R-9.17.1 drift 告警）會整族靜默失效——故 dispatcher 第三支 `post-commit` 轉呼叫共享 `.git/hooks/post-commit`，advisory 語意（無論結果 exit 0）。
- **fail-safe / fail-loud 語意**：pre-push 收到**空 stdin**（如被 pre-commit 框架 shim 吃掉）＝fail-safe **兩子專案閘門全跑**；pre-commit 的 `git diff` 失敗亦 fail-safe 全跑；刪除遠端分支（zero push）維持跳過。分流**命中**但對應子 hook 檔缺失 → **fail-loud rc=1 擋下**（不靜默放行）。大型 commit/push（>64KB 變更清單）已修復 SIGPIPE 缺陷，不再靜默漏跑。
- **已知縫隙**：merge / rebase 自動產生的 commit 天然繞過 pre-commit 家族（git 行為，非本 repo 缺陷），由 pre-push 兜底把關。另一縫隙「rename 移出子專案 fail-open」（`git mv AutoClaude/x docs/x` 時 rename 偵測只列新路徑、來源子專案閘門靜默漏跑）已於四方複審第三輪修復——dispatcher diff 加 `--no-renames`（DEF-101-008）。
- **pre-commit 新增兩道閘（四方複審第三輪，commit 可能因此被攔的新原因）**：① **NTFS 檔名閘**——新增檔名含 Windows 不允許字元（`< > : " | ? *`／控制字元）、保留裝置名（CON/PRN/AUX/NUL/COM0~9/LPT0~9，COM0/LPT0 比照業界防禦性實作採保守納入）、尾隨空白/句點、或與既有路徑僅大小寫不同（NTFS 碰撞）會被 rc=1 擋下，改名後重新暫存即可（DEF-101-011）；repo 相對路徑 **>200 字元**（code point 計，locale 無關）亦 rc=1 擋下、>180 預警——Windows MAX_PATH=260 保守閘，縮短檔名或目錄層級即可（DEF-101-039，四方複審第五輪）；② **根層基建 leg**——commit 涉及根層 `tools/`、`.github/`、`.gitattributes`、`.editorconfig` 時，對變更到的 `.sh`／無副檔名 hook 檔跑 `bash -n` 語法檢查，語法錯誤擋下（DEF-101-012）。
- **執行權限政策**：「755 入庫」範圍＝**hook 檔（`tools/git-hooks/` 由 git 直接執行；`AISDLC_SDD/.githooks/` 與 `AutoClaude/tools/git-hooks/` 為 dispatcher 分流目標——以 `bash` 呼叫、exec bit 非必要，維持 hook 家族一致即可）＋ launchd 載體 `AutoClaude/tools/run_local_nightly.sh`**（R11 D6 決策保留 755；R14 SCAN-CI-7 訂正 rationale：§8 範本與 `install_mac_nightly.sh` 產出的 plist 皆以 `/bin/bash` 為執行檔、腳本僅為引數，exec bit 已非執行必要，保留 755 作為容忍手動直呼的防禦與 D6 決策延續）；其他 `.sh` 工具一律以 `bash xxx.sh` 呼叫、索引 644，不依賴 executable bit（R12 已將 bootstrap／integration_gate／install_git_hooks／local_ci_gate／run_act 五支歷史 755 正規化為 644，使本政策句與索引實況一致）。
- **雙腳本對等機械守護**：上表 bootstrap／integration_gate／run_act／local_ci_gate 四對 `.sh`/`.ps1` 均已收斂為「薄殼＋Python 單核心」，改由 `tools/check_wrapper_thinness.py` hash 釘選守門；`check_script_parity.py` 的 `_MARKER_PAIRS` 標籤比對（R9 起標籤抽取同時接受單/雙引號，並釘選各對標籤數量下限，防「兩側同步改寫致標籤同時消失」的靜默縮面）對這四對已退場，目前為空清單，保留作為未來若有新對「雙邊各自完整原生實作」腳本需要標籤比對納管時的既有機制，非死碼（見該檔 docstring；R28 訂正——本段先前誤留 R16 收斂前的舊描述，與程式碼現況不同步）。**`local_ci_gate` 對已於 R12 收斂**（`AutoClaude/tools/local_ci_gate.py`，DEF-101-070 ② 欠帳落地；9 個 gate 的漂移面物理消滅，兩薄殼改由 thinness hash 釘選守門〔與 parity 登記另有鍵集合交叉鎖〕，與 dev_start 同類；呼叫端介面零改動）；**bootstrap／integration_gate／run_act 三對已於 R16（Architect 建議 B）同步收斂**為 `tools/bootstrap_core.py`／`tools/integration_gate_core.py`／`AutoClaude/tools/run_act_core.py`（前兩者位於根層 `tools/`，`run_act_core.py` 位於 `AutoClaude/tools/`，非根層；integration_gate 對應 DEF-101-068(b)；run_act 對應 R12 DEF-101-070 ② 同案模式延伸），三對業務邏輯漂移面同樣物理消滅，介面與收斂前完全相容。gate 名單的機械凍結＝其單元測試（`AutoClaude/tests/tools/test_local_ci_gate.py`，gate 清單/順序精確等值凍結＋editable 哨兵紅/綠，計數見該檔勿在此硬編）；**獨立第二訊號＝dispatcher pre-push AutoClaude leg 直跑 pytest（刻意不經 local_ci_gate，勿改為經其呼叫——兩訊號合流即單點化，R12 QA-2 紀律）**。其餘兩對（install_git_hooks、AISDLC_SDD install-hooks）判定邏輯已收斂至 `tools/git_hooks_install_common.py` 單一真相源、殼層無可抽取的標籤錨點，**暫無標籤比對**——改任一邊須人工同步另一邊（明文侷限，見 check_script_parity.py docstring）。`dev_start` 對**同樣**由 `tools/check_wrapper_thinness.py` hash 釘選守門——依該檔 docstring，`dev_start` 其實是本 repo「薄殼＋Python 單核心」模式的**原始範例**（早於 local_ci_gate 等後續收斂案），七步驟業務邏輯集中於跨平台單一核心 `tools/dev_start.py`，兩薄殼由 `_PINNED_SHA256` 個別釘選＋`_THINNESS_ENROLLED` 與 thinness 交叉鎖機械守住（同上，非「無業務邏輯漂移面」故不需釘選，而是釘選機制本身即涵蓋它）；不適用的只有 `_MARKER_PAIRS` 標籤比對（同前段所述四對已退場範圍，dev_start 亦不在其中）。**薄殼退化守門**：`tools/check_wrapper_thinness.py`（`root-infra-ci` 步驟 10 具名執行＋步驟 8 unittest 覆蓋）守住「兩薄殼不再長回業務邏輯」——R10 改制為**正規化內容 hash 釘選**（權威判定：剝註解/空行後 sha256 對表，任何實質變動一律紅燈、指路更新釘選；黑名單曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過，降級為 hash 紅燈時的診斷輔助）＋行數上限第二訊號（拍板案(a)，DEF-101-134）。**成對腳本註冊完整性（enrollment 發現鎖，R10 同案）**：`check_script_parity.py` 掃描 `tools/`、`AutoClaude/tools/`、`AISDLC_SDD/scripts/` 下同名 `.sh`/`.ps1` 對，斷言每對必屬 {parity 標籤比對, thinness hash 釘選, 明文豁免（附帳本依據）} 之一且註冊清單無 stale——「新增成對腳本繞過守門」自此為機械攔截，不再只靠人工記得。

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
| `root-infra-ci.yml` | （四方複審第三輪新增，非遷移）根層基建守門：**全變更觸發**（NTFS 檔名閘須守任意路徑，paths 白名單必留盲區），現行**十二道**輕量檢查（詳細內容以 workflow 檔頭註解為準，避免每次擴充都要同步改動兩處）——1. `bash -n`（**R56 擴面**：全庫 tracked active `*.sh`＋三處無副檔名 git hooks 目錄〔`tools/git-hooks/`、`AutoClaude/tools/git-hooks/`、`AISDLC_SDD/.githooks/`〕；AISDLC_SDD 凍結版 `v0.01~v0.(N-1)` 依紀律不回改故排除、LATEST 版納入，政策與第 2 道一致。檔數下限分「`.sh`／git-hooks」兩段釘選，數字刻意只住 step 內註解——第二個計數站點即第二個會漂移的站點）；2. pwsh parse＋UTF-8 BOM（active `.ps1`：根層 `tools/`＋`AutoClaude/tools/`＋`AISDLC_SDD/scripts/`＋LATEST 版，凍結版排除）；3. EOL 守門（`.sh`，須為 LF）；4. EOL 守門（`.ps1`，反方向須為 CRLF，2026-07-13 補洞）；5. NTFS 檔名閘（`tools/check_ntfs_paths.py`，pre-commit NTFS 閘的 CI 對等）；6. 腳本對等閘（`tools/check_script_parity.py`：成對 `.sh`/`.ps1` step 標籤清單＋LATEST tools 納管＋pytest 釘選三處同版）；7. `py_compile`（根層 `tools/` 下所有 `*.py` 語法檢查，dev_start 四方審查 P2）；8. `unittest`（`tools/tests/`，R10 起經 `tools/run_root_unittests.py` 執行、含測試數量下限釘選——裸 discover 對 0 個測試回 rc=0 的 fail-open 已堵；收斂 py_compile 守不到的邏輯回歸落差）；9. 缺陷帳本跨文件狀態一致（`tools/check_defect_log_crossref.py`）；10. wrapper 薄殼守門（`tools/check_wrapper_thinness.py`）；11. pytest 基線站點鎖（`tools/check_pytest_baseline_sites.py`，R13 ARCH-R13-1——基線數字唯一站點＝本檔 §7，其餘活文件禁載數字）；12. GitHub Actions 版本一致性鎖（`tools/check_gha_action_versions.py`，R55 增、**R56 通用化**——斷言**全部 `actions/*` 官方 action**〔含子路徑 action 如 `cache/restore`〕跨全部 workflow 版本唯一，不判斷哪個版本才對，只擋「同一 action 出現兩種版本」。R56 起刻意**不再列舉 action 名**：原本的四名白名單本身即 fail-open〔打錯一個字就靜默少守該 action 的所有宣告卻仍印綠燈〕，且 workflow 檔頭側再出現列舉會被 `tools/tests/test_root_infra_parity.py` 擋下）（DEF-101-012、四方複審第四／五輪＋R8／R13 擴充＋R55 擴充） |
| `windows-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）Windows 側執行級驗證：windows-smoke（bootstrap/dev_start/install 腳本/dispatcher 真實 commit 觸發；step 以 pwsh 為主，僅 dispatcher 觸發 step 刻意用 Git Bash 載具）＋ windows-nightly-full（深度回歸，**含 PS 5.1 引擎專測**——R5/S8 拍板置於 nightly 非 PR 閘門，R12 訂正本列歸屬誤植）；本地補償對等＝`tools/windows_smoke_local.ps1`（R10） |
| `macos-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）macOS 側執行級驗證：macos-smoke（bash 3.2 直呼/安裝腳本/worktree/ci-gate 雙軌）＋ macos-nightly-full；本地補償對等＝`tools/macos_smoke_local.sh`（R9）。詳見 §8/§10 |

`.actrc` 亦已上移根層；`run_act`（AutoClaude 側）與 `act-ci.sh`（AISDLC_SDD 側）現於 **monorepo 根**執行、讀根層 `.actrc`。（Dependabot 已於 2026-07-12 完全停用並移除根層 `dependabot.yml`——單人 main-only 工作流不採自動相依 PR；GitHub 端 security updates／vulnerability alerts 亦為停用。相依更新改為日後手動盯版或重新啟用。）

---

## 7. 常用驗證指令

**macOS / Linux（bash・zsh）**

```bash
# AutoClaude（在 AutoClaude/ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試
PYTHONUTF8=1 lint-imports             # 架構約束（8 kept / 0 broken）

# AISDLC_SDD（在 AISDLC_SDD/ 下）
bash scripts/ci-gate.sh               # 本機 CI 閘門（pytest + arch_fitness）
```

**Windows（PowerShell）** — R57 補齊：本節原先是全份雙平台文件中唯一只給 bash 形態的指令區，其中 `PYTHONUTF8=1 lint-imports` 的 `VAR=value cmd` 前綴語法**在 PowerShell 不存在**，會報 `The term 'PYTHONUTF8=1' is not recognized`（實測 pwsh 7）；設環境變數須改用 `$env:VAR=值; <指令>`。

```powershell
# AutoClaude（在 AutoClaude\ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試（與 bash 形態同）
$env:PYTHONUTF8=1; lint-imports       # 架構約束（8 kept / 0 broken）

# AISDLC_SDD（在 AISDLC_SDD\ 下）
powershell -ExecutionPolicy Bypass -File scripts\ci-gate.ps1   # 偵測到 Git Bash 即薄委派 ci-gate.sh＝完整對等，見 §6
```

> 🔴 **本節為全 repo pytest 基線數字唯一站點**（R13 ARCH-R13-1 收斂：其他活文件〔根/AutoClaude CLAUDE.md、AutoClaude/README、useMacWin〕一律指向本節不重複數字，由 `tools/check_pytest_baseline_sites.py` 機械守門；歷史紀錄檔〔缺陷帳本、sprint_history、improving 系列等時代快照〕不在納管範圍）。
>
> 🔴 **本節記錄規則（R58 加強；起因＝R58 五維掃描發現 #5，屬 DEF-101-289 同族的又一次復發。正式 DEF 編號於收輪時統一登記缺陷帳本，此處不預先寫死免對不上）**：
> 1. **pytest／unittest 類基線一律以 `(passed, skipped)` 成對記錄，缺一即視為不可用**——只有 passed 沒有 skipped 的數字**不得**被後續輪次引用為基線，必須重測。**理由（為何是 skipped 而不是 passed）**：skipped 是偵測「venv 污染」與「平台閘門移位」的**主要鑑別欄位**，passed 對這兩類失真幾乎沒有鑑別力。本節下方 R56 校正段落即為實證——受污染 `.venv` 量得的 passed 反而**變高**（看起來像進步），是 `skipped` 由 210 驟降到 64（PG-gated 測試由 skip 轉 pass）才揭露污染；若當時只記 passed，該錯誤基線會直接寫進 SSOT。
> 2. **每一筆量測聲明都必須標註〔量測平台〕**（本規則原由下方 R37 校正段落的 R42 SA 一審補記訂立，但長期只有 AutoClaude 那組數字照做，根層與 AISDLC_SDD 兩組持續漏標——R58 把它從「敘述性要求」提為本節開頭的硬規則）。
> 3. **平台相依的數字一平台一行**，不可壓成單一 scalar。根層 `tools/run_root_unittests.py` 的 skipped **結構性因平台而異**（POSIX-only 案例在 Windows 全 skip、在 macOS 全跑），把它記成一個沒有平台標註的數字＝把兩個不同平台的量測混成一個假通用值，正是 DEF-101-289 同族缺陷反覆復發的形狀。
> 4. **本節數字的機械守門有已知判準邊界**：`tools/check_pytest_baseline_sites.py` 只能防「同一數字在多個檔案各說各話」（第二個家），**不能**防「本節自己的數字過期」或「本節自己前後矛盾」（R58 同輪即在下方 R57 段落抓到 615／616 同行自相矛盾，見該段 R58 訂正）。本節內部一致性仍靠人審。
>
> 🔴 **量測環境揭露：Claude Code session 內取得的數字是 UTF-8 mode 下的值（R58 補，比照本節既有「巢狀 session 變因」揭露慣例）**——本 repo 的 Claude Code session 透過 `.claude/settings.json` 的 `env.PYTHONUTF8=1` 把 UTF-8 mode 注入**所有**子行程，故 session 內跑出來的基線數字全部帶這個變因。真實使用者雙擊開 Windows PowerShell 5.1 直接跑腳本時**沒有**這個變數（本機 ACP=950），`locale.getpreferredencoding()` 會是 cp950。**後果**：任何「依賴 locale 預設編碼」的退化（`open()` 未帶 `encoding=`、`subprocess` 未帶 `encoding=`／`text=True` 的解碼等）在 session 內驗證**不會翻紅**——綠燈只證明「UTF-8 mode 下沒事」。要驗這類退化必須另開一個不帶 `PYTHONUTF8` 的原生終端機重跑（與「巢狀 session」「選配 venv 污染」並列為本節第三個已知量測變因）。
>
> 註：**R58 校正（2026-07-27，五維掃描＋多包並行修復＋三輪四方複審）**——依上方新訂的記錄規則，本段校正**根層／AutoClaude／AISDLC_SDD 三組**數字，一律改為**成對值＋每平台一行**（round 3 SA-R58R3-01 訂正：本段原寫「只校正兩組、AutoClaude 本輪未重測」，但本輪確實有可重現的原生 Windows AutoClaude 量測，且複審者亦獨立複現）：
>
> - **根層 `tools/run_root_unittests.py`**
>   - 〔量測平台：**原生 Windows 11 Pro 10.0.26200**、Windows PowerShell 5.1（本機無 pwsh 7，屬 Windows 11 出廠組態）、`.venv/Scripts/python.exe` Python 3.11.9、Claude Code session 內（即帶 `PYTHONUTF8=1`，見上方揭露）〕**847 tests OK / skipped=10**（**收輪定案值**：由主控在所有並行修復包與四方複審 agent 全部停工後、於最終工作樹一次性實跑 `PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe tools/run_root_unittests.py` 取得，不做任何加減推算）。**輪次進行中的中間值依序為 646/11 → 771/10 → 781/10 → 824/10 → 827/10 → 834/10 → 835/10 → 837/10 → 844/10 → 841/10 → 846/10**（**逐值對輪次**：646/11＝round 1 前、771/10 與 781/10 為輪次中途、824/10＝round 2、827/10＝round 3、834/10＝round 4、835/10＝round 5（round 6 未增測試方法）、837/10＝round 7、844/10＝round 8、841/10＝round 9〔判準拆簡使自驗 7→4 支，淨 −3〕、846/10＝round 10〔自驗補到 9 支〕），皆已作廢，此處只保留定案值 847/10（round 11 再補 1 支 meta 散文 fixture）；**🔴 round 11 SA-R58R11-01 訂正（P1，九輪來首次 P1）**：本欄在 round 10 收尾時記的 「846 tests **OK**」**是假宣稱**——實跑為 `Ran 846 tests` 緊接 `FAILED (failures=1, skipped=10)`，三方各自複現並以 `git show :` 排除工作樹髒汙。成因是主控**在寫入該輪帳本列之前**量的，而那一列的文字本身讓一支新落地的守門測試翻紅（該鎖判別式把「描述本鎖的散文」誤判成宣稱）⇒ 基線 SSOT 記著綠燈而實況是紅燈，與 SA 在 round 1 立為 P1 的同一缺陷類、且更重。**根治見上方新增的〈收尾順序紀律〉**；本次的 847 是依該紀律「文件全部寫完後」才量的；**⚠️ 本段落初稿曾記 646/11 並自我標註「收輪前務必重測」，round 1 SA 複審即以此判為 P1 blocking（基線 SSOT 記著已過期的數字＝開發者判斷退化的唯一參照點不可信）——已依其要求於收輪回填。round 3 SA-R58R3-02 另抓到：主控回填時用無腦全域字串替換，把本句改成「初稿曾記 827/10」「中間值為 827/10」，同句自我打臉且陳述了不存在的歷史；已改回敘事正確的寫法**：本輪多包並行，量測後工作樹仍在增加測試檔，`Ran` 計數結構上無法在輪次進行中途收斂——此限制非本輪新發現，下方 R52 round 3 段落已詳載同一結構性問題（「多支修復包並行、單一 agent 事後局部重驗＋回填…對這種需橫跨全部並行修復包才能算準的全域數字，結構上無法在輪次進行中途收斂」），本段沿用該既定紀律：**最終值須由收尾角色在所有並行包停工後重測**。10 筆 skip 的組成（本節規則 1 要求 skipped 可被歸因，否則下一輪無法判斷變動是退化還是平台差異；**以下逐筆取自 `python -m unittest discover -s tools/tests -p "test_*.py" -v` 的skip 理由行，不從敘述句組**）：**8 筆 POSIX-only**（`os.killpg`／process group ×2、POSIX signal handler ×1、pgid 語意 ×4、SIGINT 轉發 ×1）、**1 筆 Darwin-only**（`install_mac_nightly.sh` 的 `report_heartbeat()` 依賴 BSD `stat -f %m`，非 Darwin 上跑本身即為假訊號）、**1 筆 symlink 建立權限不足**（`WinError 1314`）＝**10**，且**全 10 筆皆在 `tools/tests/test_dev_start.py`**（round 6 SA-P4-3：原文只對 8 筆 POSIX 宣稱「全部在」，改成對全 10 筆宣稱後，下輪一旦有別的檔冒出 skip 就立刻看得出漂移，鑑別力更強）。**⚠️ round 5 SA-R58R5-01 訂正（三處錯，且其中一處是把本輪自己消滅的東西寫回基線）**：本處原寫「8 筆 POSIX-only（…／BSD `stat`）、1 筆 symlink、1 筆「本機無 pwsh」、1 筆需 Darwin」——①加總 8+1+1+1＝**11**，與同句宣稱的 10 直接打臉；②「本機無 pwsh」這個 skip 類別**已由本輪 DEF-101-507 親手消滅**（`@skipUnless(shutil.which("pwsh"))` 改為 `_platform_helpers.powershell_exe()`），實測 skip 理由行**零筆**提及 pwsh，卻被當現存事實寫回基線 SSOT，與同 repo 帳本互相矛盾；③BSD `stat` 與「需 Darwin」是**同一筆**，被重複計數。誤植來源可推：歸因清單是從同一行前段的平台揭露句「本機無 pwsh 7」組出來的、不是從 skip log 抄的——**故本節新增紀律：skip 歸因一律以 `-v` 輸出中的 `... skipped` 標記行為唯一來源、並以該標記行為計數單位**——round 6 SD／Architect 各自提醒：第 10 筆（symlink）的理由本身含單引號，unittest 因此改用**雙引號**輸出，照 `grep "skipped '"` 這種寫法複驗只會數到 9 筆而誤判帳本多算一筆。日後若再出現以 pwsh 為由的 skip，即為 DEF-101-507 的回歸。
>   - 〔量測平台：**macOS（對照，本輪未重測）**〕R57 收尾當下記載 `skipped=4`。**此列只有 skipped 有對照價值**——同筆記載的 `Ran` 計數（616）已被本輪新增測試取代而過期，且該筆原始記載**未標註量測平台**（推定為 R57 主要作業平台 macOS，但無法從記載本身確證，見下方 R57 段的 R58 訂正）。macOS 的 skipped 結構性低於 Windows：上列 8 筆 POSIX-only 在 macOS 會實際執行而非 skip。
>   - `MIN_TESTS` 現值 **781**（R58 收輪由 616 重釘；重釘的直接原因是輪次中途實測 771 已越過 `RATCHET_STALE_RATIO`＝616×1.25=770 的保鮮期紅線、`test_current_pin_is_not_already_stale` 翻紅）。最終實測 847 ⇒ 847/781 ≈ 1.085，仍低於 `RATCHET_WARN_RATIO`（1.10），**故收輪不再二次重釘**（下限語意：實況高於下限是正常的，只有漂移過大才需重釘）。R58 中途曾記「現值 616、刻意不動」（該檔不在本段落作者的授權改動清單內——本輪另有並行包在改該檔，故此處只記「查得現值」不做修改；門檻語意見 `tools/run_root_unittests.py` 檔內註解。若收輪重測後實測 ÷ 616 > 1.25，保鮮期斷言會讓閘門變紅，屆時須由收尾角色重釘）。
> - **AutoClaude `tests/`**〔量測平台：**原生 Windows 11 Pro 10.0.26200**、`.venv/Scripts/python.exe` Python 3.11.9、`PYTHONDONTWRITEBYTECODE=1`、Claude Code session 內（帶 `PYTHONUTF8=1`）〕**3775 passed / 208 skipped**（**收輪定案值**，71.28s，由主控在所有並行 agent 停工後一次性實跑 `cd AutoClaude && ../.venv/Scripts/python.exe -m pytest tests/ -q`）。〔量測平台：**macOS（R57 對照，本輪未在該平台重測）**〕R57 記載 **3738 passed / 210 skipped**。**兩組不可直接相減**：passed 差 +37 來自本輪新增測試（`test_perception.py` 的 `%VAR%` 家族等），而 **skipped 差 −2（210→208）本身就是平台訊號**——mac 上會 skip 的 Windows 專屬項在此會跑、反之亦然，故本節規則要求 skipped 必須成對記錄且標平台。**R58 round 2 SA-R58R2-02 訂正**：本節原記「本輪未重測 AutoClaude、現行值 3738/210@macOS」，但本輪確實存在可重現的原生 Windows 量測（複審者亦獨立複現），round 1 的 P1 只修了三組基線中的兩組。
> - **AISDLC_SDD `scripts/tests/`**〔量測平台：**原生 Windows 11 Pro 10.0.26200**、`.venv/Scripts/python.exe` Python 3.11.9、`PYTHONDONTWRITEBYTECODE=1`、cwd＝`AISDLC_SDD/`（即 `scripts/ci-gate.sh` 的 `REPO_ROOT`）〕**247 passed / 1 skipped / 35 subtests passed**（**收輪定案值**，30.97s；**動工前（HEAD）基線為 245 passed / 1 skipped / 23 subtests passed**，差額＝**+2 passed／+12 subtests**，全部來自本輪對 `scripts/tests/test_component_sanitizer_reserved_trailing_space.py` 的擴充（`CONIN$`／`CONOUT$` 保留裝置名，DEF-101-478 家族）——該目錄本輪**只動過這一支**。**⚠️ round 4 SA-R58R4-02 訂正**：本處原被收輪回填的無腦全域字串替換連帶蓋成「輪次中途值」**與定案值同一組數字**（並插注「原為中途值」）——差額恆 0，卻同句聲稱有差額，自我打臉且陳述了不存在的歷史。round 3 SA-R58R3-02 已抓到同一次替換在根層那列造成的同款遺害，當時只修被點名的那一列、未整組掃過姊妹列（**教訓：收輪回填是「三組數字」的整組作業，逐項修 reviewer 點到的那一句必然漏姊妹列**）。上述動工前基線**不是沿用複審者提供的數字**，而是把該檔還原成 `git show HEAD:` 內容後重跑 `scripts/tests/` 實測所得（觀測輸出：`245 passed, 1 skipped, 23 subtests passed in 33.11s`）（`cp` 備份 + md5 核對還原，未用任何 git 還原指令）；複審者建議文字把差額歸因給 `test_ci_paths_cover_root_consumers.py`，而 `git status` 證實該檔本輪未被觸及，故未採用其歸因）。1 筆 skip 已歸因：`scripts/tests/test_install_post_commit_exec_bit.py:48`「Unix chmod 分支在 Windows 不可達」——屬平台閘門，非測試退化。**取代 R57 記載的裸「244」**（無 skipped、無平台標註，違反本節規則 1／2）。
> - **誠實揭露（本段涵蓋面，三段式）**：**已實測**＝上列**三組**（根層 847/10、AutoClaude 3775/208、AISDLC_SDD 247/1/35）皆為本輪在原生 Windows 11 上真跑，但**量測者不同**——根層與 AutoClaude 由主控在所有並行 agent 停工後親跑（本段落作者未重跑，因並行輪次禁跑全套以免互踩假紅，見上方⚠️）；AISDLC_SDD `scripts/tests` 由本段落作者親跑並重跑一次確認可重現。**R57 記載的 `3738 passed / 210 skipped`（macOS、巢狀 session、乾淨 venv）自本輪起降為歷史對照，不再是現行值**——現行值為上方的 3775/208〔原生 Windows〕。**已實測不涵蓋**＝AISDLC_SDD 的 `v0.01`／`v0.30` 兩軌本輪未重測，仍以 R57 記載為準；macOS 側本輪完全未量測（本機為原生 Windows）。**未窮舉**＝macOS 側本輪完全未量測（本機為原生 Windows），故上列 macOS 對照列是歷史記載＋推定，不是本輪證據。
>
> 註：**R57 校正（2026-07-27，五維掃描 18 項候選＋四包並行修復＋四方複審）**——本輪 AutoClaude pytest 基線於**全新臨時目錄建立的乾淨 venv**（`/opt/homebrew/bin/python3.11 -m venv` + `uv pip install -e '.[dev,notifications]'`；污染檢查改用 R56 教訓所訂的「乾淨時會印出東西」寫法 `python -m pip list | grep -E "psycopg2|sqlalchemy"` → 零輸出確認乾淨）下量測，結果為 **3738 passed / 210 skipped**（77.00s，量測平台：macOS、巢狀 Claude Code session），**與 R56 相同不變**——本輪唯一動到 `autoclaude/` 的修復是 `utils/logger.py::_sanitize_log_filename` 的保留裝置名尾隨空白缺口（DEF-101-478 第 ④ 處），其回歸鎖依「三方交叉鎖同檔並列」慣例放在根層 `tools/tests/test_windows_forbidden_filename_parity.py`，不計入 AutoClaude 側數字。其餘子專案數字（不計入本節 AutoClaude pytest）：根層 `tools/run_root_unittests.py` **616 tests OK/skipped=4**〔**R58 訂正①（平台標註缺失）**：本筆違反同節下方 R37 段落自訂的「量測聲明皆須標註平台」規則——原文未標，且把平台相依的 skipped 壓成無標註的單一 scalar。依 R57 主要作業平台推定為 macOS，但**無法從記載本身確證**，故本筆的 `skipped=4` 只能當「非 Windows 平台的歷史對照」，不可當跨平台通用值；原生 Windows 11 的成對值見上方 R58 校正段〕（R56 為 530，本輪 **+86**，`MIN_TESTS` 同步重釘為 616）；AISDLC_SDD `bash scripts/ci-gate.sh` 全綠，逐軌 v0.01:1478／v0.30:1729／scripts/tests:**244**〔**R58 訂正①（同上）**：裸 244＝無 skipped、無平台標註，違反本節規則 1／2；原生 Windows 11 的三欄成對值見上方 R58 校正段（**round 4 SA-R58R4-01 訂正**：本註原把三欄數字**複製一份**寫在這裡，正是本節規則 4 所警告的「第二個家」形狀；而且複製的那組是**動工前基線**、不是它自己所指向的 R58 校正段**定案值** ⇒ 讀者順著指針走會拿到互相打臉的兩個數字。依「數字只准住一個家」政策改為**純指針**，與同行前段根層那筆的寫法一致。**本訂正註刻意不重述那組數字**——若在此複寫，就等於一邊引用該政策一邊再造一個第二個家）〕（R56 為 238，本輪 +6）。**逐項支數刻意不細列到個位數**——R57 三度以算式推算根層測試數（552／558／584）皆當場與實況不符（SD-R57-01／QA-R57-07 抓出兩次；四方複審共三輪、每輪修復都會再增減測試，故最終值 **616**〔**R58 訂正②（同行自相矛盾）**：原文此處誤植為 615，與同一行前段「616 tests OK」及「`MIN_TESTS` 同步重釘為 616」直接打臉；以程式碼為準——`tools/run_root_unittests.py` 的 `MIN_TESTS = 616`，且該行註解明載「取其印出的『發現 N 個測試』直接填入」，故 616 才是 R57 收尾實測值、615 為誤植。**教訓**：這處誤植偏偏長在「不得以算式推算、須填實測值」這段方法論說明裡面——方法論寫對了、同一句話的舉例數字仍抄錯，可見「數字只准住一個家」的鎖對「同一個家裡自己前後矛盾」無鑑別力，見本節開頭規則 4〕亦是收尾當下實測而非累加），`MIN_TESTS` 的重釘判準已明定為「所有並行 agent 停工後，填最終工作樹實測值、不做任何加減推算」，本節敘述同此政策；欲知逐檔增量請直接 `git diff --stat`。`AutoClaude/tools/check_loc_budget.py` total=20356／cap=20438／violations=0（不變——本輪 `logger.py` 只增註解不增邏輯行）。**本節四組數字皆為所有並行 agent 停工後、由主控在最終工作樹上一次性重測所得。**
>   - 🔴 **收尾順序紀律（R58 round 11 立，因主控把順序做反而讓 §7 記著一個已作廢的綠燈）**：收輪必須依序＝**①寫完所有文件（含缺陷帳本各輪紀錄列）→ ②才跑全套取證 → ③才回填本節數字**。round 11 的實例：主控先量到根層全綠、再寫帳本列，而**那一列的文字本身讓一支新落地的守門測試翻紅**（該鎖的判別式把「描述本鎖的散文」誤判成宣稱），於是§7 記著「OK」而實況是 `FAILED (failures=1)`。R58 round 9 已為**位元數**訂過同款紀律（「同一列內不得記載會被本列自身寫入動作改變的量測值」），round 11 證明它必須擴及**任何會被文件寫入改變的量測——測試結果也算**。
>   - **LOC 治理（R58 校正，round 5 SA-R58R5 P4 補記）**：`AutoClaude/tools/check_loc_budget.py` → `total=20385 baseline=17032 cap=20438 violations=0`（原本 §7 只記 pytest 三組、未記 LOC，於是順讀下去最近一處 LOC 記載是 R57 的 `total=20356`＝已過期值當現行值）。**注意該工具 `SCAN_ROOT="autoclaude"`**，故根層 `tools/`／`tools/tests/`**完全不在 LOC 治理面內**——本輪新增的鎖模組已逾姊妹子專案奉為絕對紅線的 750 行，**未違反任何生效規則**（根層無此規則），但屬 ADR §6.3 已記載之 LOC 治理缺口的具體化，round 5 Architect 建議 R59 決定根層 `tools/` 要不要納管。
>
> 註：**R56 校正（2026-07-27，四方複審 round 1~5 共 5 輪、修復 50+ 項＋主控收尾包新增測試回填）**——本輪 Workflow 五維掃描＋四方（Architect/SA/SD/QA）**連續五輪複審**（round 1/2/3/4 皆四方全數 REJECT，round 5.2 收斂為 SD/Architect APPROVE ＋ SA/QA 各餘 P4/P3 一項，由主控修畢後最終複核），詳見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-101-437 起各列。期間 round 3 的 root 領域修復包與 round 4 原班四方 agent 曾撞上 session 用量上限夭折，由主控於上限重置後另派分域修復包與四方重新複核補完。於**全新臨時目錄建立的乾淨 venv**（`/opt/homebrew/bin/python3.11 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`／`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，結果為 **3738 passed / 210 skipped**（78.57s，量測平台：macOS、巢狀 Claude Code session），較 R55 基線 3713 多 +25（本輪各修復包新增之回歸測試，含 round 5 為 LOC 預警帶補的 `tests/contract/test_loc_budget_tiered.py` 三支鎖），skipped 210 不變。**誠實揭露一項主控本輪自身的量測方法論失誤**：動工前的污染檢查誤用 `python3 -c "import psycopg2" 2>&1 | tail -1` 寫法——成功 import 時「零輸出」，被誤讀為「乾淨」，實際上根層共用 `.venv` 確有 psycopg2 2.9.12＋SQLAlchemy 2.0.51；該錯誤基線一度寫入四方任務書，並在收尾時於受污染 `.venv` 量得 **3829 passed / 146 skipped**（skipped 自 210 驟降 64＝PG-gated 測試由 skip 轉 pass 的典型虛高），因 skipped 異常才觸發警覺、回查證實污染並棄用該數字。此為 R13／R32 同族教訓的第三次復發（前兩次是「用錯 venv」與「既有 venv 渾然不覺被污染」，本次是「檢查手法本身無鑑別力」）；已記入缺陷帳本，往後污染檢查一律改用在乾淨環境會**印出東西**的寫法（如 `python3 -m pip list | grep -E "psycopg2|sqlalchemy"`），判準是「輸出在乾淨與污染下長得夠不夠不一樣」，而非「指令有沒有報錯」。其餘子專案數字（不計入本節 AutoClaude pytest）：根層 `tools/run_root_unittests.py` **530 tests OK/skipped=4**（R55 為 496，本輪 +34：含 `test_ps51_compat.py` 7 支〔PS 5.1 語法機械鎖，新檔；R56 round 6 SD／SA 交叉訂正——原記 6 支漏算 round 5 為三元判準新增的 `test_ternary_pattern_does_not_flag_where_object_alias`〕、`TestStubAnchorDiscriminatingPower` 7 支〔WindowsApps 雙錨鑑別力常駐鎖〕、`.ps1` 掃描面三向互鎖與 `test_ps1_bom` 第四處互鎖各 1 支、round 6 為「雙錨聯集」補的 `test_union_catches_{name,predicate}_only_reinvention` 2 支等）；AISDLC_SDD `bash scripts/ci-gate.sh` 全綠，逐軌 v0.01:1478／v0.30:1729／scripts/tests:238。**本節三組數字皆為所有並行 agent 停工後、由主控在最終工作樹上一次性重測所得**（round 5 期間曾出現 3731/518 → 3738/528 的中途快照，均已被本次量測取代）。
>
> 註：**R55 校正（2026-07-27，四方複審 round 1+round 2 修復包新增測試回填；round 3 覆核於背景執行中經使用者明確指示中止，改由主控親自收尾驗證，見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-101-436）**——round 1（root 領域）新增 `tools/check_gha_action_versions.py` GitHub Actions 版本一致性機械鎖＋修復 `tools/macos_smoke_local.sh` WindowsApps guard 缺口（DEF-101-426/427/428）；round 1（autoclaude 領域）新增 `AutoClaude/autoclaude/utils/shell_deny_chars.py` 收斂 shell 注入黑名單 SSOT（DEF-101-238／DEF-101-429），新增 `AutoClaude/tests/test_shell_deny_chars_parity.py` 3 條回歸測試；round 2 修復 `check_gha_action_versions.py` 自身兩項掃描邊界缺口（DEF-101-430）。主控於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下對全部修復落地後的工作樹重跑，結果為 **3713 passed / 210 skipped**（96.90s），與 3710+3=3713 精確吻合，skipped 210 不變，故本節數字更正為 3713。**誠實揭露**：round 2 QA／SA 各自在其獨立全套 pytest 重跑中皆遇過一次 `test_shell_deny_chars_parity.py::test_goal_freeze_gate_deny_is_superset_of_base` 不可重現的偶發失敗（判定為多個審查子代理共用同一份工作樹時的瞬間並行雜訊，同 DEF-101-217 已記載模式），主控本次全新乾淨 venv 重跑（單一行程、無並行 agent 干擾）未重現此現象，結果乾淨。
>
> 註：**R53 校正（2026-07-26，四方複審 round 2 收斂：round 1 修復包新增 2 條回歸測試未回填，另揪出 `AutoClaude/tools/check_loc_budget.py` 連續第二輪逼近上限）**——本輪 Workflow 五維掃描＋四方（Architect/SA/SD/QA）round 1 一致確認 `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py`（`_EVALUATOR_TEMPLATES` 白名單死碼，DEF-101-413）與 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`（盲區 D 登記不全＋`_JOIN_RE`/`_SLASH_RE` 正則不對稱，DEF-101-414）兩組缺陷，另由 SD 主動查獲 `AutoClaude/autoclaude/evolution/_evaluator_derivation.py` 偵測/擷取判準不等價（DEF-101-415，R52 DEF-101-408 修復不完整之邊界復發）；round 1 修復包在 `tests/test_gap021_028.py` 新增 2 條參數化回歸測試。主控於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下對 round 1 修復全部落地後的工作樹重跑，結果為 **3710 passed / 210 skipped**（89.75s），與 3708+2=3710 精確吻合，且與 round 2 QA 獨立在乾淨 venv 下的量測一致，故本節數字更正為 3710。同輪 SD／QA 交叉發現 `AutoClaude/tools/check_loc_budget.py` `autoclaude/` 總量現為 `total=20438=cap=20438`（violations=0，但安全邊際自 R52 收斂後的餘 7 行完全耗盡至 0，連續第二輪逼近上限，DEF-101-416）——主控裁定不做投機性精簡通過中的程式碼，如實記入缺陷帳本 watch item，留待下一輪視是否再度命中決定是否啟動 ADR-SD07-001 §6.2 調升基線程序。四方 round 2 一致 APPROVE，收斂完成。
>
> 註：**R52 最終校正（2026-07-26，四方複審 round 4 收尾複核：round 3 自陳「最終 commit 前需再重驗一次」已完成）**——下方「R52 round 3 校正」段落記載 3699 passed / 210 skipped，但該次量測早於 round 3 稍後疊加的其餘修復包（`autoclaude/evolution/_evaluator_derivation.py` token-index 修正＋`tests/test_gap021_028.py` 新增測試、`autoclaude/artifact_check.py` console script 修復＋`tests/tools/test_run_bridge_e2e.py`／`tests/tools/test_three_tier_to_playbook.py` 新增測試），未被 3699 涵蓋。第 4 輪四方（Architect/SA/SD/QA）各自獨立在全新乾淨 venv 下重跑，皆穩定測得 **3708 passed / 210 skipped**（四方交叉印證一致，非單一來源）；同輪 Architect/SD/SA/QA 另交叉發現「round 1~3 六筆修復合併後 `AutoClaude/tools/check_loc_budget.py` 總量 cap 被突破」（`autoclaude/` 淨增 +151 行，total 20451 > cap 20438），已由收尾複核精簡兩處說明性 docstring（`_simple_mutations.py::_default_fallback_evaluator_command`／`artifact_check.py` 模組 docstring，皆為純文字精簡、無邏輯變動）收斂回 total=20431（cap 20438，餘 7 行），並重新在**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下對「R52 全部修復（round 1~3 六筆＋收尾 LOC 預算精簡）皆已落地」的最終工作樹重跑一次，結果同為 **3708 passed / 210 skipped**（90.78s，skipped 210 不變，與四方量測一致），故本節數字更正為 3708，為本輪（R52）commit 前最終值。
>
> 註：**R52 round 3 校正（2026-07-26，四方複審 round 3 收斂：round 2 的「R52 校正」段落本身在其量測時點之後，同一 round 2 稍後套用的第 3 筆修復又新增測試未回填）**——下方「R52 校正」段落已將基線訂正為 3697 passed / 210 skipped（3682+15），但該次量測早於／未涵蓋同一 round 2 稍後套用的第 3 筆修復——`AutoClaude/autoclaude/execution/mutation_applier/_simple_mutations.py` 的 encoding 修復在 `AutoClaude/tests/test_playbook_runner.py` 新增的 2 個測試函式（`test_r52_fallback_evaluator_src_subprocess_has_encoding`、`test_r52_fallback_evaluator_src_handles_non_ascii_filename`），未被計入；該段落文字本身已誠實揭露此風險（「若本輪（R52）後續仍有其他並行修復包新增測試案例，此數字在最終 commit 前仍須再重驗一次」），本次複審（Architect/SA/SD 三方獨立指出同一落差）即為該風險的具體發生實例。於本輪（round 3）在**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，結果為 **3699 passed / 210 skipped**（skipped 210 不變），與 3697+2=3699 精確吻合，故本節數字更正為 3699，延續既定方法論。**已知限制（誠實揭露，本輪加重）**：驗證過程中親自觀察到——第一次量測得 3699 之後，緊接著在同一 R52 round 3 內（其他並行修復包仍持續作業中）工作樹已再度變動（`git status --short` 顯示新增異動 `autoclaude/evolution/_evaluator_derivation.py`、`tests/test_gap021_028.py`），第二次重跑已變為 3705 passed。此為即時、可重現的實況示範：「多支修復包並行、單一 agent 事後局部重驗＋回填」的協作模式，對這種需橫跨全部並行修復包才能算準的全域數字，**結構上無法在輪次進行中途收斂**；3699 僅代表本次量測當下的快照，**本輪（R52）最終 commit 前務必由收尾複核角色在所有並行修復包全部落地後再做最後一次重驗**，方可視為最終值。
>
> 註：**R52 校正（2026-07-26，四方複審 round 2 收斂：round 1 六筆修復合併後 SSOT 基線再度落後 +15 未回填）**——round 1 第 1 個修復包曾針對「R51 commit（`35a53f9`）在 `AutoClaude/tests/test_gap021_028.py` 新增 2 個 `test_derive_part_a_evaluator_uses_sys_executable_not_bare_python` 測試函式卻未同步回填本節數字，致 R50 記載的 3680 落後實測 +2」回填為 3682 passed / 210 skipped，但該次量測早於／獨立於同輪其餘五筆並行 P1/P2/P3 修復包——`AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py` +2、`AutoClaude/tests/test_gap009.py`（對應 `pre_run_validator.py`/`boot_helper.py` 修復）+6、`AutoClaude/tests/tools/test_three_tier_to_playbook.py`（對應 `three_tier_to_playbook.py` 修復）+5、`AutoClaude/tests/test_playbook_runner.py`（對應 `mutation_applier` 修復）+2，合計 +15——這些修復包各自也新增了測試，故 3682 在六筆修復全部併入工作樹後已再度落後。四方複審（Architect/SD/QA 三方獨立指出同一落差）於 round 1 六筆修復全部套用後的當前工作樹，在**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下重跑兩次（73.63s／75.73s），結果穩定為 **3697 passed / 210 skipped**（skipped 210 不變），與 3682+15=3697 精確吻合，故本節數字更正為 3697，延續 R32/R37/R47/R48/R50 既定方法論。**已知限制（誠實揭露）**：本數字僅代表「round 1 六筆修復全部套用完畢、本次量測當下」的工作樹快照（量測前後以 `git status --short` 核對僅列出上述六筆檔案異動，無其他變更）；若本輪（R52）後續仍有其他並行修復包新增測試案例，此數字在最終 commit 前仍須再重驗一次，不可視為絕對最終值。
>
> 註：**R50 校正（2026-07-26，四方複審修復輪：SPLIT_STEP Part A evaluator 跨平台安全寫法＋SSOT 收斂等套件新增測試）**——巢狀 Claude Code session（`CLAUDECODE=1`，量測平台：macOS）下 full pytest 實測基線更新為 **3680 passed / 210 skipped**（較 R48 基線 3669 passed 多 +11，即本輪 `AutoClaude/tests/test_gap021_028.py`／`test_playbook_runner.py` 新增之 POSIX-only evaluator_command 跨平台回歸測試＋`TestGap026CSharedEvaluatorDerivationSSOT` SSOT 收斂測試，skipped 210 不變）。本次同樣於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，且**動工前已先核實根層共用 `.venv` 確實已受 psycopg2/SQLAlchemy 污染**（`import psycopg2` 成功、該 venv 下量測為 3778 passed / 146 skipped，與本節方法論不符故未採用）故延續 R32/R37/R47/R48 既定方法論。本輪另三項修復（DEF-101-395 CI paths 盲區C／DEF-101-396 nightly heartbeat 跨站行為等價＋git-longpaths 旗標鎖）分別落在 `AISDLC_SDD/scripts/tests/`（227 passed，較 R48 基線 226 +1）與根層 `tools/tests/`（486 passed／4 skipped／40 subtests passed），均不計入本節 AutoClaude pytest 數字（詳見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-101-394~397）。
>
> 註：**R48 校正（2026-07-26，DEF-101-390 `CheckpointManager.checkpoint_path()` 淨化修復新增測試）**——巢狀 Claude Code session（`CLAUDECODE=1`，量測平台：macOS）下 full pytest 實測基線更新為 **3669 passed / 210 skipped**（較 R47 基線 3667 passed 多 +2，即本輪 `tests/test_token_checkpoint.py::TestCheckpointManager` 新增的 2 條 `checkpoint_path()`/`save()` 檔名一致性回歸測試，skipped 210 不變）。本次同樣於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，且**動工前已先核實根層共用 `.venv` 確實已受 psycopg2/SQLAlchemy 污染**（`import psycopg2` 成功、該 venv 下量測為 3767 passed / 146 skipped，與本節方法論不符故未採用）故延續 R32/R37/R47 既定方法論；小幅修正（ruff line-length）後重跑一次數字一致，非單次偶然。本輪另兩筆缺陷修復（DEF-101-389 install_post_commit.ps1 反斜線正規化、DEF-101-391 windows-compat-ci.yml paths 補齊）分別落在 AISDLC_SDD 子專案與 GitHub workflow 設定，均不計入本節 AutoClaude pytest 數字（AISDLC_SDD 側 `bash scripts/ci-gate.sh` 驗證結果見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-101-389 列）。
>
> 註：**R47 校正（2026-07-26，本輪四方複審修復輪 docs/defect-log 收尾套件重新量測）**——巢狀 Claude Code session（`CLAUDECODE=1`，量測平台：macOS）下 full pytest 實測基線更新為 **3667 passed / 210 skipped**（較 R37 基線 3,653 passed 多 +14，累積自 R38～R47 各輪新增測試；skipped 210 不變）。本次同樣於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，且**動工前已先核實根層共用 `.venv` 確實已受 psycopg2/SQLAlchemy 污染**（`import psycopg2` 成功）故未採用其數字，延續 R32/R37 既定方法論；重跑兩次數字一致（78.71s／66.72s），非單次偶然。**誠實揭露一項差異**：本輪修復套件之一（r2，`file_state_repository.py` 檔名淨化）本身新增了測試，理論上會讓本次量測值內含該輪新增測試，故 +14 之中有一部分屬本輪貢獻而非純粹「R38～R46 累積未回填」；未單獨拆分兩者佔比，如實記載供未來參考。
>
> 註：**R37 校正（2026-07-24，`EscalationDump.save()` 檔名淨化修復新增測試）**——巢狀 Claude Code session（`CLAUDECODE=1`）下 full pytest 實測基線更新為 **3,653 passed / 210 skipped**（較 R33 基線 +9，即本輪 `tests/test_models.py`／`tests/plugins/test_checkpoint_plugin.py` 新增的 9 條 Windows 禁用檔名淨化＋超長 step_id fallback＋`/` 路徑穿越淨化回歸測試，skipped 數不變）。本次數字同樣於**全新臨時目錄建立的乾淨 venv**（`python3 -m venv` + `pip install -e '.[dev,notifications]'`，`import psycopg2`/`import sqlalchemy` 皆 `ModuleNotFoundError` 確認乾淨）下量測，非既有共用 `.venv`——本輪動工前已先核實根層共用 `.venv` **確實已受 psycopg2/SQLAlchemy 污染**（`import psycopg2` 成功），故未採用其數字，改建全新乾淨 venv 量測，延續 R32 教訓的既定方法論。**R42 SA 一審補記**：本則量測平台未於當時記載（原文未標註 Windows/macOS/Linux）；本輪起比照以下範例格式（如「量測平台：Windows 11、巢狀 Claude Code session」）於量測聲明中明確標註量測所在平台，後續所有量測聲明皆須標註，不可再省略。
>
> 舊註（**R33 校正，2026-07-24，DEF-101-289 收斂**）——巢狀 Claude Code session 下基線曾為 **3,644 passed / 210 skipped**（R27~R32 累積新增測試案例 `test_run_act_core.py`／`test_bash_probe_spec_contract.py`／`test_bootstrap_ps1.py` 平台守門等皆已反映在此）；當時數字於全新臨時目錄建立的乾淨 venv（`pip install -e '.[dev,notifications]'`，不含 postgres/pgvector 選配，`pip list` 確認乾淨）下量測，非既有共用 `.venv`——R32 曾因既有 `.venv` 意外裝有 `psycopg2`/`sqlalchemy` 選配、PG-gated 測試從 skip 轉 pass 造成數字虛高（3742/146）而擱置未更新，本次已排除此污染。**bootstrap 出廠環境**（非巢狀 session、全新乾淨 venv）數字**本輪未重新量測**——舊數字（3,566 passed / 196 skipped）維持標示為待重驗，需另起一個不在巢狀 Claude Code session 下的全新環境實測後才能校正。（根層 CLAUDE.md 與 AutoClaude 兩檔已於 R13 收斂為指向本節、不再重複數字）。**方法論澄清（R13 校正歷史，供未來重驗參照）**：本欄曾有一版誤標為 3,664/132，經 SA 複審抓出根因是量測時用了主目錄既有、已裝 `[postgres]` 選配（`psycopg2-binary`/`SQLAlchemy`）的 `.venv`，PG-gated 測試從 skip 轉 pass 造成數字虛高，不符本節自稱的「出廠環境」方法論；未來重驗數字時務必改用全新乾淨 venv〔`pip install -e 'AutoClaude[dev,notifications,lint]'`，不含 postgres 選配；**R57 純加引號修正、無數字變動**——zsh 下未加引號會 `no matches found` 中止，見 §5〕。skipped 中屬選配依賴缺席者（PG DSN 未設／sqlalchemy 與 `[postgres]` 未裝／claude_agent_sdk 未裝）為預期，非測試退化。AISDLC_SDD `ci-gate.sh` 的逐軌 passed 計數對 **docker daemon 可用性**敏感（daemon 停用時 v0.01／v0.30 各 -3＝`test_phase_h` 的 docker 場景 SKIP），±3 屬環境因素非退化。

---

## 8. Nightly 排程層（跨平台現況與後續）

AutoClaude 有一套 nightly 取證流程（7 stage：local_ci_gate / mutation / pg-e2e / perf / drift / obs / sdd-fsm-chaos）。**排程自動化現況：Windows 深度版完整可用；macOS 為 R11 新增的薄聚合器（刻意非對等移植，見下）**：

- **Windows（既有，可用；R19 起一鍵化）**：`AutoClaude/tools/run_local_nightly.ps1` 由 Windows 工作排程器 `schtasks` 每日 02:00 觸發（任務名 `AutoClaude_Nightly`）。**R19 前**該任務須手動 `schtasks`/GUI 建立，`AutoClaude/tools/fix_nightly_catchup.ps1` 只能「校正既有任務設定」（`Get-ScheduledTask` 找不到任務即直接拋錯），無法從零建立——與 mac 側 `install_mac_nightly.sh` 的一鍵化體驗不對稱。**R19 新增 `tools/install_windows_nightly.ps1`**（鏡射 `install_mac_nightly.sh` 定位）補上這段：`install`（預設，冪等建立排程＋內建 `fix_nightly_catchup.ps1` 記載的補跑保護設定，新機器不必再另跑一次 fix 腳本）／`-Uninstall`／`-Status`（查詢任務狀態；**R58 擴大其結束代碼語意**＝「主任務存在 **且** 涵蓋清單內各任務〔`$TaskName` + `$AuxTaskNames`，後者含 `AutoClaude_SD09_G0_GateCheck`〕的四項補跑／電源保護設定皆符期望」→ exit 0；任一項漂移或主任務不存在 → exit 1。此前它**印出四項並附 `(expected …)` 卻無條件回傳成功**，使排程漂移在整個 repo 沒有任何會翻紅的路徑（見缺陷帳本 DEF-101-515；同輪另修好一個更隱蔽的問題：該入口因 PowerShell success-stream 被變數指派捕獲而**恆 exit 0 且輸出 0 bytes**，DEF-101-248 宣稱的修復從未生效，見 DEF-101-512）。**本機現況誠實揭露**：`AutoClaude_SD09_G0_GateCheck` 的 `StopIfGoingOnBatteries` 實際仍是 `True`（需提權才能校正，R58 刻意不動使用者機器狀態），故本機 `-Status` 現為 exit 1 並精準指名該項；Windows 工作排程器原生以 `Get-ScheduledTaskInfo` 提供上次執行時間，取代 mac 版讀心跳檔案 mtime 的機制）／`-WhatIf`（PowerShell 內建預覽模式，只印將執行的動作不變更系統）。設定事後校正仍可用 `AutoClaude/tools/fix_nightly_catchup.ps1`。R9 三項強化：①前置新增 local_ci_gate 全套 stage（對齊 `windows-nightly-full` 深度回歸，push 空窗期也有每日全套訊號）；②pg-e2e stage 加跑 PG contract 測試（`tests/contract/test_pg_state_repository_contract.py`，CI 硬閘的本地對等）；③終端 exit code 帶訊號（任一 stage 失敗→exit 1；SKIP/WARN 不計）——schtasks「上次結果」從此可反映 stage 健康，不再恆 0x0。R10 五項強化：④新增 **sdd-fsm-chaos stage**（鏡射 `aisdlc-sdd-fsm-chaos-nightly.yml` 兩步：pytest `-m chaos`＋100 輪 chaos_runner sweep，CI 停擺期間 Rule 9.9.4 的本地補償，實測 <1 分鐘）；⑤pgvector recall pytest rc 以 `[ref]` 捕捉（先前被 collector 覆蓋，單日真紅假綠）；⑥mutmut log 驗證失敗改 rc=1（先前誤設 WARN 級 rc=2，「防假 pass 守門自身觸發」反而綠出場）；⑦Docker 連續 ≥3 次不可用升級為 exit 1（`.docker_skip_streak` 累計；單次 SKIP 仍屬合理）；⑧END 進度 mutation 軌改印 unique-sha 計數（ADR-SD09-011 語意，原始列數會虛報）。全部強化由 `tests/tools/test_run_local_nightly_static.py` 的**靜態錨點測試家族**鎖住（**實際支數以該檔為準，勿在本文件複製計數**——R58 訂正：原文寫死「24 個」，實測該檔現有 28 支 `def test_`，自 R10 記入後每輪新增錨點皆未回填；依本 repo「數字只准住一個家」政策，此處拿掉計數即免除未來回填義務，與 §7 pytest 基線數字收斂為單一站點同政策。要查現況：`grep -c "def test_" AutoClaude/tests/tools/test_run_local_nightly_static.py`）。
- **macOS（R11 已落地薄聚合器）**：`schtasks` 在 macOS 無對應；等價機制是 `launchd`（推薦）或 `cron`。R11 依 Architect D1 拍板落地 `AutoClaude/tools/run_local_nightly.sh`——**薄聚合器**，只串接四支既有腳本、不重寫任何檢查（四 stage：`tools/macos_smoke_local.sh` 強制系統 bash 3.2 ＋ 根層 `tools/run_root_unittests.py` ＋ AutoClaude `tools/local_ci_gate.sh` ＋ SDD `scripts/ci-gate.sh`；任一 stage 失敗記名續跑、結尾彙總、exit 1——對齊 `.ps1` R9 ③ exit 語意），下方 launchd/cron 範本即可直接啟用。**如實揭露：這不是 `.ps1` 的對等移植，而是刻意的薄聚合**——mac 側只要「平台相容性＋回歸」每日訊號（R11 教訓：smoke 全綠 ≠ unittest 全綠，故兩者都必跑），深度 stage（mutation Docker/pg-e2e/perf/obs）維持 Windows 主開發機承載；七軌其餘兩軌去向——drift＝nightly 取證帳本紀律由 Windows 主開發機承載（drift_log_history 例行 commit 即其產物）、sdd-fsm-chaos＝非平台敏感之純 Python 邏輯回歸（Windows 本地 nightly 每日承接＋CI chaos workflow 覆蓋），mac 薄聚合器均不重複。

> ⚠️ **ops 排程家族其餘三支仍 Windows-only**：`run_local_nightly` 已有 `.sh`（R11 薄聚合器，見上；launchd 排程啟用已於 R13 一鍵化——`bash tools/install_mac_nightly.sh`，見下）；但 ops 排程家族其餘三支（`g0_gate_check.ps1`、`reschedule_g0_gatecheck.ps1`、`fix_nightly_catchup.ps1`）仍屬 Windows-only、無 `.sh` 對等，為本節的明示缺口。
>
> ✅ **不同軌的另一層已補上：雲端機械化 CI 安全網（`.github/workflows/macos-compat-ci.yml`）**：上面講的是「開發者個人機器上的排程自動化」缺口；與此無關的是——在本輪之前，macOS 端**完全沒有任何機械化 CI 驗證**（全部 workflow 的 `runs-on` 只有 `ubuntu-latest`／`windows-latest`，macOS 側長期僅靠人工對照與文件宣稱）。Mac/Windows 相容性修復輪新增了 `macos-compat-ci.yml`，補上先前完全沒有的 macOS 機器化覆蓋：**`macos-smoke`**（PR/push 閘門，觸及平台敏感路徑才觸發，實際「執行」而非僅語法解析）涵蓋 `bootstrap.sh`／`dev_start.sh`（含 mac 專屬的 `cross_same_flavor` 分支）、`install_git_hooks.sh`／`install-hooks.sh`（含 linked worktree 拒絕情境）、`install_post_commit.sh` 在 **git worktree** 下的寫入情境、根層 `tools/git-hooks/` 三支 dispatcher 在 macOS **系統內建 bash 3.2**（非 Homebrew 新版）下的直接執行、`AISDLC_SDD/scripts/ci-gate.sh`（凍結基線 v0.01 + LATEST 雙軌）；**`macos-nightly-full`**（`schedule`/`workflow_dispatch`）另跑兩子專案完整測試套件在 `macos-latest` 上的深度回歸。因此「開發迴圈（測試／lint／ci-gate／整合閘門）在 macOS 已對等」現在**有機器驗證佐證**，不再只是文件宣稱——但仍有限制須如實揭露：① `macos-nightly-full` 為 `continue-on-error: true` 非阻斷 job，失敗不擋 PR、僅供事後觀察；② GitHub-hosted `macos-latest` runner 與開發者個人 Mac 的實際硬體／OS 版本仍可能有落差；③ 此 CI 與本節開頭的「本機排程自動化」（launchd/cron）屬不同層次缺口，未被本次新增的 CI 覆蓋，該缺口依然存在。
>
> ✅ **R9 補償控制（DEF-101-081 CI 帳單停擺期間）**：上段 CI 安全網停擺期間，macOS 專屬回歸（bash 3.2 語法、`.sh` 安裝腳本 worktree 防護等）在任何機器上都不會自動跑——R9 新增 `tools/macos_smoke_local.sh`（本地聚合驗證：`bash -n` 全量＋dispatcher 直呼煙霧＋兩支安裝腳本往返/worktree 拒絕＋LATEST `install_post_commit.sh` worktree 與移除後路徑斷言＋NTFS/parity 兩支守門，與 `macos-compat-ci.yml` 對應 step 同步維護），Mac 開發者可手動（或 launchd 排程）執行補位。已於 Windows Git Bash 實跑全綠（R9 當時 10 步全過、FAIL=0）；**真 macOS 實跑已於 R11 補驗關閉**：2026-07-17 真 Mac（macOS 26.5.2 arm64、系統 `/bin/bash` 3.2.57）多次獨立實跑全綠（R11 當時 10 步全過、FAIL=0，R11 修改 `install_post_commit.sh` 後的端到端重驗證據實體＝隔離 clone 疊上變更後 scratch commit 的 smoke [4] 全綠＋v0.30 worktree 回歸鎖 3 tests——本 repo 工作樹 smoke [4] 依設計自 HEAD clone、未 commit 變更不在其驗證範圍；DEF-101-113 殘留正式關閉。腳本另通過 bash 3.2／BSD 工具相容性靜態自查：無 declare -A/mapfile/`${var,,}`、無 sed -i/readlink -f/grep -P/BRE 交替）。R13 新增 [6] launchd plist render＋`plutil -lint` 驗證步、R15 再增 [7] nightly RunId log／RunAtLoad 補跑靜態錨點步（分組標籤同步重編為 /7）後，現行全綠宣稱為 **PASS=13 FAIL=0**（真 Mac 實跑；歷史宣稱之步數為當時快照，僅現行值受 `test_smoke_ci_sync` 文件↔釘選互鎖）。
>
> 🔴 **R11 補驗紀律（DEF-101-149 教訓）**：任一平台聲稱「全綠」，證據**必須含該平台的 `tools/run_root_unittests.py` 輸出，不得只附 smoke 彙總**——R11 真 Mac 首跑即實證兩者可分歧（smoke 彙總全綠的同時，根層 unittest 有 2 個 Windows 假路徑案例在 POSIX 假紅）；smoke 驗「平台載具」、unittest 驗「工具鏈邏輯」，缺一不可。
>
> ✅ **R24 對稱補揭露（DEF-101-265）／R54 訂正（版本號過期，見缺陷帳本 R54 條目）**：mac 側（本節上方 macos-compat-ci.yml 段落 ②）已明文揭露「GitHub-hosted `macos-latest` runner 與開發者個人 Mac 的實際硬體／OS 版本仍可能有落差」，但 Windows 側先前未有對等句——本節標題與 `windows-compat-ci.yml` 檔頭皆明確宣稱「Windows 11 相容性」，落差反而更該揭露。**R24 原文曾寫死「現行對應 Windows Server 2022」，該版本號已於寫入當下（2026-07-23）就已過期**（GitHub 已於 2025-09-02～09-30 遷移至 Windows Server 2025、2026-06-08～06-15 further 更新工具鏈預設為 VS2026，見 `actions/runner-images` 官方 issue #12677／#14016／#14017）——教訓：`runs-on: windows-latest` 為浮動標籤，任何在本文件內寫死當下具體版本號的揭露手法都會隨 GitHub 未來持續演進 runner image 而再度過期，且無機械鎖能偵測此類文字漂移（不同於 pytest 基線有 `check_pytest_baseline_sites.py`）。改採不會過期的措辭：**GitHub-hosted `windows-latest` runner 對應的伺服器 SKU／工具鏈版本會隨 GitHub 官方排程持續演進（並非用戶端 Windows 11），如需查證現況請見 [`actions/runner-images`](https://github.com/actions/runner-images) 官方 issue tracker／changelog，不要依賴本文件內任何寫死的版本號**；兩者在預設 PowerShell 執行策略、部分系統服務行為、電源管理／排程相關 API（本節高度倚賴的 `schtasks`／`New-ScheduledTaskSettingsSet`，見 DEF-101-002／249）等面向仍可能有出入。此為文件揭露補強，非程式邏輯變更。
>
> ✅ **R10 Windows 側對等補償（DEF-101-139）**：對稱地，`windows-compat-ci.yml` 的「執行級」`.ps1` 驗證（install 兩腳本 worktree 拒絕、LATEST `install_post_commit.ps1` worktree 實跑＋移除後路徑斷言、非 ASCII 路徑安裝）同樣只活在停擺的雲端、SDD 回歸測試明文只鎖 `.sh` 版——R10 新增 `tools/windows_smoke_local.ps1`（本地聚合驗證，PASS=12：active `.ps1` Parser 全量＋fake repo＋`install_git_hooks.ps1`／`install-hooks.ps1` 往返與 worktree 拒絕＋LATEST `install_post_commit.ps1` worktree 實跑＋中文路徑（`煙霧測試`）安裝抽驗＋R27 新增 `[7/9]` linked worktree 拒絕於「-Command 非典型呼叫鏈」下仍生效（訂正 DEF-101-263④「全庫零命中、純理論性」之過度樂觀判定，實測重現並修復 `tools/lib/GitHooksInstallCommon.ps1` 呼叫棧判斷只看最外層 frame 的缺陷）＋R18 新增 `[8/9]` `check_ntfs_paths.py`／`check_script_parity.py` 兩支機械檢查（消除先前僅 macOS smoke 單邊覆蓋的不對稱）＋R20 真 Windows 機器複審新增 `[9/9]` `install_windows_nightly.ps1 -WhatIf` 預覽（R19 新增此安裝器後從未被任何 smoke 涵蓋，同輪真機實測揪出該安裝器 `New-ScheduledTaskSettingsSet` 呼叫使用不存在的參數名之 P1 缺陷，見 DEF-101-249）；PowerShell 5.1 實跑全綠；LATEST 解析走 `AISDLC_SDD/scripts/sdd_version.py` 單一真相源）。兩平台 smoke 自此對稱：macOS＝`macos_smoke_local.sh`、Windows＝`windows_smoke_local.ps1`。

macOS 排程啟用（R13 一鍵化）：`bash tools/install_mac_nightly.sh`（安裝並載入 launchd；`--status` 查排程與心跳三態、`--uninstall` 移除、`--render-only <路徑>` 僅產 plist 驗證不載入——smoke [6/6] 即用此模式）。安裝器產出等價於以下 `launchd` 範本（`run_local_nightly.sh` 已就緒）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- ~/Library/LaunchAgents/com.autoclaude.nightly.plist（範本；run_local_nightly.sh 已就緒）-->
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
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/absolute/path/to/AISDCL_Agent/AutoClaude/logs/nightly_mac_launchd.log</string>
  <key>StandardErrorPath</key><string>/absolute/path/to/AISDCL_Agent/AutoClaude/logs/nightly_mac_launchd.err</string>
</dict>
</plist>
```
安裝（範本）：`launchctl load ~/Library/LaunchAgents/com.autoclaude.nightly.plist`

或 cron：`0 2 * * * /bin/bash /absolute/path/.../run_local_nightly.sh`

> ✅ **R12 nightly 心跳哨兵（ARCH-R12-2）**：排程層活性此前零機械查核（launchd/schtasks 是否真的在跑，斷載零訊號——CI 停擺期間 nightly 是唯一每日兜底層，缺位比 CI 活著時嚴重一級）。R12 起：`run_local_nightly.sh` 結尾（成功/失敗皆）寫心跳檔 `AutoClaude/logs/nightly_mac_latest.log`（Windows 深度 nightly 既有 `logs/nightly_latest.log` 即其心跳）；`dev_start` 步驟⑥平台健檢依平台檢查對應心跳檔——**缺席→提示行（排程可能未啟用，或已安裝但尚未跑過第一輪，指路本節）；mtime 超過 8 天→advisory 警告（排程曾在跑但斷載的靜默失效訊號）；皆不阻擋**。跨機限制如實揭露：心跳檔是本機 untracked 產物，只能守「本機」排程活性，Windows 機斷載仍須在該機 dev_start 時才會被提示（與 DEF-101-148「本機副作用類宣稱綁定該機器」同性質）。

> ✅ **R15 關機錯過補跑＋RunId log（SCAN-C-1／DEF-101-201②；R16 訂正睡眠/關機根因區分）**：launchd `StartCalendarInterval` 的原生語意是「時點觸發」，但**睡眠與關機的補跑保障不同**——依 `man launchd.plist` 明文：「Unlike cron which skips job invocations when the computer is asleep, launchd will start the job the next time the computer wakes up. If multiple intervals transpire before the computer is woken, those events will be coalesced into one event upon wake.」即**睡眠情境 launchd 原生就會在喚醒時補跑並合併多次錯過的觸發，不需額外機制**；真正沒有原生補跑保障的只有**關機**（daemon 本身不存在，無法排入喚醒後補跑）。R15 加的 `RunAtLoad` 修法對兩種情境皆有效（不會造成功能性傷害），僅此段先前的 rationale 誤把「關機」與「睡眠」歸為同一種零補跑情境（Windows 側同型缺陷已以 `StartWhenAvailable`＋`WakeToRun` 修復，事故引文見 `AutoClaude/tools/fix_nightly_catchup.ps1` 檔頭）。R15 起：①plist（安裝器 heredoc 與上方範本皆是）加 `RunAtLoad`——開機/載入即觸發＝補跑窗口；②載體 `run_local_nightly.sh` 開頭做**當日去重**（心跳檔 mtime 日期＝今日→印去重行後 exit 0；手動重跑 `--force` 繞過）——RunAtLoad 語意因此成為「載入時若今日尚未跑過才補跑」，等價 Windows `StartWhenAvailable` 且冪等重裝/多次開機不重複跑。同輪起 mac nightly 具 **RunId log**：輸出 exec 改道 `AutoClaude/logs/nightly_mac_<時間戳>.log`（BEGIN 首行帶 run_id；保留 14 天，心跳寫完後自動輪替），心跳檔彙總行之後（FAIL>0 時多一行失敗 stage）附 `log=<RunId log 路徑>` 末行指標（**前 2 行三站點契約不變**）——取證自此「心跳＝最新指標、RunId log＝完整實體」，mac 側 PASS 聲稱可依取證紀律 #3 引 RunId log:L；launchd log（`nightly_mac_launchd.{log,err}`）輪替明確不做（輸出改道後只剩 exec 前啟動錯誤，自限量，ARCH-R14-REV-2）。

> ✅ **R16 觸發歸因＋去重鎖競態修復（DEF-101-225）**：R16 掃描時，同日兩輪皆完整跑滿 4 個 stage（FAIL=0）因缺「觸發來源」欄位無法單靠 log 本身歸因是合理手動重跑還是去重漏洞——`run_local_nightly.sh` 起補兩項：①**BEGIN 行加印 `trigger=<TRIGGER_SRC>`**（四態：`manual-force`＝`--force` 呼叫／`launchd(XPC_SERVICE_NAME=...)`＝launchd 排程觸發／`manual-interactive`＝互動終端機直接執行／`non-interactive-unknown`＝其他非互動來源）；②**心跳 mtime 當日去重判斷前置一道 POSIX `mkdir` atomic lock**（鎖目錄 `AutoClaude/logs/.nightly_mac.lock`；本機查無 `flock`/`shlock` 保證可用，改用同路徑 `mkdir` 具原子性的 pattern）——修復原去重判斷本身是 check-then-act：launchd `RunAtLoad` 與 `StartCalendarInterval` 兩觸發源、或手動重跑與排程時間點重疊時，兩個行程可能同時通過「今日尚未有心跳」的檢查，導致重複跑一整套 4-stage gate 的 TOCTOU 競態窗口。陳舊死鎖（鎖檔內 PID 已死或缺失）以 `kill -0` 判活性後清除並重試一次；`trap EXIT` 確保鎖在正常結束或異常中斷時皆釋放。

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
| **跨樹掃描守門「住所」與「掃描面」錯位**（ARCH-R13-REV-3）：平台中立假路徑（四樹）與 subprocess encoding（十樹）兩守門住在根層 `tools/tests/`，掃描面卻跨兩子專案；根層 pre-push 只在 push 涉根層路徑時跑 root-infra leg——**「只改子專案 .py」的 push 本地不執行這些跨樹判準** | CI 側 `root-infra-ci.yml` 全變更觸發可補抓；但 CI 停擺（DEF-101-081）期間本地即唯一防線，該情境下違規會晚至下次涉根層 push 才被抓 | 已知縫如實揭露；擴 dispatcher 子專案 leg 附帶跑跨樹掃描的成本效益待下輪評估（R13 一審 Architect 核可以本列 known-gap 承認為收斂） |
| **凍結版 v0.01~v0.29 `install_post_commit.ps1` 用 `-Encoding ascii` 寫 hook，非 ASCII 路徑會被靜默替換為 `?`**（v0.30 已修：改 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)`） | 手動 cd 進舊版目錄執行 hook 安裝（非官方流程）時，含中文字元的使用者路徑會讓 drift/closure advisory hook 內嵌路徑損毀、靜默失效；`v0.12~v0.29`（18 支）另因缺 BOM 會先 parser 斷裂根本跑不到此行 | hook 安裝流程動態解析 LATEST 版（現為 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.ps1`；R9 訂正：本欄舊文誤植為 `AutoClaude/tools/install_hooks/...`，該路徑全 repo 歷史從未存在），正常安裝流程不會觸及舊版；凍結版依紀律不回改 |
| **`AutoClaude/pyproject.toml` 的 `hypothesis` 已於 R3 精確鎖版**（`hypothesis==6.156.6`；此前 `>=6.0` 未鎖上限曾於 Wave 1 全新環境 `pip install` 下被懷疑導致約 19 個測試連鎖失敗，後經 SA/SD 兩方獨立以全新 venv 重驗**無法重現**，原始診斷已訂正為未經證實的記事，見 DEF-101-058） | 全新環境 `pip install -e ".[dev]"` 解析依賴版本的跨平台漂移風險，不因鎖版而完全消除——`pyproject.toml` 另有 ~18 條相依（`pydantic`／`sqlalchemy`／`httpx` 等）仍未鎖版本上限，屬同類風險（見 DEF-101-060，尚未處理） | 已修：`pyproject.toml` 鎖定為經本機全新 venv 驗證綠燈的 `hypothesis==6.156.6`（DEF-101-058，fixed@Mac/Windows 四方複審 2026-07-14）。其餘 ~18 條未鎖依賴為 DEF-101-060，記事存證待後續輪逐一評估鎖版 |
| **凍結版 v0.01~v0.29 `tools/arch_fitness/run_self_evolution.sh`／`.ps1` 對 python 呼叫零可用性判斷**（WindowsApps guard 缺口） | 全新未裝真 Python 的 Windows 11 機器上手動 cd 進舊版目錄執行會掛在「請安裝 Python」商店提示；v0.30（LATEST）對應版本本輪已修復 | 正常安裝／開發流程只會執行 LATEST 版；凍結版依紀律不回改（DEF-101-359） |

> 對應缺陷帳本：前兩條＝[AutoSDD_Defect_Log.md](docs/06_quality/AutoSDD_Defect_Log.md) DEF-101-003／DEF-101-004（wontfix＋凍結版紀律）；第 4~8 條＝DEF-101-019／DEF-101-020（wontfix＋凍結版紀律）與 DEF-101-021／DEF-101-022／DEF-101-025（open）；倒數第五條（凍結版 settings 兩面向）＝DEF-101-040（wontfix＋凍結版紀律）；倒數第三條（`install_post_commit.ps1` ASCII 編碼）＝DEF-101-056（wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正）；倒數第二條（`hypothesis` 版本鎖定）＝DEF-101-058（**fixed@Mac/Windows 四方複審 2026-07-14**；R3 複審發現本文件先前敘述與此已修復實況不同步，已訂正）。**R44 跨平台輪新增末條**：末條（v0.01～v0.29 凍結版 `run_self_evolution.{sh,ps1}` 對 python 呼叫零可用性判斷）＝DEF-101-359（wontfix＋凍結版紀律；LATEST v0.30 對應版本已 fixed@R44，見 DEF-101-361）。另有 **DEF-101-005**（`verify_traceability.sh` 的 `set -e`＋grep 零命中提前靜默退出，所有 bash 版本皆然；**fixed@R16**：同根因併入 DEF-101-218 一併修復，9 處賦值敘述式補 `|| true`；本文件先前敘述與此已修復實況不同步，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正）、**DEF-101-018**（ruff 存量 baseline 待分批清理，open；其「未鎖版跨機器漂移」根因 DEF-101-006 已 fixed@四方複審第三輪；**R23 複審重新實測 baseline 為 1,147 筆**〔`.venv` ruff 0.15.21，原「1,339 筆」為舊測值，見 DEF-101-262〕）、**DEF-101-057**（`install_post_commit.{sh,ps1}` worktree 路徑解析 bug 在 v0.01~v0.29 之殘留，wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正；不佔本表列，因與上方 DEF-101-056 同源議題已合併敘述於缺陷帳本本身）、**DEF-101-358**（v0.01～v0.29 凍結版 `_sanitize_component()` 僅剝除 `/`／`\` 的較弱版本殘留；**fixed@R45**：30 個版本〔v0.01～v0.29 凍結基線＋LATEST v0.30〕已全數改為委派共用模組 `AISDLC_SDD/scripts/component_sanitizer.py`，含 Windows 保留裝置名／禁用字元／長度上限完整強化，不再有較弱版本殘留；本文件先前敘述與此已修復實況不同步，本輪複審已訂正、移除上表對應列）與 **DEF-101-060**（`pyproject.toml` 另有 ~18 條相依未鎖版本上限，open，記事存證，見上表 hypothesis 列）非平台缺口、不列本表。

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
