# 跨平台啟動提示詞與平台切換 SOP（macOS / Windows）

本檔兩用：
1. **啟動**——新開 session 的第一則訊息整段貼上〈🚀 啟動提示詞〉（兩平台共用一份，Claude 依所在平台選分支；機制本體＝[tools/dev_start.py](tools/dev_start.py)）。
2. **切換**——換機器時照〈🔁 平台切換 SOP〉：A 段做在要離開的機器（關機後補不回來），B 段做在剛到的機器（表② 回填只能在目標平台做）。

> **今天要花多久，第 1、2 步跑完就確定了**——別把驗證協定誤讀成「切換壞了」：
>
> | 情境 | 條件 | 還要做什麼 |
> |---|---|---|
> | **A** | merge 沒拉到東西 ＋ nightly 無 FAIL ＋ 第 7 步 `--check-snapshot` 綠 | 無 |
> | **B** | merge 拉進的 commit 動到指紋監測面，nightly 無 FAIL | 表② 回填（B 段第 3 步，分鐘級） |
> | **C** | nightly 有 FAIL | 在**新 HEAD** 重跑失敗的 stage（第 3 步三態判定）；指紋若也漂移，再加 B |
>
> 監測面只有**四棵測試樹＋其 rootdir `conftest.py`**（SSOT＝`tools/sync_onboarding_baselines.py` 的 `_FINGERPRINT_TREES`）；要不要回填一律以 `--check-snapshot` 為準，不是憑印象。

## 🚀 啟動提示詞（兩平台共用）

平台差異只有下表，提示詞內以「mac／win」標示，`<python>` 依表代換。全 repo 只有**根層一顆 `.venv`**（兩子專案的內容都裝在它裡面），任何工具、hook、排程都指向它：

| | macOS | Windows |
|---|---|---|
| `<python>` | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| dev_start | `source tools/dev_start.sh`（bash/zsh，勿用 POSIX sh） | `. .\tools\dev_start.ps1`（dot-source；成敗看摘要或 `$LASTEXITCODE`，**不可看 `$?`**）。非 PowerShell 載具改 `powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1`（**不可**用 `-Command` 包，會吞 exit code 假綠） |
| Claude Code hook 載具 | `.venv/bin/python`（exec form；2026-09-15 起，此前是 PATH 上的 `python3`） | `.venv\Scripts\pythonw.exe`（exec form，零彈窗） |
| nightly／額度哨兵排程現查 | `bash tools/install_mac_nightly.sh --status`；`launchctl list \| grep -E 'com.autoclaude.nightly\|AutoSDD_Sentinel_'`（憑證是有列出；launchd 不報下次執行時刻） | `Get-ScheduledTask \| Where-Object TaskName -like 'AutoClaude*' \| Get-ScheduledTaskInfo`（憑證＝`NextRunTime` 值） |

兩平台 hook 載具都是根層 .venv 裡的直譯器 ⇒ **首次 clone 到 dev_start 建好 .venv 之前，hook 全部 fail-open**（Claude Code 只記一行 ERROR、工具照跑）；載具壞掉時六支守衛靜默消失的表徵與「正常」一模一樣，dev_start **不查**這件事，所以第 2 步 [6/7] 要做正面現查（另有 `<python> tools/check_hooks_liveness.py` 會出聲）。

