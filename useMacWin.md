# 跨平台啟動提示詞與平台切換 SOP（macOS / Windows）

本檔兩用：
1. **啟動**——新開 session 的第一則訊息整段貼上〈🚀 啟動提示詞〉（兩平台共用，Claude 依所在平台選分支；機制本體＝[tools/dev_start.py](tools/dev_start.py)）。
2. **切換**——換機器時照〈🔁 平台切換 SOP〉：A 段做在要離開的機器（關機後補不回來），B 段做在剛到的機器（表② 回填只能在目標平台做）。

> **今天要花多久，提示詞第 1、2 步跑完就確定了**（別把驗證協定誤讀成「切換壞了」）；要不要回填一律以 `--check-snapshot` 為準，不憑印象：
>
> | 情境 | 條件 | 還要做什麼 |
> |---|---|---|
> | **A** | merge 沒拉到東西 ＋ nightly 無 FAIL ＋ 第 7 步 `--check-snapshot` 綠 | 無 |
> | **B** | merge 拉進的 commit 動到指紋監測面（四棵測試樹＋其 rootdir `conftest.py`；SSOT＝`tools/sync_onboarding_baselines.py` 的 `_FINGERPRINT_TREES`），nightly 無 FAIL | 表② 回填（B 段第 3 步，分鐘級） |
> | **C** | nightly 有 FAIL | 在**新 HEAD** 重跑失敗的 stage（第 3 步三態判定）；指紋若也漂移，再加 B |

## 🚀 啟動提示詞（兩平台共用）

平台差異只有下表；提示詞內以「mac／win」標示，`<python>` 依表代換。全 repo 只有**根層一顆 `.venv`**，hook 載具、排程、git hooks、ci-gate 全指向它。

| | macOS | Windows |
|---|---|---|
| `<python>` | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| dev_start | `source tools/dev_start.sh`（bash/zsh，勿用 POSIX sh） | `. .\tools\dev_start.ps1`（dot-source；成敗看摘要或 `$LASTEXITCODE`，**不可看 `$?`**）；非 PowerShell 載具改 `powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1`（**不可**用 `-Command` 包，會吞 exit code） |
| Claude Code hook 載具 | `.venv/bin/python`（`.venv/Scripts/pythonw.exe` 是指向它的符號連結，兩平台共用同一份 `settings.json` 字面） | `.venv\Scripts\pythonw.exe`（exec form，零彈窗） |
| 排程現查（nightly／額度哨兵／喚醒 job） | `bash tools/install_mac_nightly.sh --status`；`launchctl list \| grep -E 'com.autoclaude.nightly\|AutoSDD_'`（憑證＝有列出；launchd 不報下次執行時刻） | `Get-ScheduledTask \| Where-Object TaskName -like 'AutoClaude*' \| Get-ScheduledTaskInfo`（憑證＝`NextRunTime` 值） |

🔴 hook 載具＝根層 .venv 的直譯器 ⇒ **首次 clone 到 dev_start 建好 .venv 之前，hook 全部 fail-open**（只記一行 ERROR、工具照跑）；載具壞掉時守衛靜默消失、表徵與正常相同 ⇒ 第 2 步 [6/7] 必做正面現查（`<python> tools/check_hooks_liveness.py` 也會出聲）。

```
我現在要在這台機器上開發這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依你所在的平台（mac／win）依序完成：

0. `.venv` 已在（非首次 clone）時，**第一個工具呼叫**先現查本 session 的真實水位與額度（零 token、唯讀）：兩平台同字面 `python tools/session_resume_planner.py --check` 與 `python tools/session_resume_planner.py --pace`，照字面執行、不改成絕對路徑或 `& '…'` 形式（權限白名單認的是這個字面）；需 Python ≥ 3.11，所以 claude 一律在 dev_start 已啟用 .venv 的終端開，先 `python --version` 看到 3.11+。兩行結論帶著走，之後每次派工前再查一次 `--pace`。首次 clone 沒有 .venv 時跳過，dev_start 建好後補查。

1. 第 0 步之後一律先 GitHub 同步（首次 clone 時 hook 尚未生效，「不要 rebase／reset --hard／stash」全靠你遵守）：
   a. `git branch --show-current` 必須是 main；不是就列分支名與 `git status` 給我等我決定，不要自行切換、不要在非 main 跑 merge。
   b. 確認沒有 nightly 在跑：`<python> tools/dev_start.py --check-nightly`（首次 clone 跳過、視為 idle）。idle（rc=0）才往下；NIGHTLY-RUNNING（rc=1）等它跑完、期間不跑任何測試；UNDETERMINED（判不出來≠沒在跑）自己查行程：mac `ps -eo pid,etime,command | grep -E 'run_local_nightly|-m pytest' | grep -v grep`；win `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_local_nightly|pytest' } | Select-Object ProcessId,CommandLine`。
   c. `git fetch origin`（失敗＝離線：明說「本次離線、跳過同步」，第 2 步 dev_start 加 `--no-sync`）。
   d. `git merge --ff-only origin/main`（失敗／領先／分叉／未提交變更：列 `git status` 與 `git log main..origin/main` 給我等我決定，不要 rebase、reset --hard、stash）。merge 成功會自動觸發 `tools/git-hooks/post-merge` 同步額度參數檔，讀它印的末行：`env.shared 同步：0 個問題` 或 `已自動修復，備份＝…`＝完成；`🔴 … 需要人處理`＝列給我；沒看到這些行（例如走了 rebase）就手動跑 `<python> tools/lib/quota_policy.py --env-doctor`。doctor 表內若出現「〔process-env〕」＝這台的 shell 或使用者層環境變數有 AUTOSDD_* 蓋過所有檔案層，先弄清楚是誰設的、列給我。
   e. 有拉到東西時查是否動到指紋監測面（有＝第 7 步要回填）：`git diff --name-only ORIG_HEAD HEAD -- AutoClaude/tests AISDLC_SDD/scripts/tests 'AISDLC_SDD/*/tools/fsm_runtime/tests'`。

