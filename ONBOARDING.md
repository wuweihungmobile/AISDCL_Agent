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
| Docker（選用） | 只有要跑 `run_act` / PG 契約測 / nightly mutation 時才需要。**Windows 須確認 Docker Desktop 啟用 WSL2 backend**（預設值；仍在用 Hyper-V backend 的舊機器/公司鎖定環境請切換，否則 `run_act` 等容器操作可能無法正常啟動）。macOS（Apple Silicon）執行 `run_act` 時，`.actrc` 的 `--container-architecture linux/amd64` 會強制走 QEMU 模擬（刻意設計，貼近雲端 amd64 runner），預期較慢屬正常代價。🔴 **act 前置（mac 專屬，DEF-200-010）**：第一次建 runner 映像時**先把基底拉下來、再 build**（`docker pull <基底映像>` 之後才 `docker build`）——buildkit 的 deadline 涵蓋「拉基底 ＋ 跑 RUN 層」整段，而 QEMU 下光拉 2GB 級基底就可能吃掉整個額度，失敗字面是 `DeadlineExceeded`，讀起來像 build 本身壞掉（實測 RUN 層本身只要數秒）。 |
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

### 🔴 第 0 步（Windows 必讀）：`git clone` 當下就要帶 `core.longpaths`

本節此前直接從 `bootstrap.ps1` 開始，**完全沒有 clone 這一步**——而 Windows 上「怎麼 clone」本身就是一個會讓開箱失敗的決定。R76-01 單變因實測（目標目錄長度 168）：

| clone 指令 | rc | 落地檔數 | `tools\bootstrap.ps1` 在磁碟上？ |
|---|---|---|---|
| `git clone <url>`（未帶旗標） | **128** | **301** | **否** |
| `git clone -c core.longpaths=true <url>` | 0 | 27,523 | 是 |

失敗形態是**無聲的半套 checkout**：git 印幾行 `Filename too long` 就結束，目錄看起來有東西、`git status` 也不會告訴你少了兩萬多支檔案，而本節教的第一個指令（`bootstrap.ps1`）根本不在磁碟上。

```powershell
# Windows：clone 當下就帶旗標（這一條是開箱的第 0 步，不可省略）
git clone -c core.longpaths=true <repo-url>

# 建議同時做一次機器級設定，讓「忘記帶旗標」不再是單點故障（一次性、對之後所有 clone 生效）
git config --global core.longpaths true
```

> 🔴 **為什麼不能只靠 `dev_start` 的 [6/7] 平台健檢**：那一步設的是 `--local`，也就是**這個 repo 已經 clone 成功之後**才寫得進去的設定。clone 失敗的那個當下它還不存在。實查三層 config：`--system` rc=1、`--global` rc=1、主 checkout `--local` → `true` ⇒ **保護只存在於已經 clone 好的 repo 裡，fresh clone 零保護**。上面那條 `--global` 就是把這個單點故障補起來。
>
> 幾何上界（現況一律現查 `python tools/check_ntfs_paths.py`，它每次執行都會印出算式與代入值，本節刻意不寫死當下的數字）：checkout 根前綴（含結尾分隔符）受兩個面同時約束——檔案面 `259 − 最長 tracked 相對路徑`、目錄面 `247 − 最深 tracked 相對目錄`。🔴 **這個上界是會隨 repo 長大而縮水的量，不是常數**：每多一層深目錄或一個長檔名，所有人的可用根前綴就同步變少，而超過上界時沒有任何警告、只有半套 checkout。實測的失敗點是 168 字元的根目錄——巢狀 workspace／帶組織名的同步資料夾／`worktree` 子目錄疊起來很容易到那個量級（**未逐一量測各種常見安裝位置，此句是機制說明不是量測宣稱**）。
>
> macOS/Linux 不需要這一步（PATH_MAX 1024/4096，結構上沒有這個形態）——**這正是「只在 mac 開發的人永遠不會發現它」的原因**。

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

驗證 hooks 正常（未報 `python not found`）：重開一個 session，SessionStart 若印出 `[SDD-ROUTER] SDD 治理 hooks 休眠中…` 即為正常（純 AutoClaude 工作時 hooks 本應休眠）。要對 SDD 框架做 dogfooding 時才設 `SDD_ACTIVE_VERSION`（🔴 R83 補齊平台：本句原本只給 bash/zsh 形態，Windows 讀者無路可走）——macOS / Linux 的 bash・zsh 寫 `export SDD_ACTIVE_VERSION=<版本號>`，Windows PowerShell 寫 `$env:SDD_ACTIVE_VERSION = '<版本號>'`（值＝當前最新版號，一律以 [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md) 為唯一真相源；本文撰寫時為 `0.30`）。

---

## 5. 常見雷區對照（Windows 開發者初到 macOS，或反向）

| 現象 | 原因 | 解法 |
|------|------|------|
| 每個工具呼叫都報 `python: command not found` | macOS 無 `python`，只有 `python3` | 啟用 `.venv`（§3）；勿改 hooks 的裸 `python` |
| `pip install` 失敗、要求 ≥3.11 | 系統 Python 太舊 | 裝 Python 3.11（§1），重跑 bootstrap |
| `.sh` 腳本報 `$'\r': command not found` | Windows 曾把 `.sh` 存成 CRLF | [.gitattributes](.gitattributes) 已強制 `.sh=LF`；重新 checkout 或 `git add --renormalize <file>` |
| `tools\xxx.ps1` 在 macOS 跑不了 | PowerShell 腳本是 Windows 專屬 | 用對應的 `.sh`（見 §6 對照表） |
| 工作樹的 `.ps1` 變成 LF，而 `git status` 一片乾淨 | `.gitattributes` 對 `*.ps1` 是 `text eol=crlf`：index 側恆為 LF，`git status` 兩側套同一份正規化規則 ⇒ **工作樹行尾漂移結構上不可見**（`git add` 之後連唯一那個 `M` 而 `git diff` 全空的幽靈列都會消失）。R79 已把寫入者溯源到 Claude Code 的 `Write` 工具 | 寫入當下由 PostToolUse 的 `AutoClaude/tools/hooks/check_ps1_encoding.py` 自動補 BOM ＋收成 CRLF（LF→CRLF 對 `*.ps1` 是 blob-neutral，改不到入庫內容）；事後兜底＝`tools/tests/test_platform_neutral_paths.py::TestWorktreeEolMatchesPolicy`（讀 `git ls-files --eol` 的 `w/` 欄）。手動修：`git add --renormalize <file>` 或重新 checkout |
| Windows `git pull` 後 `AISDLC_SDD/.claude/settings.local.json` 從工作樹消失 | 該檔已出庫（gitignore），倉內僅留 example | 複製同目錄 `settings.local.json.example` 為 `settings.local.json`（本機個人設定，之後不會再被 git 動到） |
| cd 進 repo 後 pyenv shim 報 `version 3.11 is not installed` | [.python-version](.python-version) 只寫兩位版號 `3.11`：uv 與 Windows `py` launcher 原生支援，但 **pyenv 需 ≥ 2.4** 才支援前綴解析（pyenv-win 視版本而定） | 升級 pyenv ≥ 2.4；或先 `pyenv install 3.11.x` 並確保該版可被解析；或改用 uv |
| 全新 Windows 11 跑 `.venv\Scripts\Activate.ps1` 報「因為這個系統上已停用指令碼執行」 | Windows 預設 `ExecutionPolicy=Restricted` 擋所有 `.ps1`（bootstrap／dev_start 以 `-ExecutionPolicy Bypass -File` 呼叫可跑，但**日常啟用 venv 與 `. tools\dev_start.ps1` dot-source 都會被擋**，見 §2.1 前置） | 一次性放行：`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| 文件裡的路徑是 `d:\CursorProject\...` | 文件在 Windows 上撰寫 | 純說明性路徑，忽略即可；實際指令請用相對路徑 |
| GUI 發起的 git commit（如 VSCode Source Control 按鈕）被 hooks 擋下：`python: command not found`（mac）或缺 ruff 的系統 Python（Windows） | GUI App 不繼承終端機 venv PATH，hooks fail-loud 擋下 | 從已啟用 venv 的終端機啟動編輯器（如 `code .`），或改用終端機 commit |
| Windows 上首次 `pip install`／`pytest` 異常緩慢 | Windows Defender 即時掃描大量小型 Python 檔案（`.venv`、`__pycache__`） | 非必要但建議：把 `.venv` 與本 repo 目錄加入 Defender 排除清單，可顯著加速 |
| 手動補裝套件時 `python -m pip ...` 報 `No module named pip` | `.venv` 是 bootstrap 偵測到 `uv` 時走 `uv venv` + `uv pip install` 建的，這種 venv **內部本來就沒有 `pip` 模組**（Mac/Windows 四方複審實機驗證重現） | 改用 `uv pip install -e '.[...]'`（uv 已安裝時對任何已啟用的 venv 皆可用；**extras 的引號不可省，理由見下一列**）；完整警語見 [CLAUDE.md](CLAUDE.md)「AutoClaude — 常用指令與架構」§安裝/執行 與 [docs/AISDLC_Agent_UserGuide.md](docs/AISDLC_Agent_UserGuide.md) §1.2 |
| macOS 上跑 `uv pip install -e .[dev,notifications]` 報 `zsh: no matches found: .[dev,notifications]`（R57 新增） | macOS 自 Catalina 起預設 shell 是 **zsh**，`.[...]` 未加引號會被當成 glob 做 filename generation；repo 內無匹配檔名時 zsh **在執行前就中止整條指令**（uv／pip 根本沒被叫到，所以錯誤訊息看起來與套件無關）。同一行在 bash 與 PowerShell 下正常，故 Windows 開發者不會遇到 | extras 一律加單引號：`uv pip install -e '.[dev,notifications]'`（三種 shell 皆正確）。權威指令站點見 [CLAUDE.md](CLAUDE.md)「AutoClaude — 常用指令與架構」§安裝/執行；本列因必須引述壞形態才說得清症狀，於 `tools/tests/test_extras_quoting_zsh_safety.py` 取得行內豁免 |<!-- zsh-glob-ok: 雷區對照表必須原樣引述未加引號的壞形態才能說明症狀，此處非教學指令 -->
| 以 Git Bash 呼叫 `powershell -File …`，或經 pyenv-win `.bat` shim 跑 python，**看不到 stdout／中文路徑變亂碼**（R59 新增） | 兩種形態皆實測：① 經 Git Bash 呼叫 `tools/windows_smoke_local.ps1`，非 ASCII 路徑步驟產生**假紅**（少一項通過、兩項失敗；同一支腳本改用原生 PowerShell 則全數通過。本列刻意不寫 `PASS=N` 字面——`tools/tests/test_smoke_ci_sync.py` 有一道「ONBOARDING 的 `PASS=N` 宣稱集合必須恰等於兩腳本釘選值」的跨檔鎖，本列談的是假紅觀測、不是釘選宣稱，寫成該字面會被它正確攔下〔R59 落地本列時當場被攔〕)；② 經 Git Bash → pyenv `python.bat` shim 跑 `python -c` 印字串**完全沒有輸出**（只有 stderr 透得出來），曾害主控把「修好後零輸出」誤判成比原 bug 更糟 | **驗證任何與 `.bat` shim 或非 ASCII 路徑有關的行為，一律用 PowerShell 載具、不要走 Git Bash**（PowerShell 視窗／Windows Terminal／schtasks／Claude Code 的 PowerShell 工具）。`windows_smoke_local.ps1` 自 R59 起偵測 `MSYSTEM` 即 fail-fast 拒跑（DEF-101-511／520②）。🔴 **本輪訂正（F-07）：這四個載具不是同一個引擎，先前把它們一律稱為「原生 PowerShell」是假的**——Claude Code 的 PowerShell 工具當回合實測 `$PSVersionTable.PSVersion` ＝ **7.6.4（Core）**，而 schtasks Action 與 `powershell.exe` 是 **5.1.26100.8875（Desktop）**；兩者的預設檔案編碼分別是 utf-8 與 big5，全庫 `.ps1` 以 `[Parser]::ParseFile` 對跑實測 7.6.4 零錯、5.1 有 29 支錯。⇒ **凡標的是 PS 5.1 語意的腳本**（`windows_smoke_local.ps1`、`install_windows_nightly.ps1`、任何 schtasks Action）**必須顯式外呼** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File …`；直接用 PowerShell 工具跑 smoke 會被它自己的 ENGINE-MISMATCH 守衛擋下（實測 rc=1） |
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
- **執行權限政策**：「755 入庫」範圍＝**hook 檔（`tools/git-hooks/` 由 git 直接執行；`AISDLC_SDD/.githooks/` 與 `AutoClaude/tools/git-hooks/` 為 dispatcher 分流目標——以 `bash` 呼叫、exec bit 非必要，維持 hook 家族一致即可；`.claude/hooks/` 為 hook 家族的第四個住所——根層 settings.json 以裸 command 形態直接執行該目錄下的載體檔（不走 python 前綴），故 exec bit 在 mac/Linux 上是執行必要，R80 補列）＋ SDD 專案初始化器 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh`（R80 DEF-101-935 補列：該檔自己的 -h 逐字教人裸跑它本身，mac/Linux 一 clone 照做即 rc=126 Permission denied，故 exec bit 在該平台是執行必要——這與上方判準①「治理文件教裸跑就必須 100755」是同一條規則的兩面；凍結版 v0.01~v0.29 的同型存量依 Copy-on-Evolve 不改，見 DEF-101-936）＋ launchd 載體 `AutoClaude/tools/run_local_nightly.sh`**（R11 D6 決策保留 755；R14 SCAN-CI-7 訂正 rationale：§8 範本與 `install_mac_nightly.sh` 產出的 plist 皆以 `/bin/bash` 為執行檔、腳本僅為引數，exec bit 已非執行必要，保留 755 作為容忍手動直呼的防禦與 D6 決策延續）；其他 `.sh` 工具一律以 `bash xxx.sh` 呼叫、索引 644，不依賴 executable bit（R12 已將 bootstrap／integration_gate／install_git_hooks／local_ci_gate／run_act 五支歷史 755 正規化為 644，使本政策句與索引實況一致）。
  - 🔴 **R79：這條政策此前只是散文，現在有機械物**＝`tools/tests/test_platform_neutral_paths.py::TestExecBitIsGovernedViaTheGitIndex`。它只讀 **git 索引模式**（`git ls-files -s`），因為那是 Windows 上唯一還看得見這一維的管道——本機 `core.filemode=false`（實測），檔案模式從不出現在 `git status`／`git diff`／任何 pre-commit 掃描裡。三道判準：①治理文件裡凡教人**裸跑** `./x.sh` 而標的索引模式不是 100755 者判紅（mac/Linux 一 clone 就 `Permission denied`／rc=126，而 Windows 上永遠讀起來是對的）；②索引 100755 的檔檔首必須是 `#!` 且不得帶 BOM；③凍結版 SDD 樹的同型存量以精確計數登記為可見欠債（Copy-on-Evolve 禁改，本輪只修 LATEST 那一支 `tools/README.md`）。
  - ⚠️ **在 Windows 上「加執行權限」是做不到的動作**（R79 於 Git Bash／MINGW64 實測）：`[ -x file ]` 判的是**檔首是不是 `#!`**，不是權限位元——同一支腳本加了 UTF-8 BOM 就由 `EXECUTABLE` 翻成 `NOT-EXEC`，而 `chmod +x` 之後仍然是 `NOT-EXEC`。所以 `tools/git-hooks/post-commit` 那道 `if [ -x "$target" ]` 在 Windows 側是內容猜測：dispatcher 檔首多任何位元組就會靜默 exit 0。要真的改索引模式請用 `git update-index --chmod=+x <file>`。
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
| `root-infra-ci.yml` | 🔴 **R68 訂正①（雲端 CI 可用性是輪次屬性，不是本文件的常數）**：本列 R60~R67 版把當時雲端 CI 的不可用狀態寫成現況，還附了一條涵蓋**全文件**的解讀指令（「他處凡寫『接 root-infra-ci 第 N 道』者一律以該句為準」）；該前提已於 **2026-08-01 12:31Z 起翻轉**——同日 14:03:42Z 那批 push 的四支 workflow 全數 `success`（root-infra-ci 實跑 2m41s），原補注來源 `QA-R60R3-04`／`DEF-101-597` 所述狀態屬該日之前，原句逐字保全於 `ADR-XPLAT-002` §6 邊界 1 的逐輪覆蓋表。**改法**：本列與本文件他處一律**不再代言雲端狀態**，「接 root-infra-ci 第 N 道」讀作**接線完整性**宣稱；要主張「已在雲端跑過」請自己跑現查指令 `gh run list --workflow=root-infra-ci.yml --limit 5 --json conclusion,createdAt,event`。逐輪覆蓋沿革見 `ADR-XPLAT-002` **§6 邊界 1 的逐輪覆蓋表**（🔴 R69 訂正：本句原寫「見 **§9.1 逐輪平台覆蓋表**」，而本文件**從來沒有 §9.1**——那是一條寫下當時就解析不到的死指標，指路句自己指向不存在的地方，比不指路更糟。逐輪覆蓋沿革的活來源是上述 ADR 節次與 §7 表② 兩條 `snapshot-fingerprints-<平台>` 錨的 provenance）。（四方複審第三輪新增，非遷移）根層基建守門：**全變更觸發**（NTFS 檔名閘須守任意路徑，paths 白名單必留盲區），**道數與逐道內容一律以 `.github/workflows/root-infra-ci.yml` 檔頭註解為準，本列刻意不再就地列舉**——🔴 **R68 訂正②**：本列原寫「現行 N 道」並內嵌 1~N 列舉，而它自己指定的權威來源（workflow 檔頭）當時已寫另一個數字；R68 實測 `grep -c '^      - name:' .github/workflows/root-infra-ci.yml` → 16，扣掉 `Set up Python 3.11` 與 `tools/tests 第三方相依` 兩個環境步即為實際守門道數，本列漏列的兩道是「缺陷帳本保全稽核」與「§7 表② presumed-stale 觸發器」。同一個計數住兩個家＝保證會漂移的第二站點（同 §7 pytest 基線「唯一站點」政策），故物理消滅本列這一份。現查：`grep -n '道' .github/workflows/root-infra-ci.yml | head -3`（道數）、`grep -n '^      - name:' .github/workflows/root-infra-ci.yml`（逐道清單）。（DEF-101-012、四方複審第四／五輪＋R8／R13 擴充＋R55 擴充） |
| `windows-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）Windows 側執行級驗證：windows-smoke（bootstrap/dev_start/install 腳本/dispatcher 真實 commit 觸發；step 以 pwsh 為主，僅 dispatcher 觸發 step 刻意用 Git Bash 載具）＋ windows-nightly-full（深度回歸，**含 PS 5.1 引擎專測**——R5/S8 拍板置於 nightly 非 PR 閘門，R12 訂正本列歸屬誤植）；**本地補償（非全等）**＝`tools/windows_smoke_local.ps1`（R10）＋ nightly stage ＋ pre-push leg，逐 step 的承載歸屬與**零本地承載差集**見 `tools/tests/test_smoke_ci_sync.py::_CI_STEP_LOCAL_CARRIER`（機械鎖：CI 新增 step 未登記即紅） |
| `macos-compat-ci.yml` | （Mac/Windows 相容性輪新增，非遷移）macOS 側執行級驗證：macos-smoke（bash 3.2 直呼/安裝腳本/worktree/ci-gate 雙軌）＋ macos-nightly-full；**本地補償（非全等）**＝`tools/macos_smoke_local.sh`（R9）＋ nightly stage ＋ pre-push leg，逐 step 的承載歸屬與**零本地承載差集**見 `tools/tests/test_smoke_ci_sync.py::_CI_STEP_LOCAL_CARRIER`（機械鎖：CI 新增 step 未登記即紅）。🔴 **R67-C19 訂正**：本列與上列原寫「本地補償**對等**」，而實測有數個 compat-CI step 在本地零承載（bootstrap／dev_start 實跑、`integration_gate` 實跑、真實 git commit 觸發 dispatcher 等），且該覆蓋差集**當時無任何機械鎖**（注入一個全新 CI step 後根層 1139 支測試全綠）；「對等」二字會讓讀者以為本地綠燈 ≈ CI 綠燈而停止追問（🔴 **R68 訂正**：原句另以 compat-CI 當時的雲端不可用作為加強理由，該狀態已於 2026-08-01 翻轉——macos-compat-ci 當日三批 push 皆 `success`；但**覆蓋差集是否存在與雲端是否活著無關**，故理由收斂為「本地綠燈本來就不等於 CI 綠燈」。雲端現況一律現查 `gh run list --workflow=macos-compat-ci.yml --limit 5`）。差集清單刻意**不在此重抄一份**（那是保證會 stale 的第二站點），一律指向上述登記表。詳見 §8/§10 |

`.actrc` 亦已上移根層；`run_act`（AutoClaude 側）與 `act-ci.sh`（AISDLC_SDD 側）現於 **monorepo 根**執行、讀根層 `.actrc`。（Dependabot 已於 2026-07-12 完全停用並移除根層 `dependabot.yml`——單人 main-only 工作流不採自動相依 PR；GitHub 端 security updates／vulnerability alerts 亦為停用。相依更新改為日後手動盯版或重新啟用。）

---

## 7. 常用驗證指令

**macOS / Linux（bash・zsh）**

```bash
# AutoClaude（在 AutoClaude/ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試
PYTHONUTF8=1 lint-imports             # 架構約束（契約條數 SSOT＝AutoClaude/.importlinter；rc=0 即全 kept）