```
我現在要在這台機器上開發這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依你所在的平台（mac／win）依序完成：

1. 一律先 GitHub 同步（不要先判斷 dev_start 檔存不存在才決定）。首次 clone 時本步跑在 hook 尚未生效的視窗：兩平台 hook 載具都是根層 .venv 裡的直譯器，`block_destructive_git` 等六支守衛要到第 2 步 dev_start 建好 .venv 後才會活，所以本步的「不要 rebase／reset --hard／stash」全靠你遵守，不是機械阻斷。a. git branch --show-current 必須是 main，不是就列分支名與 git status 給我等我決定；不要自行切換，也不要在非 main 跑 merge（--ff-only 會靜默改寫分支指標）。
   b. 確認沒有 nightly 在跑（避免撞同一分鐘造成假紅寫進心跳檔）：`<python> tools/dev_start.py --check-nightly`（首次 clone 還沒有 .venv 時跳過本項、視為 idle）。idle（rc=0）才往下；NIGHTLY-RUNNING（rc=1）等它跑完、期間不跑任何測試；UNDETERMINED（rc=0，判不出來≠沒在跑）自己查行程：mac `ps -eo pid,etime,command | grep -E 'run_local_nightly|-m pytest' | grep -v grep`；win `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_local_nightly|pytest' } | Select-Object ProcessId,CommandLine`。
   c. git fetch origin（失敗＝離線：明說「本次離線、跳過同步」，第 2 步 dev_start 加 `--no-sync`）；d. git merge --ff-only origin/main（失敗／領先／分叉／未提交變更：列 git status 與 git log main..origin/main 給我等我決定，不要 rebase、reset --hard、stash）；e. 有拉到東西時查是否動到指紋監測面（有＝預期第 7 步要回填）：`git diff --name-only ORIG_HEAD HEAD -- AutoClaude/tests AISDLC_SDD/scripts/tests 'AISDLC_SDD/*/tools/fsm_runtime/tests'`。

2. 在 repo 根執行 dev_start（指令見上表；timeout 設 10 分鐘上限，bootstrap 合法耗時數分鐘；被中斷就重跑同一條，疑似半殘 .venv 可加 `--force-bootstrap`）。七步（標題取自終端機實印，括號為補充說明）：[1/7] 環境偵測（Developing vs Now）／[2/7] GitHub 同步（只提醒不自動 stash/rebase/push）／[3/7] 平台切換（跨平台無效快取清理）／[4/7] venv／依賴整備／[5/7] git hooks 檢核（根層 dispatcher）／[6/7] 平台專屬健檢／[7/7] 狀態寫回。
   [4/7] 全樹只准有根層一顆 .venv：印「🔴 偵測到雜散 venv／殘留」即 ❌，照它印出的刪除指令手動刪掉後重跑（刻意不自動刪；`--force-bootstrap` 不會解這一種）。
   [5/7]（win）印「偵測不到 Git Bash」不是雜訊：三支 hooks dispatcher 都是 bash，commit/push 會跑不起來，先把 `git --version` 與 `where.exe bash` 列給我。
   [6/7] 要讀：nightly 心跳三態（「未偵測」＝advisory）；心跳「新鮮」≠上一輪成功，另有一行「⚠️ nightly 最近一輪有 FAIL=N」一定要讀；已自動跑 `--check-snapshot`（advisory，但 pre-push 是阻斷項）；GitHub CI 的 ⚠️ 當場 `gh run list --limit 10` 現查再判讀。再做 hook 載具正面現查（兩平台都要；「沒報錯」「不閃窗」都不算過）：載具在不在——mac `test -x "$(git rev-parse --show-toplevel)/.venv/bin/python" && echo carrier-ok`／win `Test-Path (Join-Path (git rev-parse --show-toplevel) '.venv\Scripts\pythonw.exe')` 須 True；然後 `claude -p --model haiku --debug hooks --debug-file h.log "ok"` 後 mac `grep 'Hook SessionStart.*success' h.log`／win `Select-String -Path h.log -Pattern 'Hook SessionStart.*success'` 要有命中，查完刪 h.log。win 另一件：`core.longpaths` 只設 `--local`（clone 當下自帶 `git clone -c core.longpaths=true`）。