2. 在 repo 根執行 dev_start（指令見上表；工具 timeout 設 10 分鐘上限，bootstrap 合法耗時數分鐘；被中斷就重跑同一條，疑似半殘 .venv 加 `--force-bootstrap`）。七步 [1/7] 環境偵測～[7/7] 狀態寫回，要特別讀：
   [4/7] 印「🔴 偵測到雜散 venv／殘留」即 ❌：照它印出的刪除指令手動刪掉後重跑（刻意不自動刪；`--force-bootstrap` 不解這一種）。
   [5/7]（win）印「偵測不到 Git Bash」不是雜訊：hooks dispatcher 都是 bash，commit/push 會跑不起來，先把 `git --version` 與 `where.exe bash` 列給我。
   [6/7] nightly 心跳三態（「未偵測」＝advisory）；心跳「新鮮」≠上一輪成功，「⚠️ nightly 最近一輪有 FAIL=N」一定要讀；已自動跑 `--check-snapshot`（advisory，但 pre-push 是阻斷項）；GitHub CI 的 ⚠️ 當場 `gh run list --limit 10` 現查。再做 hook 載具正面現查（「沒報錯」「不閃窗」都不算過）：mac `test -x "$(git rev-parse --show-toplevel)/.venv/bin/python" && echo carrier-ok` 與 `readlink "$(git rev-parse --show-toplevel)/.venv/Scripts/pythonw.exe"` 應印 `../bin/python`；win `Test-Path (Join-Path (git rev-parse --show-toplevel) '.venv\Scripts\pythonw.exe')` 須 True；然後 `claude -p --model haiku --debug hooks --debug-file h.log "ok"`，mac `grep 'Hook SessionStart.*success' h.log`／win `Select-String -Path h.log -Pattern 'Hook SessionStart.*success'` 要有命中，查完刪 h.log。win 另：`core.longpaths` 只設 `--local`（clone 當下自帶 `git clone -c core.longpaths=true`）。

3. 讀「dev_start 摘要」：❌ 先排除——半殘 .venv（`--force-bootstrap`）、雜散 venv（照 [4/7]）、「取不到互斥鎖」（先確認沒有另一個 dev_start 遺留行程再回報，不要手動刪 .dev_start.lock）；⚠️ 工作樹不乾淨／分叉／領先未 push：列給我決定，不要自動 commit/stash/push；⚠️ nightly 有 FAIL 三態判定：① 失敗 stage 時間與 `git reflog --date=iso` 最近一次 merge 重疊＝可疑假紅；② 不論是否重疊都在當前 HEAD 重跑那些 stage（nightly 跑的是 merge 前的 code）；③ 舊紅可能已被 merge 修掉、同時換上新紅，兩邊都要看，假紅要跟我說、別默默當迴歸修。重跑：mac 在 `AutoClaude/tools/run_local_nightly.sh` 找 `run_stage`；win 在 `AutoClaude/tools/run_local_nightly.ps1` 找 `Invoke-Stage`（都不支援單跑一個 stage）。已知非迴歸形態：「rc=1 但 pytest 0 failed」＝`check_skip_census()` 對未登記剖面判紅（DEF-200-183／291／303）；mac `root_unittests` 紅＝launchd PATH 缺 `/opt/homebrew/bin` 找不到 pwsh，互動 shell 重跑即綠。沒印「工作樹不乾淨」≠ 乾淨：自己跑 `git status --porcelain --untracked-files=all`。