# AISDLC_SDD（在 AISDLC_SDD/ 下）
bash scripts/ci-gate.sh               # 本機 CI 閘門（pytest + arch_fitness）
```

**Windows（PowerShell）** — R57 補齊：本節原先是全份雙平台文件中唯一只給 bash 形態的指令區，其中 `PYTHONUTF8=1 lint-imports` 的 `VAR=value cmd` 前綴語法**在 PowerShell 不存在**，會報 `The term 'PYTHONUTF8=1' is not recognized`（實測 pwsh 7）；設環境變數須改用 `$env:VAR=值; <指令>`。

```powershell
# AutoClaude（在 AutoClaude\ 下，需已啟用 venv）
python -m pytest tests/ -q            # 全套測試（與 bash 形態同）
$env:PYTHONUTF8=1; lint-imports       # 架構約束（契約條數 SSOT＝AutoClaude\.importlinter；rc=0 即全 kept）

# AISDLC_SDD（在 AISDLC_SDD\ 下）
powershell -ExecutionPolicy Bypass -File scripts\ci-gate.ps1   # 偵測到 Git Bash 即薄委派 ci-gate.sh＝完整對等，見 §6
```

> 🔴 **看到 `N skipped` 先讀 §7.1（本節末）**：那個數字裡有**一整類**（PG 相依）既不是缺件、也不是平台差或退化，解法是**拉起 docker 容器＋跑一次 `alembic upgrade head`（容器是 tmpfs、每次重建都要重 migrate）、零程式改動、零常駐環境變數**。它佔多少支是**量測值**，§7.1 附現查指令，本行刻意不寫死。

> 🔴 **本節為全 repo pytest 基線數字唯一站點**（R13 ARCH-R13-1 收斂：其他活文件〔根/AutoClaude CLAUDE.md、AutoClaude/README、useMacWin〕一律指向本節不重複數字，由 `tools/check_pytest_baseline_sites.py` 機械守門；歷史紀錄檔〔缺陷帳本、sprint_history、improving 系列等時代快照〕不在納管範圍）。
>
> 🔴 **Windows 11 側基線（R59 新增，2026-07-28 實機量測）— 本節此前只有 macOS 數字**
>
> 本節自 R13 收斂為「唯一站點」以來，歷輪校正註記的量測平台**全部是 macOS**（R37 起才開始
> 要求標註平台）。但這是一份雙平台 onboarding 文件，而兩平台的數字在結構上**永遠不可能相同**
> ——結果是 Windows 開發者照本節驗證時，四組數字有四組對不上，而文件沒有任何一句話能讓他
> 分辨「平台差異」與「退化」。R59 於 Windows 11 Pro（26200）實機補齊（DEF-101-515）：
>
> **表① — live 格（有機械鎖：根層 unittest 閘門每次執行都當場重算，stale 即紅並印出應填值）**
>
> 量測時點＝**R60 收尾工作樹**。這兩格不靠人記得回填：取值來源是機器，一鍵回填指令為
> `python tools/sync_onboarding_baselines.py --write`（`--check` 為稽核模式，即測試消費的那一條路；
> 產生器 ＋ `--check` 的形狀對齊 repo 既有慣例＝`AutoClaude/CLAUDE.md` 的 `[Architecture Snapshot]`
> ↔ `AutoClaude/tools/snapshot_sync.py`）。
>
> 🔴 **R67 訂正（R67-D20）**：`tools/sync_onboarding_baselines.py` 的 `--check` 在 R67 之前
> **並不是實存旗標**——該工具以 `"--flag" in argv` 手搓解析、未知旗標一律靜默掉進 default 分支並
> rc=0，所以 `--check` 只是「恰好看起來對」；同一個洞也讓 `--check-snapshot` 少打一個字母時，在
> 表② 確實過期的工作樹上回 rc=0 假綠（正確拼法同時 rc=1）。現已改 argparse：`--check` 成為實存
> 旗標、**未知旗標／打錯字／前綴縮寫一律 rc=2 fail-loud**、`--help` 印完整用法（另有 `--json`、
> `--platform`、`--allow-pg-extras`）。**凡在提及 `sync_onboarding_baselines` 的行上以反引號寫出的
> 旗標**，都由 `tools/tests/test_doc_loc_baseline_freshness_r60.py` 對該工具的 argparse parser 反查
> 機械釘住——文件不得引用不存在的旗標。
>
> | 量測項 | macOS | **Windows 11 欄**（🔴 R67 round 2 訂正：欄頭不再代言量測時點與平台——本欄的「受鎖 token」是**平台中立值**、取值來源逐格標示於歸因欄；只有 `skipped=N`／LOC 三數字這類「非受鎖」附註才是 Windows 實機量測。原欄頭寫「Windows 11（R60 收尾實測）」，而該格裝的其實是 R67 在 Darwin 真機上量得的 `MIN_TESTS`——SA-R67-07） | 差異歸因（實測，非推算）＋ 鎖與取值來源 |
> |---|---|---|---|
> | 根層 `tools/run_root_unittests.py` | 收集總數與 Windows 欄同一個數（兩平台收集總數相同，見本列歸因欄）⇒ **本欄不另寫一份數字**，一律看 Windows 欄那個受鎖 token。⚠️ 該 token 是 `MIN_TESTS` **下限釘選**、不是當下實收數（實收會高於它直到下次重釘）。macOS 側與 Windows 的差異只在 skip：R67 於 Darwin-25.5.0-arm64 實測 `skipped=15`。🔴 **本欄是 dated snapshot、不受 live 鎖管轄**——`rootunit-baseline-live` 鎖只抽右欄那個 `N tests OK` token（R67-F28：原本此處寫死 `616（skipped=4；R57 量測）`，落後實況約九輪而任何機械物都抓不到，因為它根本不在鎖的取值範圍內；故改寫成**指向 live 來源**而非再寫死一個會過期的數字） | **3735 tests OK**（量測時點 2026-08-19）｜`skipped=43` 的量測時點仍是 2026-08-08、**本輪沒有重量**（🔴 R96 二審訂正：原文把兩個各自變動的東西塞進同一個括號，於是新 token 被貼上一個舊的量測時點——正是 R75 判過的形態。該值刻意不在鎖內〔見本欄下方「鎖的邊界」〕⇒ 機械物不會為它說話；而同一輪 `tools/tests@win32` 的 skip 天花板才剛由 38 上修為 42，這個 43 幾乎確定已落後。現查＝跑一次根層閘門、讀 `report_all_skips` 印出的那一段，本欄不再代填一個沒有現場取值來源的數字） | 收集總數沿革 R57=616 → R59=661 → **R60 見本格 live 值**（每輪新增回歸鎖，含四方複審條件補的鎖），兩平台收集總數相同、差異只在 skip。🔴 **`skipped=N` 的逐項清單刻意不再手寫在本表（R75 訂正）**：原文把該數字逐項展開成三類 POSIX-only／macOS-only 語意的組成，而那份清單自寫下之後從未被任何機械物核對過——本格的受鎖 token 被 `sync_onboarding_baselines.py` 每輪更新，`skipped=N` 與其後的清單卻不在鎖內（見本欄下方「鎖的邊界」），於是本輪淨增約 33 筆 skip 時**數字與清單雙雙落後、零機械記帳**。現行做法：逐項清單的唯一權威來源＝每次執行根層閘門時 `report_all_skips` 印出的那一段（門面在 `tools/lib/windows_skip_tags.py` 再匯出，實作住 `tools/lib/skip_runtime_report.py`），它把當次每一支 skip 的 id ＋ 理由 ＋ 標籤**逐支**列出（DEF-101-510 已明訂「全列不得只印計數」）；本格數字由 Windows 11 Pro（26200）原生 PowerShell 跑一次該閘門取得。🔴 **本格刻意不再記「已標籤／未標籤各幾支」的分佈**——那是同一個病的縮小版（標籤體系一改組成就變，而沒有任何東西會核對這個附註）；要看當次分佈就讀那段輸出。未標籤的**靜態站點**數另由 `_POSIX_TAG_RATCHET` 逐棵測試樹釘死（該常數住 `tools/lib/skip_tag_policy.py`，`tools/lib/windows_skip_tags.py` 再匯出）（🔴 站點 ≠ 測試支數：一個 class 級 decorator 可覆蓋多支測試，且「工具沒裝」那類 skip 不屬平台述詞、不進該棘輪——本輪實測 tools/tests 有 11 個「Windows 上會 skip」的靜態站點，對應到 32 支已標籤 skip，故靜態站點數不可當作 `skipped=N` 的替代量）。**R59 動工時的 11 支**屬 R59 世代史料，非現況 🔴 **本格測試數自 R60 起有機械鎖**：取值來源＝`tools/run_root_unittests.py` 的 `MIN_TESTS`（該值本身即「收輪時填實測值、不做加減推算」的釘選，見該檔第 38 行）。**同一份 repo 對同一個數字只准有一種說法**——R60 SA-R60-01／ARCH-R60-03 抓到的正是「本格寫 661 而 `MIN_TESTS` 已重釘 756」。維護契約：**重釘 `MIN_TESTS` 時必須同步本格**（`python tools/sync_onboarding_baselines.py --write` 一鍵回填），否則根層 unittest 閘門紅——它不是假警報。**`skipped=N` 刻意不在鎖內**（無現場取值來源，屬 dated snapshot 語意）。🔴 **鎖的邊界（R60 round 2 四方全數命中，ARCH-R60R2-03／SA-R60R2-02／SD-R60-R2-03／QA2-R60-02）**：本行**只有 `N tests OK` 這個 token 受鎖**，其餘數字都是散文。round 1 落地產生器後，同一行的鎖住值已回填為當輪實測，而散文仍留著一個較舊的當輪值宣稱——**產生器 ＋ `--check` 只保證「被抽取的那個 token」新鮮，完全不保證同一行的散文新鮮**，這是本 repo 對「機械鎖已落地」的認定門檻必須修正的地方（DEF-101-562）。根治＝`_SPECS` 的 `prose_claims` 判準：受鎖行上任何 `R<輪號>=<數字>` 形態的同量宣稱，只要值 ≠ live 值就必須登記進產生器的 `historical` 白名單（附 WHY），否則紅。故當輪值**一律不寫進散文**、只寫「見本格 live 值」。<!-- rootunit-baseline-live: R60 錨點，勿刪；刪除本標記會讓該測試 fail-loud --> |
> | `check_loc_budget` / `lint-imports` | 同值（純靜態分析，無平台差異；數值見右欄，來源標示同右欄） | total=17096 cap=20438 violations=0 ／ lint-imports rc=0（契約條數見 SSOT，本格不寫死） | 純靜態分析，無平台差異。🔴 **來源標示（R60 SA-R60-07③）**：本列三數字為 **Windows 11 實機量測**；因 LOC 只數行、不執行程式，兩平台必然同值，故 macOS 欄標「同值」而非另填一份——**不要誤讀為 macOS 實測**。🔴 **本格 LOC 三數字自 R60 起有機械鎖**：`tools/tests/test_doc_loc_baseline_freshness_r60.py` 每次跑根層 unittest 閘門時，經 `tools/sync_onboarding_baselines.py` 當場實跑 `AutoClaude/tools/check_loc_budget.py --json`，與本格字面值逐項比對，不符即紅並印出應填的值。**填值時點比照 `MIN_TESTS` 重釘紀律**——「所有並行 agent 停工後，填最終工作樹實測值、不做任何加減推算」：`autoclaude/` 是多包並行修復的共同標的，本格在收輪前必然數次變動（R60 實測：主控動工量 20359，同輪另一包改 `utils/logger.py` 後即變動為**左欄值**——當輪值刻意不在此重複一次，見下方「受管值不得在受鎖行出現第二次」判準），故只在收輪最終工作樹上填一次。**維護契約（R60 SD-R60-09）**：判準是**精確相等**（非 `MIN_TESTS` 的下限語意），即此後任何動到 `autoclaude/` 行數的變更都必須同步本格——這是刻意承受的維護負擔，成本已由產生器攤平：`python tools/sync_onboarding_baselines.py --write` 一鍵回填。lint-imports 的結果**不在鎖內**（需另跑 import-linter，屬另一筆缺口，如實揭露）。🔴 **R82 訂正：本格與 §7 兩個指令區原本各寫死一份「8 kept / 0 broken」，而 R82 落地 `no-harness-import` 後實測為 9**（當回合 `lint-imports` rc=0、逐字 `Contracts: 9 kept, 0 broken.`）——一個沒有機械物在守的數字住了三個家、三個都過期。訂正方式**不是**把 8 改成 9（那只是把 stale 往後推一輪），而是三處一律改為指向 SSOT `AutoClaude/.importlinter`（現查＝數該檔的 `name =` 行）；本格保留「不在鎖內」這句誠實劃界不變。<!-- loc-baseline-live: R60 錨點，勿刪；刪除本標記會讓該測試 fail-loud --> |
>
> **表② — dated snapshot（機器無法在根層閘門現場算出 ⇒ 無機械鎖，只能靠收輪紀律回填）**
>
> 🔴 **provenance 逐格標註（R60 round 2 四方全數命中：ARCH-R60R2-02／SA-R60R2-02／SD-R60-R2-02／QA2-R60-01；DEF-101-563）**
>
> 本段原寫「量測時點＝R60 收尾工作樹…**四格皆另經 R60 SA 複審者獨立序列重跑覆核相符**」，
> 而 round 2 四方各自實跑 `ci-gate` 皆得 v0.30 = **1747**、本表卻寫 1736（round 1 時點值）
> ⇒ 該句在寫下時即為假。**一個宣稱「四格皆經獨立覆核」而其中一格與現場實測差 11 的表，
> 比沒有 provenance 宣稱更糟**（ARCH 原話）。故 provenance 改為**逐格標註**、不再由本段代言：
>
> 🔴 **下表是 R60 世代的史料，不是現行 provenance（R67 round 2 訂正，SA-R67-07）**：它描述的是
> 當時 **Windows 欄**四格的量測與覆核，寫下時為真；此後 R65（`58a829f`）**只**把 v0.30 一格回填
> 為 1750、其餘三格未動，四格自此**混世代** ⇒ 這正是 R67 把 Windows 欄 provenance 一律記
> `unrecorded` 的原因（見下方「Windows 欄為何整欄記 `unrecorded`」）。**現行 provenance 的唯一
> 來源＝各平台的 `snapshot-fingerprints-<平台鍵>` 錨**；下表只保留「當時誰量過什麼」的史料價值，
> **不得**再被讀成對現況的覆核宣稱——同一節裡留著兩套結論相反的 provenance 而不標世代，讀者會
> 採信先看到的那一套（本節 R60 的教訓原話：一個宣稱「四格皆經獨立覆核」而其中一格與現場實測
> 對不上的表，比沒有 provenance 宣稱更糟）。
>
> | 格（R60 世代史料） | 當時填的量測時點 | 當時誰實測過（R60 round 2 獨立重跑） |
> |---|---|---|
> | AutoClaude pytest | R60 收尾工作樹 | 主控 ＋ Architect（連 4 次）＋ SD ＋ QA（第 2 跑；第 1 跑的 1 failed 已證為 QA2-R60-04 並行假紅） |
> | ci-gate v0.01 | R60 收尾工作樹 | 主控 ＋ Architect ＋ SD ＋ QA（皆 1478） |
> | ci-gate v0.30 | **R60 round 3 訂正為 1747** | round 1 填 1736；round 2 Architect／SD／QA **三方獨立**皆測得 1747 ⇒ 該輪訂正。⚠️ **該值已於 R65（`58a829f`）被 1750 取代**，本列自 R65 起即為史料——R67 round 2 之前它仍以現行 provenance 的姿態與下方表② 的 1750 並存（SA-R67-07 命中） |
> | ci-gate scripts/tests | R60 收尾工作樹 | 主控 ＋ Architect ＋ SD ＋ QA（皆 249） |
>
> **為何這四格沒有 live 鎖（逐項說明，不是懶）**：AutoClaude 全套 pytest 單次約 78 秒、且對執行
> 旗標敏感（見該列歸因欄），把它塞進根層 unittest 閘門會讓每一次閘門執行都多付一整套測試的
> 代價；三格 `ci-gate` 需切到 `AISDLC_SDD/` 以另一組 `pytest.ini` 與另一棵 venv 執行，根層閘門
> 取不到現場值。**故這四格與表①刻意分開排版**——混排會讓讀者以為「有鎖所以可信」
> （R60 ARCH-R60-03 的原始成因就是一張表裡 1 格有鎖 4 格 stale）。
>
> 🔴 **但「沒有 live 鎖」不等於「只能靠人記得」（round 3 根治，DEF-101-563）**：本表四格改為
> **一條指令回填 ＋ 因果式 stale 觸發器**，取代「靠收輪紀律」這個純記憶機制——
> 上述 1736→1747 的復發，機制上就是「round 2 動了 v0.30 測試樹、沒人記得回填表②」。
>
> - **回填（一條指令）**：`python tools/sync_onboarding_baselines.py --write --with-slow`
>   ——實跑 `bash AISDLC_SDD/scripts/ci-gate.sh`（解析它自己的 `逐軌計數：vX:N` 自證行）
>   ＋ `python -m pytest tests/ -q`（plain 形態，與本表宣告一致），**本機平台那一欄**的四格一次
>   填完（R67 起；跨平台代填即假 provenance，故無對應欄的平台一律 rc=2 拒絕回填）。
>   ⚠️ 該指令在**可 import psycopg2／sqlalchemy 的 venv 上會 rc=2 拒跑**——那種環境會讓
>   AutoClaude 的 PG-gated 測試由 skip 轉 pass、`passed` 虛高，與本表宣告的出廠環境不是同一件事；
>   請改用只裝 `.[dev,notifications]` 的乾淨 venv，或明確加 `--allow-pg-extras` 讓 provenance
>   記下 `pgextras=present`。
> - **stale 觸發器（毫秒級，不必重測）**：下方**每個平台各一條** `snapshot-fingerprints-<平台鍵>`
>   錨，記錄「**該欄的數字是在哪一棵測試樹上量的**」＋ provenance（`measured-at` 何時／`host`
>   哪台機器／`docker` daemon 狀態／`pgextras` venv 有無 PG extras／`interpreter` 哪一支直譯器／
>   `sdk-extra` 有無 `claude_agent_sdk`）。🔴 **後兩欄是本輪 Q-03 補的**：同一棵樹、同一天、前四欄
>   完全相同，`.venv`／pyenv-win／出廠 cleanvenv 三支直譯器的 AutoClaude skipped 實測為
>   160／145／224——差 15 支而在錨上長得一模一樣。**它們是告知級、不計 rc**（相等判準會製造清不掉
>   的紅：回填必須在乾淨 venv、而 pre-push 跑的是帶 PG extras 的開發主樹，兩者結構上不同一支；
>   取捨逐字寫在 `tools/lib/baseline_origin.py::late_field_notices`）；有牙的是**欄位存在性**
>   ——缺席或改名即 fail-loud。`--check-snapshot` 重算並
>   比對，**本機平台那一欄的指紋一變就判 presumed stale 並紅**（其他平台欄自 R67 round 2 起改印
>   `ℹ️` 到 **stdout**、不再是 stderr 的 `⚠️`，且不影響 rc——別台機器的欄不是本機修得動的東西，
>   硬紅只會養成忽略紅燈的習慣）。🔴 **看到那則 `ℹ️` 不代表有新問題（QA-R67-05）**：在單機交替
>   的工作流下，非本機平台欄**結構上恆為 presumed stale**，該提醒因此是常態而非事件；它的內容
>   已由「四棵樹指紋 diff」（單機交替下必然變動、資訊量為零）改成「上次量測日期＋距今 N 天」，
>   `unrecorded` 另走「尚未建立基線」措辭（不得以漂移箭頭把「沒量過」寫成「過期」）。**真正有牙
>   的是本機平台欄那一行的 ✅／❌**——取捨論證逐字寫在 `tools/sync_onboarding_baselines.py` 的
>   `_stale_summary` docstring。判準是**因果的**：測試
>   計數只可能因測試樹變動而變（同 `ADR-SD09-011` 把「證據」從「日曆」解綁改綁「源碼變動」的
>   先例）。已接進 pre-push（收輪＝push 時點付這個代價才合理，刻意**不**接根層 unittest 閘門
>   ——那支每輪跑數十次，會逼人養成忽略紅燈的習慣）。**無對應欄的平台**（Linux CI runner）判準
>   退化為「**沒有任何一欄是新鮮的**」才紅——嚴格弱於逐欄判準，如實劃界。
> - 🔴 **R67 起本表逐欄記帳（R67-D1／D6）**：在 R67 之前，`--write --with-slow` 的欄位正則以
>   `**` 粗體硬綁 Windows 欄、全檔零平台偵測 ⇒ **在 macOS 上照本節指令回填，會把 macOS 實測值
>   靜默寫進標示「Windows 11 實測」的格子**；且指紋只有一條全域錨，另一欄的 stale 在結構上永遠
>   測不到（實測：macOS 欄灌成 9999 仍 ✅ rc=0）。現行實作以**表頭推導欄號 ＋ 只在該格內替換**，
>   寫到別欄在結構上不可能發生；`--platform` 只准用於唯讀稽核，與 `--write` 併用即 rc=2。
> - **誠實劃界（指紋抓不到什麼）**：指紋只覆蓋**測試樹**（`AISDLC_SDD_v0.01|v0.30/tools/fsm_runtime/tests/`、
>   `AISDLC_SDD/scripts/tests/`、`AutoClaude/tests/`）的 `*.py` 內容。理論上「生產碼變動改變
>   `parametrize` 來源」也能改變計數，該面**不在指紋內**；docker daemon 可用性、平台差異亦然
>   （見下方容差訂正段）。故它是 stale 的**充分觸發器、非必要條件**——會漏、不會冤。
> <!-- snapshot-fingerprints-darwin: v001=8ffe3c3dabbd v030=b17718d7e776 scripts=b5952a095a82 autoclaude=73924a086fde measured-at=2026-08-29 host=Darwin-25.6.0-arm64 docker=up pgextras=absent interpreter=mac_cleanvenv_20260829/bin@3.11.15 sdk-extra=absent baseline-origin=self-recorded ／ 由 `python tools/sync_onboarding_baselines.py --write --with-slow` 在 macOS 上維護，勿手改；刪除本標記會讓 --check-snapshot fail-loud -->
> <!-- snapshot-fingerprints-win32: v001=8ffe3c3dabbd v030=b17718d7e776 scripts=b5952a095a82 autoclaude=73924a086fde measured-at=2026-08-29 host=Windows-10-AMD64 docker=up pgextras=absent interpreter=autoclaude_cleanvenv_20260829/Scripts@3.11.9 sdk-extra=absent baseline-origin=self-recorded ／ 同上，由 Windows 側維護。🔴 該 origin 值的語意以 `tools/lib/baseline_origin.py::ORIGIN_SELF` 為準（本行不另寫一份定義）＝**本欄四格是在同一台 Windows 真機上一次量完、env 欄位在當時的定義下齊全**。🔴 兩條錨的後兩欄現值是 `tools/lib/baseline_origin.py::PRE_FIELD`＝**本錨早於那一欄**（不是「不可考」，也**不得**手填一個猜的值——那會把今天的環境寫在昨天的數字旁邊）；下一次在該平台跑 `--write --with-slow` 就會自動被真值取代 -->
>
> 🔴 **Windows 欄 provenance 沿革（史料段，非現況；R74 訂正）**：本段標題與內文自 R67 起逐字寫著
> 「Windows 欄整欄記 `unrecorded`」並解釋為何如此，而 R73 已在一台 Windows 真機上一次量完四格、
> 把上方 win32 錨回填成 `measured-at=2026-08-04 / host=Windows-10-AMD64 /
> baseline-origin=self-recorded` ⇒ **同一節裡並存兩套結論相反的 provenance 敘述**（錨說「當場記錄、
> 四項齊全」，散文說「整欄不可考」），而讀者採信先看到的那一句。這正是本節 R60 教訓（一個與現場
> 實測對不上的 provenance 宣稱比沒有宣稱更糟）在說明文字自身上的復發。**現行 provenance 一律看兩條
> `snapshot-fingerprints-<平台鍵>` 錨，不看本段。**
>
> 以下保留當時的處置理由作為史料（為何當時不填一個猜的指紋）：R67 建立逐平台記帳時實查 git 沿革，
> Windows 欄的四格**當時**是混世代——`v0.30` 那格於 R65（`58a829f`）回填 1747→1750，其餘三格更早
> （R60 世代），而 R66（`1cbe9fd`）又只把全域指紋洗綠、**計數一格未動**。四格既然不是在同一棵測試樹
> 上量的，就沒有任何單一指紋能誠實代表它 ⇒ 當時一律記 `unrecorded`，效果是該欄恆判 presumed stale，
> 直到有人在一台 Windows 上**一次量完四格**（`--write --with-slow`）——R73 做到了，所以那個狀態已經
> 結束。「填一個猜的指紋會讓一欄假裝新鮮」這個判斷本身至今不變。
>
> | 量測項 | macOS（provenance 見 snapshot-fingerprints-darwin 錨） | **Windows 11（provenance 見 snapshot-fingerprints-win32 錨）** | 差異歸因（實測，非推算） |
> |---|---|---|---|
> | AutoClaude `pytest tests/ -q` | **4542 passed / 225 skipped** | **4592 passed / 175 skipped** | 🔴 **R67 訂正一句已失實的宣稱（R67-F28 併同處理）**：本欄原寫「兩平台的 **passed+skipped 結果總數相同**（3948）」，而 R67 逐欄回填後 macOS 側 passed+skipped 與 Windows 側**都不等於 3948**——該總數是更早世代的值，兩欄本來就在不同時點、不同測試樹上量的（見各自 `snapshot-fingerprints-<平台>` 錨的 `measured-at`），**跨世代的兩欄本就不該相加比對**。故此處**不再寫死任何總數**：要比對兩平台，先確認兩欄的 `measured-at` 指向同一棵樹，否則差額只是時代差。〔**保留的二審 SA 訂正用詞**：`--collect-only` 的計數會**低於** passed+skipped，差額來自兩個模組級 `pytest.importorskip("sqlalchemy")`——sqlalchemy ABSENT 時整檔跳過、collect 少算但跑起來各記 1 skip。原寫「收集總數」會讓照本節驗證的人以為少了 3 支。〕Windows 上 `[WINDOWS-NATIVE-ONLY]` 標籤的 3 支（`test_perception.py::TestCloseKillsCmdShimGrandchild` 1 支、`test_run_local_nightly_static.py::TestConcurrencyGuardBehavior` 2 支）由 skip 轉 pass；反向新增 2 支 Windows 專屬 skip（`test_perception.py` POSIX process-group、`test_sdd_to_playbook_adapter.py` 無 symlink 權限 `[WinError 1314]`）。**殘差 ±1 未歸因**——需一台 macOS 同時量測才能對帳，本節依既定紀律**不做加減推算**、只填實測值 🔴 **量測旗標會改變結果（R60 ARCH-R60-04）**：本格值以 plain `python -m pytest tests/ -q` 量得；R60 四方複審在**同一棵工作樹**加 `PYTHONDONTWRITEBYTECODE=1 … -p no:cacheprovider` 後實測 rc=1（2~3 failed，失敗集中在 `tests/test_gap021_028.py` 的 `--collect-only` 子行程，其 rootdir 退化到磁碟根、掃到 system temp 兄弟項而撞 `WinError 2`），plain 兩次皆 rc=0。照本表驗證時請用 plain 形態；該非確定性已於 R60 立案（macOS 的 `/var/folders` 是同構暴露面）。<!-- autoclaude-pytest-snapshot: R60 round 3 錨點，勿刪；刪除本標記會讓 --check-snapshot fail-loud --> |
> | AISDLC_SDD `ci-gate` v0.01 | **1478** | **1478** | v0.01 的 3 支 docker 測試無 Windows 排除 ⇒ **本列的兩欄差額完全由 docker daemon 狀態解釋，不是平台差、更不是退化**（daemon 停用時該 3 支跳過＝ −3，方向與是否成立一律看兩欄各自的 provenance）。🔴 **R67 round 2 訂正（SA-R67-07 同類，本輪回填時自查發現）**：原句進一步寫死了「Windows 欄量測時 daemon 執行中／macOS 欄量測時 daemon 停用」這個**當時的組合**，而 R67 round 2 於 macOS 側回填時 daemon 為 `up`，該句當場失實（兩欄現為同值、差額 0）。**故此處不再寫死任何一欄的 daemon 狀態與差額方向**，一律現查：`grep -n 'snapshot-fingerprints-' ONBOARDING.md`（實跑 rc=0，兩條錨各印一行含 `docker=`）。🔴 **兩欄的 docker 狀態一律以各自 `snapshot-fingerprints-<平台>` 錨的 `docker=` provenance 為準**（R67 起機械記錄）——原句寫「本機 docker 執行中故全跑」而沒說「本機」是哪一台，正是 DEF-101-515「容差宣稱漏掉一個維度比沒有容差宣稱更糟」的同型。<!-- cigate-v001-snapshot: R60 round 3 錨點，勿刪；刪除本標記會讓 --check-snapshot fail-loud --> |
> | AISDLC_SDD `ci-gate` v0.30 | **1747** | **1746** | −4 ＝ 2 支 `test_phase_h.py` `requires_docker_success`（**`sys.platform.startswith("win")` 硬排除，與 docker 是否可用無關**，見 DEF-101-062）＋ 2 支 `test_post_commit_drift_worktree.py`（POSIX shebang hook chain，`skipif(win)`） 🔴 **R60 訂正：兩欄已不可直接相減**——上述 −4 是 R59 時的平台差（當時 Windows 1725 ／ macOS 1729）；R60 Windows 由 1725 增至**Windows 欄實測值**（本輪 v0.30 側新增回歸鎖；round 1 時點為 1736、round 2 四方三方獨立測得 1747 ⇒ round 3 訂正，過程見上方 provenance 表）。🔴 **R67 訂正**：此處原寫「而 macOS 欄仍是 R59 記載、本輪未重測」——R67 已在 macOS 真機一次量完四格並逐欄回填（provenance 見 `snapshot-fingerprints-darwin` 錨），該句已成假話故改寫；**兩欄現在也仍不可直接相減**，因為兩欄的 `measured-at`／`docker`／`pgextras` 不同（Windows 欄整欄 `unrecorded`，見上方說明），本節依既定紀律**不做加減推算**。🔴 **當輪值刻意不寫進歸因散文**（Cluster B 教訓：受管值在同一行出現第二次就是下一個 stale 站點）。<!-- cigate-v030-snapshot: R60 round 3 錨點，勿刪；刪除本標記會讓 --check-snapshot fail-loud --> |
> | AISDLC_SDD `ci-gate` scripts/tests | **348** | **349** | R59 動工時實測 245（比 R57 記載的 244 +1，未追查是平台差異或 R57 收尾後的回填落差）；收尾為 248＝再 +3，即 DEF-101-512 的兩道降級 fallback 鎖 + QA-R59-10 的 `-rs` 鎖；**R60 收尾見 Windows 欄**＝再 +1（本輪 `AISDLC_SDD/scripts/tests/` 側之鎖；`--collect-only` 實測較 passed 數多 1 collected＝多出的那支為 skip，與 passed 數相符）。**未逐支追認該 +1 的來源**，依紀律只填實測值、不做歸因推算。🔴 **當輪值刻意不寫進歸因散文**（同上，Cluster B 教訓）。<!-- cigate-scripts-snapshot: R60 round 3 錨點，勿刪；刪除本標記會讓 --check-snapshot fail-loud --> |
>
> **表③ — 雲端 CI 狀態（R74 新增；「本機全綠但雲端紅」唯一會顯形的地方）**
>
> 🔴 **為何非加這張表不可（R74 的 P0，本節自己就是活體樣本）**：表①②量的全是**本機**——
> 六道根層閘門、四棵測試樹、LOC。R73 收輪時這些全綠、`82eee92` 推上去，而**同一個 commit 的
> `windows-compat-ci` 在雲端是 `failure`**（唯讀實查：`gh run list --workflow windows-compat-ci.yml
> --event push --limit 1`）。這件事在結構上不可能被任何本機機械物報出來：本節此前**零欄位**承載
> 雲端結論，而 `tools/lib/ci_liveness.py` 的哨兵只查**排程軌**活性（`--event schedule` /
> `workflow_dispatch`），push 軌完全不在它視野內。於是「本機閘門全綠」被讀成「這個 commit 是綠的」
> ——與 DEF-101-756（缺記錄被寫成缺量測）同型，只是這次缺的是**平面**：地端 ≠ 雲端。
>
> 🔴 **本節先前逐字宣告的那條「回填了本機基線卻沒重查雲端就會紅」的新鮮度判準，實作裡一行都沒有
> ——本輪（D-01）訂正**。它曾經存在（比的是 `checked-at` 與兩條 `snapshot-fingerprints` 錨
> `measured-at` 的**日期字串**），但 QA-R74-01 已指出那種比較在一輪之內結構上不可能觸發，R75 修
> 「判準的比較對象不得隨被它所判的動作而改變」那個死結時**把整層拿掉了**，而這兩句散文沒有跟著改
> ⇒ 讀者會以為「動了本機基線就會被逼著重查雲端」，於是不去查。當回合注入實測：把兩條錨的
> `measured-at` 推到 2099-12-31，`cloud_status_problems` 仍回 `[]`（對照組把 `head-sha` 換成全零則
> 立刻紅 ⇒ 探針本身有鑑別力）。**現行判準的權威清單一律以
> `tools/tests/test_doc_loc_baseline_freshness_r60.py::cloud_status_problems` 為準**（本節不另寫一份
> 會漂的複本）；它逐條掛的是：掃描面完整性／`pending` 非假性／`head-sha` 形態＋真 commit＋HEAD 祖先／
> `checked-at` ↔ commit 時間的**因果**／`red` ↔ 表格 failure 列／`nightly-red` 三欄與 14 天過期帶。
> **沒有任何一條讀 `snapshot-fingerprints`。**
>
> 掃描面是現查的：`.github/workflows/*.yml` 中**帶 `push:` 觸發**的每一支都必須在本表有一列，
> 新增一支 push 軌而沒記進來即紅——不靠任何人記得。
> ⚠️ **「錨有沒有覆蓋最新一次 push」結構上不可能由住在被測 commit 內的測試回答**（見下方分工表），
> 那一半至今仍是人工；別把上面那串判準讀成「有機械物在盯著雲端現況」。
>
> **回填（一條指令，逐 workflow 現查）**：
>
> ```powershell
> foreach($wf in (Get-ChildItem '.github\workflows\*.yml').Name){
>   gh run list --workflow $wf --event push --limit 1 --json conclusion,headSha,updatedAt,url }
> ```
>
> | workflow（push 軌） | 最近一次 push run 結論 | 該 run 的 commit | 判讀 |
> |---|---|---|---|
> | `windows-compat-ci.yml` | 🔴 **failure** | `a1ee537` | 🔴 **本表存在的理由（史料保留）**：R73 收輪時六道本機閘門全綠、而雲端這支在 `82eee92` 上是紅的，沒有任何本機機械物報得出來。R74 修掉那筆、R75 又因「判準拿會隨 push 前進的參照當比較對象」讓它連同另兩支再紅一次。**本輪現值＝failure，成因已逐筆查證：`gh run view 31027341743 --json jobs` 顯示三個 job 的 steps 數皆為 0＝GitHub Actions 帳務停擺造成的未啟動，不是程式碼紅**；但本表記的欄位就是 run 層 conclusion，成因不改變它的值，故不得寫成綠（那正是本表存在理由的反面） |
> | `macos-compat-ci.yml` | 🔴 **failure** | `a1ee537` | 同上未啟動（run `31027341732`）。三支同時、同一秒、同一種形態 ⇒ 與程式碼無關 |
> | `root-infra-ci.yml` | 🔴 **failure** | `a1ee537` | 同上未啟動（run `31027341879`） |
> | `autoclaude-ci.yml` | ✅ success | `5993f09` | 該 workflow 的 `paths:` 過濾使 `a1ee537`（純文件 commit）**未觸發** ⇒ commit 欄照實記那次 run 的 sha，不得填 HEAD（見下一列的完整說明） |
> | `aisdlc-sdd-ci.yml` | ✅ success | `5993f09` | 同上未觸發。**「沒觸發」與「跑過且綠」在 GitHub UI 上長得一樣**，故 commit 欄一律照實記那次 run 的 sha、不得填 HEAD——本列的 sha 本次由現查前進（前一版記的是更早那次 run） |
> | `autoclaude-mutation-on-change.yml` | ✅ success | `0b6468b` | 同上未觸發（源碼變動觸發軌，見 `ADR-SD09-011`） |
> | `shellcheck-ci.yml` | ⏳ **雲端尚未執行過** | （無） | R80 新生（DEF-101-937 接電 shellcheck）；本輪尚未 push，故雲端**零次** run，commit 欄刻意留「（無）」而不是抄一個 HEAD 上去——那會讓「沒跑過」長得像「跑過且綠」，正是本表存在的理由。首次 push 後依上方 SOP 回填真實 run 結論。本機唯一執行者＝`python tools/run_shellcheck.py`（載具缺席 rc=2 fail-loud），且它**尚未**接進 pre-push（見 DEF-101-938） |
>
> ⚠️ **本表刻意不含 `conclusion` 之外的判定**：一個 run 的 `conclusion=success` **不代表**它裡面
> 每個 job 都綠——兩支 compat-CI 的 `*-nightly-full` 帶 job 層 `continue-on-error: true`，紅了
> run 仍是 success（R74 已讓 `tools/lib/ci_liveness.py::run_level_fail_open` 把這件事逐字說出來）。
> 要看真實 job 結論：`gh run view <run-id> --json jobs`。
>
> **表③-b — 兩支 compat-CI 的 `continue-on-error` nightly job（上表結構上看不到的那一半）**
>
> 🔴 **為何非另立一張表不可（R76-03）**：上表記的是 **run 層 conclusion**，而這兩支 job 的紅
> 被 `continue-on-error: true` 吸收掉 ⇒ 上表照實填 `success` 也**不算填錯**，問題正在這裡。
> 這條紅唯一的顯形通道是 GitHub issue，而該通道**零讀者**：實查唯一一筆 issue #10 自
> 2026-07-14 起 OPEN、橫跨 R72~R75 四輪「雲端全綠」宣稱都沒人讀到。
>
> 🔴 **取樣的是各自最近一次 `--event schedule` 的 run，不是 push run**：這兩支 job 在 push 事件
> 上一律 `skipped`（實查 a61bf0c 的 windows run：nightly-full 與 nightly-alert 皆 skipped）
> ⇒ 若照 push run 記帳，這一欄結構上恆為 `none`＝一道永遠不會響的鎖。**它們的 provenance 因此
> 與上表不同**（不同 run、不同 commit、週頻），故逐列自帶 run 與 commit，不共用上方的錨欄位。
>
> 🔴 **第一欄刻意放 job id 而不是 workflow 檔名**：上表的判準⑦ 以「列首是反引號包住的 `*.yml`」
> 認列，把 workflow 檔名擺第一格會讓本表被它一起吃進去、`failure` 列被要求進上表的紅集合。
> 兩張表的紅集合是兩個不同的東西，**不要「整理」成同一種列首**。
>
> | job id | workflow | 最近一次 schedule run 結論 | run id ／ commit | 判讀 |
> |---|---|---|---|---|
> | `windows-nightly-full` | windows-compat-ci.yml | 🔴 **failure** | `32004746324` ／ `45ba6115` | R98 收尾現查（2026-08-21）：job 層 `steps=0` ⇒ 帳務停擺造成的未啟動，非程式碼紅（同 macos 那列同一成因） |
> | `macos-nightly-full` | macos-compat-ci.yml | 🔴 **failure** | `32008307980` ／ `45ba6115` | R98 收尾現查（2026-08-21）：job 層 `steps=0`（同一次排程視窗、同一成因），非「這種 job 本來就會紅」——此前 R76 的對照組已不成立，兩支目前同為帳務停擺型未啟動 |
>
> 對應的機器欄位是錨上的 `nightly-red`（值＝以逗號分隔的 `<workflow 檔名>:<job id>` 集合，
> 全綠時寫 none）。它與 `red` 欄刻意分開：`red` 對的是 push 軌 run 層、`nightly-red` 對的是
> 排程軌 job 層，混成一欄就等於把「被 `continue-on-error` 吸收掉」這件事又蓋回去。
>
> 🔴 **回填 SOP（QA-R74-01 訂立 — 照這五步做，填錯會紅）**。下方那個錨是表③ 的機械受檢面；
> 它的每一個欄位都有判準，**不是註解**：
>
> 1. **push 之後**，等五支 push 軌 run 全部 `completed`（R74 起的硬規則：不等結論就收輪＝把紅
>    留給下一輪開場才發現）。
> 2. 跑上方那條 `gh run list` 指令，把每一支的 `conclusion` / `headSha` 抄進表格列。
> 3. 錨的 `head-sha=` 填**完整 40 位 sha**（不是短 sha）：判準會驗它①形態合法、②在本 repo
>    解析得出 commit 物件、③是 HEAD 本身或 HEAD 的祖先。填全零、短 sha、別的分支的 sha 都會紅。
> 4. 錨的 `checked-at=` **請填帶時間的 ISO8601**（例 `2026-08-05T14:30:00+08:00`）。判準會驗它
>    不早於 `head-sha` 那個 commit 自己的提交時間（因果）。**只寫到日就必須同時寫
>    `granularity=day`**，明說這份新鮮度只到「日」——本 repo 一輪常在同一天內做完多個 commit，
>    日粒度在一輪之內抓不到「錨落後一個 commit」，那個弱點必須寫在錨上而不是靜默存在。
> 5. 錨的 `red=` 必須**逐字等於**表格裡結論為 `failure` 的 workflow 集合（全綠就寫 `red=none`）。
>    這一條比的是內容不是日期，所以「改了表格忘了改錨」在同一天內也會紅。
> 6. **（R76-03 新增）另記表③-b 與錨的 `nightly-red` 欄**——兩支 compat-CI 帶
>    `continue-on-error` 的 job，其紅**不會**出現在第 2 步那條指令的 `conclusion` 裡。
>    逐支現查各自最近一次**排程軌** run 的 job 層結論：
>
>    ```powershell
>    foreach($wf in @('windows-compat-ci.yml','macos-compat-ci.yml')){
>      $r = gh run list --workflow $wf --event schedule --limit 1 `
>             --json conclusion,headSha,databaseId | ConvertFrom-Json
>      gh run view $r.databaseId --json jobs --jq '.jobs[] | "\(.name) => \(.conclusion)"' }
>    ```
>
>    把結果填進表③-b，錨的 `nightly-red` 欄則填**以逗號分隔的 `<workflow 檔名>:<job id>`
>    集合**（全綠寫 none）。⚠️ 這一欄取樣的是**排程軌**：push run 上這兩支恆為 `skipped`，
>    照 push run 記帳會讓它結構上恆綠——那就白做了（同「判準的比較對象要選對」那條教訓）。
>    ⚠️ 本欄與 `checked-at`／`head-sha` **不同步**（週頻 vs 每次 push），故 provenance 逐列
>    寫在表③-b 裡，不要拿上表的 commit 去代言它。
>
>    🔴 **（R76 複審 ARCH-03 補）同時更新錨上另外兩欄，缺一即紅**：
>    `nightly-run=<那一次 schedule run 的 databaseId>`（必須逐字出現在表③-b 的 run id 欄，
>    這是錨 ↔ 表格的內容綁定，同 `red=` 那條）、`nightly-checked-at=<帶時區的 ISO8601>`
>    （這一次查核的時點）。**`nightly-red=none` 也必須帶這兩欄**——沒有 provenance 時
>    「沒查」與「查過全綠」在錨上長得一模一樣。判準另設**過期帶 14 天**（＝排程軌兩個
>    週期），逾期即紅並在訊息裡印回這一段指令。
>
>    ⚠️ **這一欄的失明面（誠實劃界，勿超譯）**：機械物保證的是「有人在 14 天內查過並
>    留下 run-id、而且那個 run-id 對得上表③-b」，**不是**「此刻雲端的 job 結論就是錨上
>    寫的那樣」。本判準不去雲端對帳（那要拿 push 之後才確定的值來比，見下方 §「一般化的
>    規則」）。R76 之前這一欄連時點都沒有，於是 PKG-B 修好 `windows-nightly-full` 之後
>    錨仍會逐字宣告它是紅的、而鎖照樣綠——**一句被鎖守著的假話**；反向若下週換
>    `macos-nightly-full` 轉紅，判準也一行都不會響。過期帶治的就是這兩個方向。
>
> 🔴 **「還沒查」怎麼合法表達**：輪次進行中的常態就是「推上去了、run 還在跑／還沒去查」。這個
> 狀態**要誠實寫出來，不准用填假值讓它變綠**：在錨上加一欄
>
> ```
> pending=<那個已 push、但結論還沒進本表的 commit 的完整 40 位 sha>
> ```
>
> 語意＝「這個 commit 已 push，它的結論**尚未**進本表；本表現有結論覆蓋的是 `head-sha` 那個
> 較舊的 commit」。此時 `checked-at`／`head-sha`／表格列**一律保持原值不動**——它們記載的是
> 一次**真的發生過**的查核，改動它們就是宣稱一次沒發生過的查核（`[[no-fabricated-tool-output]]`）。
> 查完之後：把真實結論填進表格、`head-sha` 改成那個 commit、**刪掉 `pending=` 欄**。
>
> 🔴 **哪一半由 CI 守、哪一半由 pre-push 守（R75 付了代價才劃清的界線）**：
>
> | 問題 | 誰能回答 | 現況 |
> |---|---|---|
> | 錨**有沒有說假話**（sha 是否真實、是否 HEAD 祖先、`checked-at` 是否早於它所評的 commit、`red=` 是否對得上表格列、同欄位是否重複衝突） | **repo 內的測試（CI 會跑）** | 已機械化，見上方 `TestR74CloudCiStatusIsRecorded` |
> | 錨**有沒有覆蓋最新一次 push** | **只有 pre-push／收輪清單** | 人工，見下方 ⚠️ |
>
> **為什麼第二列不可能由 CI 守（不是偷懶，是結構）**：CI 在 push **之後**才跑，那時「最後一次
> push 的 commit」就等於**被測的那個 commit 自己**。要讓 commit X 通過這種判準，X 的檔案內容
> 就得寫進 X 自己的 sha——而 sha 是 X 內容的雜湊，**自我指涉、任何 commit 都滿足不了**。R75
> 第一版正是這樣寫的，實測代價是 main 上三支 workflow 全紅、且**每一次 push 都會紅**。
> 這條教訓已升為機械物 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit`：判準的執行碼裡出現
> 任何 remote-tracking 參照（`origin/…`／`@{u}`／`ls-remote` 等）即當場判紅。
>
> **一般化的規則（比這個個案重要）**：**判準的比較對象若會隨「被該判準所判的那個動作」本身而
> 改變，這個判準結構上不可滿足。** 遇到這種問題，判準要拆成「內部一致性／非假性」（可住在
> repo 內）與「與外部世界對帳」（只能住在動作發生的那個時點）兩半。
>
> ⚠️ **殘留缺口（誠實揭露）**：「收輪前必須把 `pending` 解除」目前**沒有** rc 級機械物——它的
> 正確歸宿是 pre-push（比照 `--check-snapshot` 只接 pre-push 的既有先例，在那個時點
> `origin/main` 尚未前進、比較才有意義，而「去查雲端」那時也真的做得到），需在
> `tools/sync_onboarding_baselines.py` 加一條，屬另一件事。在那之前，收輪檢查清單第一項＝
> **確認本錨沒有 `pending` 欄**。
>
> <!-- cloud-ci-status: checked-at=2026-08-06T09:41:12+08:00 head-sha=a1ee5379d2e5a6880c5e7a2bcdaee8e936a51fb1 red=windows-compat-ci.yml,macos-compat-ci.yml,root-infra-ci.yml nightly-red=windows-compat-ci.yml:windows-nightly-full,macos-compat-ci.yml:macos-nightly-full nightly-run=32004746324 nightly-checked-at=2026-08-21T14:05:45+08:00 ／ 由上方 gh 指令現查後手動回填，回填步驟見上方六步 SOP；`tools/tests/test_doc_loc_baseline_freshness_r60.py` 的 TestR74CloudCiStatusIsRecorded 機械守。🔴 **判準清單一律以該檔的 `cloud_status_problems` 為準，本行不再列舉**（本輪 D-01：先前這裡逐項抄了一份，其中「新鮮度」那一項在 R75 拿掉整層之後就成了假話，而抄本沒有任何東西在守——同一份知識住兩個家、只有一個家被鎖）。🔴 本錨現值＝**本輪重查一次的結果**：前一版停在 `a61bf0c`、落後 HEAD 四個 commit 且宣告全綠；當回合逐支現查，三支 compat／root-infra 對 HEAD 的最近一次 push run 皆 completed 而 conclusion 為 failure，故 `red` 欄照實列出那三支（另三支因 `paths:` 過濾未觸發，commit 欄照實記各自最近一次 push run 的 sha，見表格判讀欄）。🔴 **那三筆的成因已逐筆查證＝Actions 帳務停擺造成的未啟動（每個 job 的 steps 數皆為 0），不是程式碼紅**——但本表記的欄位就是 conclusion，成因不改變它的值，**不得**因為「不是真紅」而填成綠。`pending` 欄不填：本次查的就是 HEAD 自己，沒有任何「已 push 而結論未進表」的較新 commit。`granularity` 欄亦已刪除——`checked-at` 現在帶完整時間與時區，再自陳「只到日」就是一句與同一行資料矛盾的假話，該矛盾另有判準守。🔴 **R76-03 新增的那一欄（表③-b 的機器面）取樣的是排程軌 job 層、不是 push 軌 run 層**，故它的新鮮度與本行其餘欄位**刻意不同步**（週頻 vs 每次 push），逐列 provenance 寫在表③-b；現值指向的是本輪（R98 收尾，2026-08-21）重查的結果：`windows-nightly-full` 與 `macos-nightly-full` 兩列這次同為 failure（皆 steps 為零，帳務停擺型未啟動，非程式碼紅）——前一版本錨記的「macos 側是綠的對照組」在這次重查已不成立，故本輪同步改記兩列，那筆紅在 run 層看不見，正是它存在的理由。🔴 **R76 複審 ARCH-03 之後，這一欄自己也帶時點與出處**（`nightly-run` 是那一次 schedule run 的 databaseId、必須逐字對得上表③-b；`nightly-checked-at` 是查核時點，逾 14 天即紅）——沒有這兩欄的話，本欄只保證「有人查過一次」而不是「現在是什麼狀態」，於是「修好之後沒人回來清」與「新的紅沒人補進來」兩個方向都不會有任何東西出聲。🔴 **本行的說明文字刻意不寫出任何 `欄位＝值` 形態的字樣**：機器欄位與人讀散文同住這一行，散文裡只要出現可被解析的那種寫法就會覆蓋真欄位值（本輪已兩度實測踩到，第二次是由該筆的根治判準自己抓出來的）。🔴 下一次 push 之後本表即成為 dated snapshot，收輪檢查清單第一項＝重跑上方 gh 指令、確認六列與錨都對得上現況（該項無 rc 級機械物，且刻意不做成 CI 判準——會不可滿足，見上方分工表與 TestR75CloudCriteriaAreSatisfiableAtAnyCommit）。刪除本標記會讓該鎖 fail-loud -->
>
> **訂正一項已被證偽的容差宣稱（DEF-101-515 併同處理）**：本節下方 R33 註尾原寫「`ci-gate.sh`
> 的逐軌 passed 計數對 **docker daemon 可用性**敏感（daemon 停用時 v0.01／v0.30 各 -3），
> ±3 屬環境因素非退化」。該句**只涵蓋 docker 這一個維度，完全沒有平台維度**，於是 Windows 上
> 實測的 v0.30 −4 落在宣稱容差之外 → 依文件字面應判定為「退化」，而實況是 2 支平台硬排除
> ＋2 支 docker-success 排除、零退化。**在容差宣稱裡漏掉一個維度，比沒有容差宣稱更糟**：
> 它會主動把正確的平台差異誤導成迴歸。正確判準見上表「差異歸因」欄。
>
> **本表的量測時點宣告（R59 SA-R59-01 訂正 → R60 SA-R60-01／ARCH-R60-03 重寫）**：量測時點已改為**寫在各表表頭**（表①、表②皆為 R60 收尾工作樹），不再由本段代言——⚠️ 原句寫「上表四組數字皆為 **R59 收尾工作樹**…一次性重測所得」，R60 複審實測該句已成假話：R60 只回填了 LOC 一格，其餘四格仍是 R59 值，一張表混兩個時代，而表頭又標「R59 實測」，照本節自陳目的（讓開發者分辨平台差異與退化）驗證的人必然把正常狀態誤判為退化。**兩則訂正紀實刻意逐字保留（歷史校正註記，不改寫）**——(a)〔R59〕**訂正紀實**：本表初版誤填了「根層 616 / scripts/tests 245」兩個**動工時**的中途值，與同輪缺陷帳本 DEF-101-519 自己記的 653 互相矛盾——這正是本節 R56 註記警告過、且本輪 DEF-101-515 要根治的同一形態在修復內部原地復發（且 `MIN_TESTS` 的 ratchet 警戒線 616×1.10=677.6 > 653，**沒有任何機械物會抓到它**，是靠 SA 人工對帳抓出）。 (b)〔R60〕本節被宣告為「全 repo pytest 基線數字唯一站點」，但唯一站點只保證『數字只住一個家』（`tools/check_pytest_baseline_sites.py` 守的就只有這件事），**完全不保證那個家裡的數字是新鮮的**；R60 為 LOC 一格加了新鮮度鎖後，反而讓同一張表出現「1 格有鎖、4 格 stale」的內部矛盾，其中根層那格寫 661 而 `tools/run_root_unittests.py` 的 `MIN_TESTS` 已重釘 **756**——同一份 repo 對同一個數字兩種說法（DEF-101-066／DEF-101-515 家族）。根治手段＝表①的 live 鎖（取值來源是機器）＋ `tools/sync_onboarding_baselines.py` 產生器，並把「機器算不出來的四格」明確隔到表②、標為 dated snapshot、寫明為何沒有鎖。**下一輪讀本節時請先分清自己看的是表①還是表②**：表①錯了會有紅燈，表②錯了只有人審會抓到。
>
> 🔴 **污染檢查手法訂正（R59，DEF-101-516）— 下方 R56 註訂的規則在 uv 建的 venv 上零鑑別力**
>
> R56 註尾訂下的方法論是：「往後污染檢查一律改用在乾淨環境會**印出東西**的寫法（如
> `python -m pip list | grep -E "psycopg2|sqlalchemy"`），判準是『輸出在乾淨與污染下長得夠不夠
> 不一樣』」。該判準本身正確，但**選定的指令不滿足它自己的判準**：根 CLAUDE.md 明載
> `tools/bootstrap.*` 偵測到 `uv` 時一律用 `uv venv` 建置（＝**預設路徑**），而這種 venv
> **內部沒有 `pip` 模組**——`python -m pip list` 直接報 `No module named pip`、stdout 為空，
> grep 零命中，讀起來與「乾淨」**一模一樣**。R59 於本機實測重現（`python -m pip --version`
> → `No module named pip`），這正是 R56 想根除的「假乾淨」，只是換了一條路徑進來（同族第四次）。
>
> **改用以下寫法**（不依賴 pip 是否存在，且乾淨/污染兩種情況都必定印出東西）：
>
> ```bash
> # 兩平台同形；.venv/Scripts/python.exe（Windows）或 .venv/bin/python（macOS）
> python -c "import importlib.util as u; [print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') for m in ('psycopg2','sqlalchemy')]"
> ```
>
> 判準：兩行都必須是 `ABSENT` 才算乾淨。**任何一行印不出來就是探針壞了**（而非「乾淨」）——
> 這是這個寫法相對 `pip list | grep` 的關鍵差異：它沒有「靜默零輸出」這個狀態。
> 若堅持用 pip 清單形態，在 uv venv 下必須改用 `uv pip list`（不是 `python -m pip list`）。
>
> 註：**R57 校正（2026-07-27，五維掃描 18 項候選＋四包並行修復＋四方複審）**——本輪 AutoClaude pytest 基線於**全新臨時目錄建立的乾淨 venv**（`/opt/homebrew/bin/python3.11 -m venv` + `uv pip install -e '.[dev,notifications]'`；污染檢查改用 R56 教訓所訂的「乾淨時會印出東西」寫法 `python -m pip list | grep -E "psycopg2|sqlalchemy"` → 零輸出確認乾淨）下量測，結果為 **3738 passed / 210 skipped**（77.00s，量測平台：macOS、巢狀 Claude Code session），**與 R56 相同不變**——本輪唯一動到 `autoclaude/` 的修復是 `utils/logger.py::_sanitize_log_filename` 的保留裝置名尾隨空白缺口（DEF-101-478 第 ④ 處），其回歸鎖依「三方交叉鎖同檔並列」慣例放在根層 `tools/tests/test_windows_forbidden_filename_parity.py`，不計入 AutoClaude 側數字。其餘子專案數字（不計入本節 AutoClaude pytest）：根層 `tools/run_root_unittests.py` **616 tests OK/skipped=4**（R56 為 530，本輪 **+86**，`MIN_TESTS` 同步重釘為 616）；AISDLC_SDD `bash scripts/ci-gate.sh` 全綠，逐軌 v0.01:1478／v0.30:1729／scripts/tests:**244**（R56 為 238，本輪 +6）。**逐項支數刻意不細列到個位數**——R57 三度以算式推算根層測試數（552／558／584）皆當場與實況不符（SD-R57-01／QA-R57-07 抓出兩次；四方複審共三輪、每輪修復都會再增減測試，故最終值 615 亦是收尾當下實測而非累加），`MIN_TESTS` 的重釘判準已明定為「所有並行 agent 停工後，填最終工作樹實測值、不做任何加減推算」，本節敘述同此政策；欲知逐檔增量請直接 `git diff --stat`。`AutoClaude/tools/check_loc_budget.py` total=20356／cap=20438／violations=0（**此為 R57 當時值**，該輪不變——當時 `logger.py` 只增註解不增邏輯行；**現行值請看本節上方 Windows 11 基線表的 LOC 那格**，該格自 R60 起有機械鎖守新鮮，本則歷史註記刻意不回填）。**本節四組數字皆為所有並行 agent 停工後、由主控在最終工作樹上一次性重測所得。**
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
> 舊註（**R33 校正，2026-07-24，DEF-101-289 收斂**）——巢狀 Claude Code session 下基線曾為 **3,644 passed / 210 skipped**（R27~R32 累積新增測試案例 `test_run_act_core.py`／`test_bash_probe_spec_contract.py`／`test_bootstrap_ps1.py` 平台守門等皆已反映在此）；當時數字於全新臨時目錄建立的乾淨 venv（`pip install -e '.[dev,notifications]'`，不含 postgres/pgvector 選配，`pip list` 確認乾淨）下量測，非既有共用 `.venv`——R32 曾因既有 `.venv` 意外裝有 `psycopg2`/`sqlalchemy` 選配、PG-gated 測試從 skip 轉 pass 造成數字虛高（3742/146）而擱置未更新，本次已排除此污染。**bootstrap 出廠環境**（非巢狀 session、全新乾淨 venv）數字**本輪未重新量測**——舊數字（3,566 passed / 196 skipped）維持標示為待重驗，需另起一個不在巢狀 Claude Code session 下的全新環境實測後才能校正。（根層 CLAUDE.md 與 AutoClaude 兩檔已於 R13 收斂為指向本節、不再重複數字）。**方法論澄清（R13 校正歷史，供未來重驗參照）**：本欄曾有一版誤標為 3,664/132，經 SA 複審抓出根因是量測時用了主目錄既有、已裝 `[postgres]` 選配（`psycopg2-binary`/`SQLAlchemy`）的 `.venv`，PG-gated 測試從 skip 轉 pass 造成數字虛高，不符本節自稱的「出廠環境」方法論；未來重驗數字時務必改用全新乾淨 venv〔`pip install -e 'AutoClaude[dev,notifications,lint]'`，不含 postgres 選配；**R57 純加引號修正、無數字變動**——zsh 下未加引號會 `no matches found` 中止，見 §5〕。skipped 中屬選配依賴缺席者（PG DSN 未設／sqlalchemy 與 `[postgres]` 未裝／claude_agent_sdk 未裝）為預期，非測試退化。AISDLC_SDD `ci-gate.sh` 的逐軌 passed 計數對 **docker daemon 可用性**敏感（daemon 停用時 v0.01／v0.30 各 -3＝`test_phase_h` 的 docker 場景 SKIP），±3 屬環境因素非退化。**⚠️ R59 訂正：本句只涵蓋 docker 一個維度、漏掉平台維度，在 Windows 上會主動把正確的平台差異誤導成迴歸（實測 v0.30 −4 落在此宣稱容差之外，而實況零退化）。正確判準見本節上方「Windows 11 側基線」表的「差異歸因」欄（DEF-101-515）。本句刻意逐字保留不改寫**——它是歷史校正註記的原文，改寫會破壞該註記的時代快照性質；訂正以本標記就地指路。

### 7.1 跑全套測試看到大量 `skipped`？先把 CI 對等 PG 容器拉起來（R83）

🔴 **為何非寫這一節不可**：掌舵者連續多輪問「為什麼有 skipped、要怎麼徹底解決」，而 AutoClaude 這一側**佔最大宗的那一類**（R83 於 macOS 實測為最大單一類；比例是量測值，見下方現查）的答案就是**一行 `docker compose` 指令**——不必改任何程式、跑測試時不必設任何環境變數（`AutoClaude/tests/conftest.py` 的 PG autodetect 會自己偵測並注入 DSN）。這件事在 R83 之前**在本文件與 `useMacWin.md` 裡都找不到**：`AutoClaude/docker-compose.ci.yml` 檔頭寫過用法，但那是「已經知道要找它」的人才會打開的檔。⇒ 這是**可發現性缺陷**，不是技術缺陷；技術面早在 R79 就做完了。

**做法（兩平台各一份，可直接貼）**

```bash
# macOS / Linux — ① 先確定 docker daemon 真的在跑（Windows 側請見下一塊）
open -a Docker            # macOS：啟動 Docker Desktop（Linux 用 systemctl start docker）
docker info --format '{{.ServerVersion}}'    # 印得出版本號才算 daemon 活著

# ② 拉起 CI 對等 PG（pg17 + pgvector，與 autoclaude-ci.yml 同鏡像）
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d
docker compose -f docker-compose.ci.yml ps   # 要看到 healthy

# ③ 這顆容器是 tmpfs、用完即丟 ⇒ 每次新建都要 migrate 一次，否則 autodetect 的第 ④ 條剎車會拒絕注入。
#    🔴 這一步**必須自己給 DSN**：autodetect 只注入 pytest **那一個行程**的環境變數，alembic 是
#    另一個行程（實測不給時 rc=2、印「❌ 缺少 PostgreSQL DSN」）。刻意用行內前綴而不是 export——
#    一旦 export 出去，pytest 會走「顯式優先」那條剎車，第 ④ 步的憑證行改印
#    `[PG autodetect] 跳過：AUTOCLAUDE_DB_DSN 已由使用者顯式設定（顯式優先）`（實測）。
#    PG 照樣接得上、測試結果不變，但你就驗不到「autodetect 這條路是通的」這件事
AUTOCLAUDE_DB_DSN='postgresql://autoclaude:autoclaude@localhost:5432/autoclaude' alembic upgrade head

# ④ 照常跑——**這一步**才是「不必設任何環境變數」的那一步（第 ③ 步的 DSN 是給 alembic 的，不留在環境裡）
python -m pytest tests/ -q
```

```powershell
# Windows — ① 先啟動 Docker Desktop（GUI，或 Start-Process），再確認 daemon 活著
docker info --format '{{.ServerVersion}}'
# ② 拉起 CI 對等 PG
#    🔴 定位子專案目錄一律走 `git rev-parse --show-toplevel`（同鐵律二：絕對路徑、不用裸 cd）。
#    **不要**寫 `$env:CLAUDE_PROJECT_DIR\AutoClaude`：那個變數只由 Claude Code 注入 hook 子行程，
#    開發者自己開的終端機裡是空的（本輪實測：一般 shell 內未設定），PowerShell 會把它展開成
#    空字串 ⇒ `Push-Location \AutoClaude` 去敲磁碟機根目錄，實測逐字 `Cannot find path
#    '/AutoClaude' because it does not exist.`（pwsh 7 實跑；Windows 上等價地變成 `C:\AutoClaude`）
Push-Location (Join-Path (git rev-parse --show-toplevel) 'AutoClaude'); docker compose -f docker-compose.ci.yml up -d; Pop-Location
# ③ migrate（PowerShell 沒有行內環境變數前綴語法 ⇒ 設完必須清掉，否則第 ④ 步的 autodetect 會被「顯式優先」剎車擋下）
Push-Location (Join-Path (git rev-parse --show-toplevel) 'AutoClaude')
$env:AUTOCLAUDE_DB_DSN = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
alembic upgrade head
Remove-Item Env:\AUTOCLAUDE_DB_DSN
# ④ 照常跑
python -m pytest tests/ -q
Pop-Location
```

**憑證（照做之後應該看到的東西）**——pytest 尾端會多印這兩行，貼不出它們就代表沒生效：

```
AUTOCLAUDE-PG-DSN-IN-EFFECT=1 ...
[PG autodetect] 已注入 AUTOCLAUDE_DB_DSN／AUTOCLAUDE_TEST_PG_DSN = postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude
```

**它消掉幾支是量測值，本節刻意不寫死**（本 repo 明文禁止把會漂移的量測常數寫進散文——同 §7 表①②「受管值不得在受鎖行出現第二次」的判準）。現查＝**同一棵工作樹上跑兩次、比對 `skipped`**：

```bash
# 在 AutoClaude/ 下。第一次刻意關掉 autodetect＝模擬「docker daemon 沒開」
AUTOCLAUDE_NO_PG_AUTODETECT=1 python -m pytest tests/ -q | tail -1
python -m pytest tests/ -q | tail -1                       # 第二次：容器已 healthy
```

```powershell
# 在 AutoClaude\ 下（PowerShell 沒有 VAR=value <指令> 前綴語法，須先設再跑、跑完清掉）
$env:AUTOCLAUDE_NO_PG_AUTODETECT = '1'; python -m pytest tests/ -q | Select-Object -Last 1
Remove-Item Env:\AUTOCLAUDE_NO_PG_AUTODETECT; python -m pytest tests/ -q | Select-Object -Last 1
```

⚠️ **誠實劃界（三點，別把這一節讀成「skip 全解了」）**：
1. `AUTOCLAUDE_NO_PG_AUTODETECT=1` 是**近似**「daemon 沒開」而非等同——它只關掉注入，關不掉別的測試自己對 docker 的偵測；量到的差額是 PG 這一類的**下界**。R83 於 macOS 實測該旗標另會讓 `tests/tools/test_local_ci_gate.py::test_conftest_is_where_the_autodetect_is_wired` **失敗 1 支**（那支正是在守「autodetect 掛在 conftest」），那是旗標的副作用、不是迴歸。
2. 剩下的 skip **不是**這一類：平台專屬（`[WINDOWS-NATIVE-ONLY]`／`[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]`）、選配套件缺席、以及刻意 opt-in 的延遲 SLA（`PG_REAL_ENABLED`，見 `AutoClaude/tests/perf/test_pgvector_recall_perf.py` 的 reason）都在這一行 docker 指令的射程外。逐支清單看 `-rs` 的輸出，別數總數。
3. 容器是 `tmpfs`（`docker-compose.ci.yml` 刻意如此，取證紀律 #7 fresh），**每次重建都要重跑 `alembic upgrade head`**；沒 migrate 時 autodetect 的第 ④ 條剎車會拒絕注入並靜默跳過——那是設計，不是壞掉。


---

## 8. Nightly 排程層（跨平台現況與後續）

AutoClaude 有一套 nightly 取證流程（7 stage：local_ci_gate / mutation / pg-e2e / perf / drift / obs / sdd-fsm-chaos）。**排程自動化現況：Windows 深度版完整可用；macOS 為 R11 新增的薄聚合器（刻意非對等移植，見下）**：

> 🔴 **R59 訂正上一句的框架（DEF-101-517）**：「Windows 深度＝完整／macOS 薄＝子集」這個對比在**三項上方向是相反的**，而本節與 `.ps1` 檔頭此前都沒說。R59 逐項實測（`grep` 確認 `run_local_nightly.ps1` 對三者皆零呼叫）：① **平台 smoke** — mac 的 `[1/4]` 每日自動跑 `macos_smoke_local.sh`，Windows 對等物 `windows_smoke_local.ps1`（現行 PASS=12）曾**只能手動觸發**、nightly 不呼叫它；這是三項中最要緊的，因為該腳本正是 DEF-101-139 為「雲端 CI 帳務停擺」而建的 Windows 側**執行級補償控制**，沒有自動觸發器＝補償控制自己沒有心跳。**⚠️ R60 訂正（DEF-101-529，本句的「沒有心跳」已不再成立）**：現由 `tools/install_windows_nightly.ps1` 註冊的**獨立 schtasks 任務** `AutoClaude_WindowsSmoke` 觸發（設計意圖：排在 nightly 之前——便宜的 tripwire 先跑；R73 實測 smoke 88 秒 vs nightly 5 分 38 秒）。🔴 **R73 訂正（DEF-101-779）**：本段原本寫死「每日 01:00／nightly 02:00」，兩者都與實況不符（實測 smoke 23:30、nightly 22:30，順序還相反）；**時刻一律現查** `Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Get-ScheduledTaskInfo`，本節不再快照具體時刻。心跳查詢走 `Get-ScheduledTaskInfo`，`-Status` 對任務缺席回 exit 1。**刻意保留為真的那半句**：`run_local_nightly.ps1` 對它仍是**零呼叫**——兩者刻意解耦（不動 nightly 的 summary 契約，該契約被 `tools/dev_start.py` 的心跳哨兵以跨檔字面正則解析），smoke 的心跳由它自己的排程任務負責，不寄生在 nightly 上。② **根層 unittest** — mac 的 `[2/4]` 每日跑 `tools/run_root_unittests.py`，Windows nightly 不跑（其 `local-ci-gate` stage 走 `local_ci_gate.py`，範圍是 pytest + LOC + lint-imports，**皆 AutoClaude scope**）。③ **SDD 完整閘門** — mac 的 `[4/4]` 每日跑 `ci-gate.sh` 雙軌全套，Windows nightly 只有 `sdd-fsm-chaos`（chaos 子集）。
>
> 也就是說 R11 為 mac 側補的「七軌去向帳目」一直**只有單向**：mac 交代了自己不跑哪幾軌、由誰承載；Windows 從未交代反向。R59 已在 `run_local_nightly.ps1` 檔頭補上反向帳目。**本輪刻意只補帳目、不補 stage**（理由明說）：新增 stage 需同步改 summary 行／summary JSON／exit-decision 清單／`Format-Rc` 標籤共四處，而 summary 行被 `tools/dev_start.py` 的心跳哨兵以跨檔字面正則解析（DEF-101-263②／R25 跨檔字面鎖），改 summary 契約會連帶動到那組鎖；且本檔是 CI 停擺期間唯一的活體驗證管道，當時無法觀測真正的排程執行結果。列為 backlog，需獨立一輪並以一次真實排程執行收尾。🔴 **R73 補記**：「無法觀測」這個前提已不成立——`Start-ScheduledTask` 可隨選觸發並拿到排程環境下的真實結果（R73 實測 smoke 88 秒、rc=0、log 覆核 `PASS=12 FAIL=0`），「要等到半夜」不再是有效理由。

- **Windows（既有，可用；R19 起一鍵化）**：`AutoClaude/tools/run_local_nightly.ps1` 由 Windows 工作排程器 `schtasks` 每日觸發（任務名 `AutoClaude_Nightly`；**時刻現查** `Get-ScheduledTask -TaskName AutoClaude_Nightly | Get-ScheduledTaskInfo`，本節刻意不快照——R73/DEF-101-779 實證寫死的時刻會過期並誘發破壞性操作）。**R19 前**該任務須手動 `schtasks`/GUI 建立，`AutoClaude/tools/fix_nightly_catchup.ps1` 只能「校正既有任務設定」（`Get-ScheduledTask` 找不到任務即直接拋錯），無法從零建立——與 mac 側 `install_mac_nightly.sh` 的一鍵化體驗不對稱。**R19 新增 `tools/install_windows_nightly.ps1`**（鏡射 `install_mac_nightly.sh` 定位）補上這段：`install`（預設，冪等建立排程＋內建 `fix_nightly_catchup.ps1` 記載的補跑保護設定，新機器不必再另跑一次 fix 腳本）／`-Uninstall`／`-Status`（查詢任務狀態；Windows 工作排程器原生以 `Get-ScheduledTaskInfo` 提供上次執行時間，取代 mac 版讀心跳檔案 mtime 的機制）／`-WhatIf`（PowerShell 內建預覽模式，只印將執行的動作不變更系統）。設定事後校正仍可用 `AutoClaude/tools/fix_nightly_catchup.ps1`。R9 三項強化：①前置新增 local_ci_gate 全套 stage（對齊 `windows-nightly-full` 深度回歸，push 空窗期也有每日全套訊號）；②pg-e2e stage 加跑 PG contract 測試（`tests/contract/test_pg_state_repository_contract.py`，CI 硬閘的本地對等）；③終端 exit code 帶訊號（任一 stage 失敗→exit 1；SKIP/WARN 不計）——schtasks「上次結果」從此可反映 stage 健康，不再恆 0x0。R10 五項強化：④新增 **sdd-fsm-chaos stage**（鏡射 `aisdlc-sdd-fsm-chaos-nightly.yml` 兩步：pytest `-m chaos`＋100 輪 chaos_runner sweep，CI 停擺期間 Rule 9.9.4 的本地補償，實測 <1 分鐘）；⑤pgvector recall pytest rc 以 `[ref]` 捕捉（先前被 collector 覆蓋，單日真紅假綠）；⑥mutmut log 驗證失敗改 rc=1（先前誤設 WARN 級 rc=2，「防假 pass 守門自身觸發」反而綠出場）；⑦Docker 連續 ≥3 次不可用升級為 exit 1（`.docker_skip_streak` 累計；單次 SKIP 仍屬合理）；⑧END 進度 mutation 軌改印 unique-sha 計數（ADR-SD09-011 語意，原始列數會虛報）。全部強化由 `tests/tools/test_run_local_nightly_static.py` 24 個靜態錨點鎖住。
- **macOS（R11 已落地薄聚合器）**：`schtasks` 在 macOS 無對應；等價機制是 `launchd`（推薦）或 `cron`。R11 依 Architect D1 拍板落地 `AutoClaude/tools/run_local_nightly.sh`——**薄聚合器**，只串接四支既有腳本、不重寫任何檢查（四 stage：`tools/macos_smoke_local.sh` 強制系統 bash 3.2 ＋ 根層 `tools/run_root_unittests.py` ＋ AutoClaude `tools/local_ci_gate.sh` ＋ SDD `scripts/ci-gate.sh`；任一 stage 失敗記名續跑、結尾彙總、exit 1——對齊 `.ps1` R9 ③ exit 語意），下方 launchd/cron 範本即可直接啟用。**如實揭露：這不是 `.ps1` 的對等移植，而是刻意的薄聚合**——mac 側只要「平台相容性＋回歸」每日訊號（R11 教訓：smoke 全綠 ≠ unittest 全綠，故兩者都必跑），深度 stage（mutation Docker/pg-e2e/perf/obs）維持 Windows 主開發機承載；七軌其餘兩軌去向——drift＝nightly 取證帳本紀律由 Windows 主開發機承載（drift_log_history 例行 commit 即其產物）、sdd-fsm-chaos＝非平台敏感之純 Python 邏輯回歸（Windows 本地 nightly 每日承接＋CI chaos workflow 覆蓋），mac 薄聚合器均不重複。

> ⚠️ **ops 排程家族其餘三支仍 Windows-only**：`run_local_nightly` 已有 `.sh`（R11 薄聚合器，見上；launchd 排程啟用已於 R13 一鍵化——`bash tools/install_mac_nightly.sh`，見下）；但 ops 排程家族其餘兩支（`g0_gate_check.ps1`、`fix_nightly_catchup.ps1`）仍屬 Windows-only、無 `.sh` 對等，為本節的明示缺口。🔴 **R76 訂正**：本行原列三支，第三支 reschedule_g0_gatecheck.ps1（**刻意不加反引號**——本行的反引號 `.ps1` token 正是 `test_onboarding_parity_interlock.py` 抽取的清單本體，加了就等於把已刪的檔又登記回去）已整支刪除——它唯一能做的事是重排 `AutoClaude_SD09_G0_GateCheck`，而該排程工作於 R71 從本機移除，每條路徑都停在「Task not found」守衛 exit 1；缺口清單只該列「還活著但只有 Windows 有」的東西，孤兒留在清單裡會讓缺口看起來比實際大。
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
| **熱鍵 ESC+F12 預設不再安裝**（R76 起） | `keyboard` 已從 core 相依移到選配 extra（成因：其 metadata 逐字 `Requires-Dist: pyobjc ; sys_platform == "darwin"`，把整個 pyobjc 傘包拖進 macOS 安裝面）。`bootstrap` 裝的是 `[dev,notifications,lint]`，**不含** `hotkey` ⇒ 出廠環境按 ESC+F12 無反應，程式面優雅降級只印 warning | 要用就顯式裝：`uv pip install -e 'AutoClaude[hotkey]'`（zsh 需引號，見 §5）。Ctrl+C 一律可用且同樣寫 checkpoint |
| **macOS 上 ESC+F12 即使裝了也不會生效** | 🔴 R76 訂正：真正擋路的**不是**「輔助使用」權限，是 `keyboard` 的 `_darwinkeyboard.listen()` 首行 `os.geteuid() != 0` 直接拋 `OSError: Error 13 - Must be run as administrator`（R68 macOS 26.5.2 / keyboard 0.13.5 真機取證，見 `AutoClaude/autoclaude/perception/hotkey_handler.py:37-39`）——授權輔助使用也一樣失敗 | 非 root 的 mac 上請直接用 `Ctrl + C`（同樣寫 checkpoint 後退出）。要熱鍵只能 sudo 執行，不建議（平台限制，無對應 DEF 條目） |
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
| 🔴 **證據來源偏斜（元資訊列）——「本輪在哪個平台驗的」一律現查，本列不寫平台常數**（本表其餘各列講「某平台會炸」；本列講的是**證據來源本身的偏斜**，是讀本文件時的元資訊）。🔴 **R69 訂正：本列原文已被 R67／R68 兩個 macOS 真機輪逐字證偽**——原句逐字為「**R60（及近輪）全部實機驗證平台＝Windows 11，macOS 側為靜態分析或推論**｜量測／驗證環境逐字：Windows 11 Pro 26200、Windows PowerShell 5.1.26100.8875、**pwsh 7 本機不存在**、Git Bash 5.2.37、docker 29.5.3、根 `.venv`=3.11.9／`AutoClaude/.venv`=3.12.11」，逐字保全於此當史料，**但它今日為假**：R67 是首個 macOS 真機輪，R68／R69 續在 macOS 真機上執行。訂正方式**不是換一個會過期的平台斷言**（照 `ADR-XPLAT-002` §6 邊界 1：平台覆蓋是**輪次屬性**、不是治理文件的常數；`CrossPlatform_Scan_Dimensions.md` 對同型句子已用同一手法處置過），而是指向 live 來源 | 🔴 **R70 訂正本欄自己（DEF-101-756）——上一版逐字寫「`snapshot-fingerprints-win32` 錨整欄 `unrecorded` ⇒ 今日缺的是 Windows 真機量測」，那句推論是假的，而且它就是本 repo 至今唯一一次「文件缺陷直接造成決策錯誤」的成因**：主控據它向使用者建議下一輪去 Windows，並宣稱「Windows 側從未有真機輪」，被使用者當場以開發史駁回。**`unrecorded` 講的是「量測環境沒被記下來」，不是「沒量過」**——同一欄裝著的 `3767 passed / 208 skipped` 正是 Windows 實機量得的，歸因欄那句「`[WINDOWS-NATIVE-ONLY]` 3 支由 skip 轉 pass、反向新增 2 支 `[WinError 1314]` skip」更是只有在真 Windows 上跑才寫得出來。**史實**：R20 是首個 Windows 真機輪（逐字「本輪首次在真實 Windows 11 機器（非 mac）上執行本 repo」），R20~R66 為 Windows 真機期；R9~R19 與 R67~R70 為 macOS 真機期；**兩個平台都有真機輪，只是輪次不同**。**且 Windows 真機至今每天仍在產生證據**：Task Scheduler 的 `AutoClaude_Nightly` 每日 02:00 跑完整回歸（見 §8），只是它的 log 是 untracked＋14 天輪替，從別台機器結構上看不到。現查指令：`python tools/sync_onboarding_baselines.py --check-snapshot`（自 R70 起逐欄印出**三態**基線狀態＋該平台 nightly 心跳現況；其 rc 反映的是「指紋有無漂移」，**不是**「有沒有真機量測過」，兩者別混）。逐輪平台覆蓋的權威來源是 [ADR-XPLAT-002](docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md) §6 邊界 1 的**逐輪覆蓋表**，不是本欄、也不是那支工具。另一項與平台無關、且**尚未關閉**的殘留：`.github/workflows/macos-compat-ci.yml`／`windows-compat-ci.yml` 曾長期因 GitHub 帳務在數秒內失敗而 **job 從未真正執行**（🔴 R60 round 3 訂正過「永遠不會被觸發」的說法：實況是**全部被觸發、全部 completed/failure**，`QA-R60R3-04`／`DEF-101-597`），雲端那一半的真機覆蓋是否恢復，一律以唯讀 `gh run list` 現查為準 | 讀任何「本輪已驗證」宣稱時**仍**請先問「在哪個平台驗的」，但**答案不再有預設值**——去看該輪帳本列「發現情境」欄與 §7 表② 對應錨的 provenance，別沿用本列原文那句「本 repo 的預設答案是 Windows」。**不要**用「兩平台程式碼相同」推論「兩平台皆已驗證」（DEF-101-511／512 立的原則：讓結論自己說出降級）；🔴 **R70 訂正這句的射程（DEF-101-756）**：本句原意是「**本輪**要在 Windows 上取得新證據只有這條路」，但它沒寫「本輪」，讀起來像「Windows 從來沒被驗過」——那是假的（見左欄史實）。正確表述：**要讓 §7 表② Windows 欄的 provenance 從 `pre-provenance-mechanism` 升級為 `self-recorded`，只有一條路＝在一台真 Windows 11 機器上跑 `--write --with-slow`**（或讓 `windows-compat-ci.yml` 的 nightly-full 真的跑完）。那是**後設資料缺口**，不是覆蓋缺口；Windows 側的既有量測**仍然有效**，且本機 nightly 每日仍在該平台累積新證據 |
| **凍結版 v0.01~v0.29 `tools/fsm_runtime/rule_loader._write_rule()` 無 `newline=""`**（LATEST v0.30 已於 R60 修復；29 個凍結版依 Copy-on-Evolve 不回補，其中 21 版有 `record_state_fires` 呼叫路徑） | Windows 上跑舊版 FSM 會把 tracked 的 `governance/rules/*.yaml`（v0.01 實查 38 支）整檔由 LF 轉 CRLF——與 `.gitattributes` 宣告的 `*.yaml text eol=lf` 相反，`git diff` 印警告、工作樹「假髒」，且會讓下一位以為有人改了規則檔 | 用 **v0.30 同檔**（已帶 `newline=""`）。凍結版若非得跑，事後以 bytes 層正規化回 LF（`git diff` 應為空＝語意零變更）。**重新評估觸發條件**：若未來有文件或流程引導使用者手動 `cd` 進舊版目錄執行 FSM，屆時重新評估是否回補。觸發條件三款詳見缺陷帳本 **DEF-101-534**（fixed@R60；本列＝該筆依 ADR-XPLAT-001 §4.3 C1 必須存在的 §9 對應列，故該筆**不得歸檔**——一歸檔，本指針與 C1 機械鎖的掃描面會同時失效） |

> 對應缺陷帳本：前兩條＝[AutoSDD_Defect_Log.md](docs/06_quality/AutoSDD_Defect_Log.md) DEF-101-003／DEF-101-004（wontfix＋凍結版紀律）；第 4~8 條＝DEF-101-019／DEF-101-020（wontfix＋凍結版紀律）與 DEF-101-021／DEF-101-022／DEF-101-025（closed-by-decision@R80：三筆 known-gap 已如實揭露且各有防線，屬**決定接受**而非待辦；本節的揭露內容不變，逐筆實查見 `docs/06_quality/CrossPlatform_R80_Scan_Findings.md` §C）；倒數第五條（凍結版 settings 兩面向）＝DEF-101-040（wontfix＋凍結版紀律）；倒數第三條（`install_post_commit.ps1` ASCII 編碼）＝DEF-101-056（wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正）；倒數第二條（`hypothesis` 版本鎖定）＝DEF-101-058（**fixed@Mac/Windows 四方複審 2026-07-14**；R3 複審發現本文件先前敘述與此已修復實況不同步，已訂正）。**R44 跨平台輪新增末條**：末條（v0.01～v0.29 凍結版 `run_self_evolution.{sh,ps1}` 對 python 呼叫零可用性判斷）＝DEF-101-359（wontfix＋凍結版紀律；LATEST v0.30 對應版本已 fixed@R44，見 DEF-101-361）。另有 **DEF-101-005**（`verify_traceability.sh` 的 `set -e`＋grep 零命中提前靜默退出，所有 bash 版本皆然；**fixed@R16**：同根因併入 DEF-101-218 一併修復，9 處賦值敘述式補 `|| true`；本文件先前敘述與此已修復實況不同步，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正）、**DEF-101-018**（ruff 存量分批清理 closed-by-decision＝移入結構性長債軌，解鎖條件見 docs/06_quality/AutoSDD_Structural_Debt_Log.md；其「未鎖版跨機器漂移」根因 DEF-101-006 已 fixed@四方複審第三輪；**R23 複審重新實測 baseline 為 1,147 筆**〔`.venv` ruff 0.15.21，原「1,339 筆」為舊測值，見 DEF-101-262〕）、**DEF-101-057**（`install_post_commit.{sh,ps1}` worktree 路徑解析 bug 在 v0.01~v0.29 之殘留，wontfix＋凍結版紀律，記事存證；本文件先前誤記為 open，經 `tools/check_defect_log_crossref.py` 機械揪出已訂正；不佔本表列，因與上方 DEF-101-056 同源議題已合併敘述於缺陷帳本本身）、**DEF-101-358**（v0.01～v0.29 凍結版 `_sanitize_component()` 僅剝除 `/`／`\` 的較弱版本殘留；**fixed@R45**：30 個版本〔v0.01～v0.29 凍結基線＋LATEST v0.30〕已全數改為委派共用模組 `AISDLC_SDD/scripts/component_sanitizer.py`，含 Windows 保留裝置名／禁用字元／長度上限完整強化，不再有較弱版本殘留；本文件先前敘述與此已修復實況不同步，本輪複審已訂正、移除上表對應列）與 **DEF-101-060**（`pyproject.toml` 另有 ~18 條相依未鎖版本上限，open，記事存證，見上表 hypothesis 列）非平台缺口、不列本表。

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