3. 讀「dev_start 摘要」：❌ 先排除，常見來源：半殘 .venv（`--force-bootstrap`）、雜散 venv（照印出的指令手動刪，見 [4/7]）、「取不到互斥鎖」（先確認沒有另一個 dev_start 遺留行程再回報，不要手動刪 .dev_start.lock）；⚠️ 工作樹不乾淨／分叉／領先未 push：列給我決定，不要自動 commit/stash/push；⚠️ nightly 有 FAIL 是三態判定：① 失敗 stage 時間與 `git reflog --date=iso` 最近一次 merge 重疊＝可疑假紅，② 不論是否重疊都在當前 HEAD 重跑那些 stage（nightly 跑的是 merge 前的 code），③ 舊紅可能已被 merge 修掉、同時換上新紅，兩邊都要看，假紅要跟我說、別默默當迴歸修——重跑指令：mac 在 `AutoClaude/tools/run_local_nightly.sh` 找 `run_stage`；win 在 `AutoClaude/tools/run_local_nightly.ps1` 找 `Invoke-Stage`（函式名不同，都不支援單跑一個 stage）。已知非迴歸形態：「rc=1 但 pytest 0 failed」＝`check_skip_census()` 對未登記剖面判紅（缺陷帳本 DEF-200-183／291／303）；mac `root_unittests` 紅＝launchd PATH 缺 `/opt/homebrew/bin` 找不到 pwsh，互動 shell 重跑即綠（口述經驗，無登記票號）。沒印「工作樹不乾淨」≠ 乾淨（只在要 pull 時才查）：自己跑 `git status --porcelain --untracked-files=all`。

4. shell 狀態不跨工具呼叫存活 ⇒ 之後所有 Python 指令一律用完整路徑 <python>，不要誤用系統 Python；5. 先讀根 CLAUDE.md，進子專案前讀它自己的 CLAUDE.md（override 級規範）；6. 繁體中文回覆。
7. ONBOARDING §7 表② 本平台欄回填——每次啟動都跑（靠機械判準，不靠記憶）：`<python> tools/sync_onboarding_baselines.py --check-snapshot`。presumed stale 或 baseline-origin 非 self-recorded ⇒ 要回填（觸發源常是第 1 步 merge 拉進對面機器的 commit）；回填照 B 段第 3 步，排在 commit/push 之前，做完把工具輸出貼給我。