4. shell 狀態不跨工具呼叫存活 ⇒ 之後所有 Python 指令一律用完整路徑 <python>；5. 先讀根 CLAUDE.md，進子專案前讀它自己的 CLAUDE.md（override 級規範）；6. 繁體中文回覆。
7. ONBOARDING §7 表② 本平台欄——每次啟動都跑 `<python> tools/sync_onboarding_baselines.py --check-snapshot`：presumed stale 或 baseline-origin 非 self-recorded ⇒ 要回填（照 B 段第 3 步，排在 commit/push 之前，做完把工具輸出貼給我）。
8. 任何指令被 auto 分類器擋下（文字開頭 `Permission for this action was denied by the Claude Code auto mode classifier`）：不要繞、不要改派子代理，把那條指令原樣貼給我用 `!` 親手跑（`.claude/` 下的守衛檔與 settings 只能這樣改）。

完成後簡短回報：首次執行？跨平台切換？（以 [1/7] 第三行「最近 commit 開發平台（git 判定）」為準——「本機上次平台」只記這台機器，不可拿它回答；該行標「未 fetch」或「未與 origin 比對」時先完成第 1 步再看；對面機器有 commit 尚未 push 時本機看不到屬正常）同步結果？.venv 重建？hooks 正常？有無待我處理的警告？然後等我下任務，不要自己開工。
```

## 🔁 平台切換 SOP

兩種拓撲皆適用（ONBOARDING §2.1）：共用工作目錄、雙機各自 clone。A、B 兩段都要做。額度／模型參數的真相在 repo 的 `env.shared`，本機 `.env` 只放例外，pull 後自動對齊（ONBOARDING §2.2）——不必手動同步參數檔。

### A. 離開前（做在要離開的機器；關機後補不回來）
```bash
git fetch origin
git status --porcelain --untracked-files=all           # 期望：無輸出。--untracked-files=all 不可省：未 add 的新檔對 git ls-files 型掃描面隱形，會讓閘門假綠
git rev-list --left-right --count origin/main...main   # 期望：0<TAB>0（左＝落後、右＝領先未 push）
git stash list                                         # 期望：無輸出
git worktree list                                      # 期望：只有主 checkout 一行
gh run list --limit 10 --json workflowName,conclusion,event,createdAt,headSha   # 雲端 CI 唯讀現查
```
雲端 CI 判讀：只有 `root-infra-ci.yml` 是全變更觸發，其餘有 `paths` 白名單 ⇒ 先列「這次 push 應觸發哪幾支」再對帳，**缺席＝未驗證，不是通過**；還沒回來的 run 把 `headSha` 寫進交接。順手用上表的排程現查看一眼還掛著哪些哨兵／喚醒 job（不必拆：閒置 6 小時會自動收；睡著的 Mac 本來就不會被叫醒）。

### B. 到達後（做在剛到的機器；順序不可調換：**閘門先、回填後**——回填寫的是根層 `ONBOARDING.md`，先回填後發現紅，成果會被自己的紅鎖在本機）

1. **跑一次啟動提示詞**（全新 Windows 機器先 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`）。看 SessionStart 簡報的 `statusLine：` 句：印「未安裝」或「已安裝但與本 checkout 不符」時，`<python> tools/install_statusline.py --dry-run` 預覽、確認後去掉旗標安裝，再開新 claude 視窗看最下方有無 `ctx NN%`（選配；每台機器各一份、不隨 clone 走）。
2. **跑全套閘門確立新平台基線，紅燈在這步清完**（指令見 ONBOARDING §7 與根 CLAUDE.md；本檔不抄數字）——剛過來的第一輪最容易冒出跨平台缺口，是本步目的、不是意外。
3. 🔴 **回填本平台 ONBOARDING §7 表②**——唯一只能在目標平台做的事（跨平台代填＝假 provenance，工具 rc=2 拒絕）。首選一條龍載具 `tools/lib/clean_venv_carrier.py`（建樹外乾淨 venv → 裝依賴 → 探針 psycopg2／sqlalchemy 必 ABSENT → `--write --with-slow` 回填 → 必刪）：
   ```bash
   "$(git rev-parse --show-toplevel)/.venv/bin/python" tools/lib/clean_venv_carrier.py
   ```
   ```powershell
   & "$(git rev-parse --show-toplevel)\.venv\Scripts\python.exe" tools/lib/clean_venv_carrier.py
   ```
   - 前提：**docker daemon 要開**（`docker info` 印得出版本）；**不准 `--allow-pg-extras`**（會把 provenance 悄悄改成 `pgextras=present`）；本機 `.venv` 不可當乾淨 venv（幾乎必裝過 pg extras，工具 rc=2 拒用），一定要另建在 **repo 樹外**。
   - 手動備援（只在載具本身壞掉時；出廠定義＝`tools/bootstrap_core.py`；目錄名須含 `cleanvenv` 且放暫存目錄，dev_start 的殘留掃描才認得；extras 一律單引號）：
     ```bash
     python3.11 -m venv "${TMPDIR:-/tmp}/cleanvenv"
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
   - **回填排在 commit/push 之前，回填後不再改那四棵樹**（改了就再回填一次）；驗收＝`--check-snapshot` 本平台欄綠。**收尾**：手動備援建的樹外 venv 立刻刪掉（載具已自刪）；Docker 若只為回填才開就關掉（mac 要 quit 兩個 app 名：`osascript -e 'quit app "Docker"'` 再 `osascript -e 'quit app "Docker Desktop"'`，`pgrep -f Docker.app` 為空才算；Windows 系統匣 Quit）。

### C. 兩平台語法雷區（實際踩過；完整對照 ONBOARDING §5／§6／§7）

| 症狀 | 根因 → 正解 |
|---|---|
| mac 裝 extras 報 `zsh: no matches found` | zsh 把未引號的 `.[...]` 當 glob → extras 一律單引號 `'.[dev,notifications]'` |
| win 跑 `PYTHONUTF8=1 lint-imports` 報 `not recognized` | PowerShell 沒有 `VAR=value 指令` 前綴語法 → `$env:PYTHONUTF8=1; lint-imports` |
| win 呼叫 bash 腳本得到 UTF-16 亂碼「WSL has no installed distributions」 | 裸名 `bash` 先命中 System32 的 WSL 佔位 → 一律解析成絕對路徑（`tools/lib/Find-GitBash.ps1`、`tools/integration_gate_core.py::find_git_bash()`），禁止把裸 `"bash"` 交給 subprocess |
| mac 讀 `${PIPESTATUS[0]}` 得空字串 | Claude Code 的 Bash 工具在 mac 是 zsh：陣列叫 `pipestatus`、下標從 1 起 → 別用管線判 rc：`cmd > out.log 2>&1; rc=$?` |
| mac 迴圈跑「指令 + 參數」字串全報 rc=2 | zsh 不對未引號變數分詞 → 需要分詞就包 `bash -c '…'` 或用陣列 |
| bash 3.2（mac 內建；launchd 下的 hook／腳本）把 `$var；` 的全形字首位元組併進變數名，`set -u` 下 unbound 中止 | 變數後緊接非 ASCII 一律寫 `${var}` |
| push 被 pre-push 擋、印「找不到 ruff」 | root-infra 快層跑 `ruff check tools/`，ruff 缺席刻意 fail-loud → 先啟用根層 .venv 並裝好開發相依 |
| `git push` 非零但看不到 `remote:` 行、尾段卻像全綠 | 沒送到伺服器，是 pre-push 自己紅；尾段樂觀字樣屬某一段 leg → 只看 `main -> main` 那行；真因搜 `[pre-push` 的 ❌ 行，在中段 |
| push 被擋（`refresh_nightly_anchor.py --check-head` 失敗，或 FAIL 在 `test_doc_loc_baseline_freshness_r60`），訊息含「`nightly-checked-at` … 已是 N 天前」 | ONBOARDING §7 表③ 錨的排程軌過期帶；本機 nightly 每日把它寫回工作樹，多半只是沒被 commit 帶走 → 照訊息末行處置：`git add ONBOARDING.md` 併入 commit；工作樹也舊時先 `python tools/refresh_nightly_anchor.py --write`（需 `gh auth login`；排程通道停擺時先 `gh workflow run windows-compat-ci.yml`／`macos-compat-ci.yml` 補跑）。細節見 ONBOARDING §7 SOP 第 6 步 |

### D. 跑全套測試前：拉起 CI 對等 PG 容器（兩平台共通）

AutoClaude 有一整類 PG 相依測試只因 docker 沒開而 skip；一行 compose 即可，conftest 的 PG autodetect 會自己注入 DSN（影響幾支是量測值，本檔不寫；見 ONBOARDING §7.1）。🔴 PG 在場時 pytest 必加 `--dist loadgroup`（預設 `worksteal` 會讓多個 worker 同碰一顆 PG，conftest 會拒跑並教你怎麼改）。容器是 tmpfs，每次新建都要 migrate。

```bash
open -a Docker && docker info --format '{{.ServerVersion}}'       # 印得出版本才算 daemon 活著
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d
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
⚠️ 別和 B 段第 3 步搞混：那步要的是**出廠環境乾淨 venv**（PG driver 缺席）；本節是日常開發把 skip 降到最低。做完記得收：`docker compose -f docker-compose.ci.yml down`，Docker 只為此開的就關掉（同 B 段第 3 步收尾）。mac 首次建 `run_act` runner 映像會撞 `DeadlineExceeded`：先 pull 基底再 build，見 ONBOARDING §1 的 Docker 列。