完成後簡短回報：首次執行？跨平台切換？同步結果？.venv 重建？hooks 正常？有無待我處理的警告？然後等我下任務，不要自己開工。
```

## 🔁 平台切換 SOP

兩種拓撲皆適用（ONBOARDING §2.1）：共用工作目錄、雙機各自 clone。A、B 兩段都要做。

### A. 離開前（做在要離開的機器；關機後補不回來）
```bash
git fetch origin
git status --porcelain --untracked-files=all           # 期望：無輸出。--untracked-files=all 不可省：未 add 的新檔對 git ls-files 型掃描面隱形，會讓全套閘門假綠
git rev-list --left-right --count origin/main...main   # 期望：0<TAB>0（左＝落後、右＝領先未 push）
git stash list                                         # 期望：無輸出
git worktree list                                      # 期望：只有主 checkout 一行
gh run list --limit 10 --json workflowName,conclusion,event,createdAt,headSha   # 雲端 CI 唯讀現查
```
雲端 CI 判讀：只有 `root-infra-ci.yml` 是全變更觸發，其餘有 `paths` 白名單、沒命中就不會出現在清單 ⇒ 先列「這次 push 應觸發哪幾支」再對帳，**缺席＝未驗證，不是通過**。還沒回來的 run 把 `headSha` 寫進交接。本節不記任何平台 CI 的紅綠——那是輪次屬性、不是常數。

### B. 到達後（做在剛到的機器）

順序不可調換：**閘門先、回填後**——回填寫的是根層 `ONBOARDING.md`，而 pre-push 慢層只在 push 含根層檔時才跑；先回填、後才發現紅，成果會被自己的紅鎖在本機。

1. **跑一次啟動提示詞**（全新 Windows 機器先 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`，預設 Restricted 擋掉所有 .ps1）。
2. **跑全套閘門確立新平台基線，紅燈在這步清完**（指令見 ONBOARDING §7 與根 CLAUDE.md；本檔不重抄數字）——剛過來的第一輪最容易冒出跨平台缺口，是本步目的、不是意外。
3. 🔴 **回填本平台 ONBOARDING §7 表②**——整份 SOP 唯一只能在目標平台做的事（跨平台代填＝假 provenance，工具 rc=2 拒絕）。**首選一條龍載具** `tools/lib/clean_venv_carrier.py`（建樹外乾淨 venv → 裝依賴 → 探針 psycopg2／sqlalchemy 必 ABSENT → `--write --with-slow` 回填 → finally 必刪；DEF-200-306）：
   ```bash
   "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/lib/clean_venv_carrier.py
   ```
   ```powershell
   & "$(git rev-parse --show-toplevel)\.venv\Scripts\python.exe" tools/lib/clean_venv_carrier.py
   ```
   - 前提：**docker daemon 要開**（`docker info` 印得出版本，provenance 記 `docker=up／down`）；**不准 `--allow-pg-extras`**（會把 provenance 悄悄改成 `pgextras=present`，沒有機械物會察覺）。乾淨 venv ≠ 本機 `.venv`（本機幾乎必裝過 pg extras，工具 rc=2 拒用），所以一定要另建、且建在 **repo 樹外**（樹內會污染全樹掃描型測試）。
   - 手動備援（只在工具本身壞掉時逐步照抄；出廠定義＝`tools/bootstrap_core.py`）。目錄名須含 `cleanvenv` 且放暫存目錄，dev_start 的殘留掃描才認得：
     ```bash
     python3.11 -m venv "${TMPDIR:-/tmp}/cleanvenv"     # 放 $TMPDIR（mac 預設非 /tmp）
     "${TMPDIR:-/tmp}/cleanvenv/bin/python" -m pip install -e 'AutoClaude/.[dev,notifications,lint]' -r AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt
     "${TMPDIR:-/tmp}/cleanvenv/bin/python" -c "import importlib.util as u; [print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') for m in ('psycopg2','sqlalchemy')]"   # 兩行都要 ABSENT；印不出來＝探針壞了、不是乾淨
     "${TMPDIR:-/tmp}/cleanvenv/bin/python" tools/sync_onboarding_baselines.py --write --with-slow
     ```
     ```powershell
     py -3.11 -m venv $env:TEMP\cleanvenv
     & "$env:TEMP\cleanvenv\Scripts\python.exe" -m pip install -e 'AutoClaude/.[dev,notifications,lint]' -r AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt
     & "$env:TEMP\cleanvenv\Scripts\python.exe" -c "import importlib.util as u; [print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') for m in ('psycopg2','sqlalchemy')]"   # 兩行都要 ABSENT
     & "$env:TEMP\cleanvenv\Scripts\python.exe" tools/sync_onboarding_baselines.py --write --with-slow
     ```
     extras 一律單引號（zsh 才不會把 `.[...]` 當 glob）。
   - **回填排在 commit/push 之前，回填後不再改那四棵樹**（改了就再回填一次）；驗收＝`--check-snapshot` 本平台欄綠。**收尾（不要漏）**：手動備援建的樹外 venv 立刻刪掉（一條龍載具已自刪；殘留會被下次 dev_start 擋下），Docker 若只為回填才開就關掉（mac `osascript -e 'quit app "Docker"'`；Windows 系統匣 Quit）。

### C. 兩平台語法雷區（實際踩過；完整對照 ONBOARDING §5／§6／§7）

| 症狀 | 根因 → 正解 |
|---|---|
| mac 裝 extras 報 `zsh: no matches found` | zsh 把未引號的 `.[...]` 當 glob，指令執行前就中止 → extras 一律單引號 `'.[dev,notifications]'` |
| win 跑 `PYTHONUTF8=1 lint-imports` 報 `not recognized` | PowerShell 沒有 `VAR=value 指令` 前綴語法 → `$env:PYTHONUTF8=1; lint-imports` |
| win 呼叫 bash 腳本得到 UTF-16 亂碼「WSL has no installed distributions」 | 裸名 `bash` 由 CreateProcess 先命中 System32 的 WSL 佔位 → 一律解析成絕對路徑（`tools/lib/Find-GitBash.ps1`、`tools/integration_gate_core.py::find_git_bash()`），禁止把裸 `"bash"` 交給 subprocess |
| mac 讀 `${PIPESTATUS[0]}` 得空字串 | Claude Code 的 Bash 工具在 mac 是 zsh：陣列叫 `pipestatus`、下標從 1 起 → 別用管線判 rc：`cmd > out.log 2>&1; rc=$?` |
| mac 迴圈跑「指令 + 參數」字串全報 rc=2 | zsh 不對未引號變數分詞，整串當單一檔名 → 需要分詞就包 `bash -c '…'` 或用陣列 |
| push 被 pre-push 擋、印「找不到 ruff」 | root-infra 快層跑 `ruff check tools/`，ruff 缺席刻意 fail-loud → 先啟用根層 .venv 並裝好開發相依 |
| `git push` 非零但看不到 `remote:` 行、尾段卻像全綠 | 沒送到伺服器，是 pre-push 自己紅；尾段樂觀字樣屬某一段 leg → 只看 `main -> main` 那行；真因搜 `[pre-push` 的 ❌ 行，在中段 |
| push 被擋，FAIL 全在 `test_doc_loc_baseline_freshness_r60`、訊息含「`nightly-checked-at` … 已是 N 天前」 | ONBOARDING §7 表③ 錨的排程軌查核有 14 天過期帶，是計時炸彈、與你的改動無關（久未開發後第一次 push 最常撞到） → 照 ONBOARDING §7 回填 SOP 第 6 步：`gh run list --event schedule` ＋ `gh run view <id> --json jobs` 現查，更新表③-b 兩列與錨的 `nightly-run`／`nightly-checked-at` |

### D. 跑全套測試前：拉起 CI 對等 PG 容器（兩平台共通）

AutoClaude 有一整類 PG 相依測試只因 docker 沒開而 skip；一行 compose 即可，conftest 的 PG autodetect 會自己注入 DSN（影響幾支是量測值，本檔不寫；完整說明見 ONBOARDING §7.1）。🔴 PG 在場時 pytest 必加 `--dist loadgroup`：預設 `-n auto --dist worksteal` 會讓多個 xdist worker 同碰一顆 PG，conftest 偵測到會直接拒跑並教你怎麼改（DEF-200-274 X1）。

```bash
open -a Docker && docker info --format '{{.ServerVersion}}'       # 印得出版本才算 daemon 活著
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d    # 容器是 tmpfs，每次新建都要 migrate
AUTOCLAUDE_DB_DSN='postgresql://autoclaude:autoclaude@localhost:5432/autoclaude' alembic upgrade head   # 行內前綴而非 export，才驗得到 autodetect
python -m pytest tests/ -q --dist loadgroup                        # 尾端要出現 `[PG autodetect] 已注入 …`
```
```powershell
docker info --format '{{.ServerVersion}}'
Push-Location (Join-Path (git rev-parse --show-toplevel) 'AutoClaude')   # 勿用 $env:CLAUDE_PROJECT_DIR，開發者終端機裡它是空的
docker compose -f docker-compose.ci.yml up -d
$env:AUTOCLAUDE_DB_DSN = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
alembic upgrade head
Remove-Item Env:\AUTOCLAUDE_DB_DSN     # 不清掉會擋住下一行的 autodetect
python -m pytest tests/ -q --dist loadgroup
Pop-Location
```
⚠️ 別和 B 段第 3 步搞混：那步要的是**出廠環境乾淨 venv**（PG driver 缺席）；本節是日常開發把 skip 降到最低。mac 首次建 `run_act` runner 映像會撞 `DeadlineExceeded`：先 pull 基底再 build，見 ONBOARDING §1 的 Docker 列。
