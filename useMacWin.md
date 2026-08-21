# 跨平台啟動提示詞與平台切換 SOP（macOS / Windows）

本檔兩用：

1. **啟動**——給 Claude Code 的完整提示詞，新開 session 第一則訊息直接複製貼上對應平台版本。核心依據：[tools/dev_start.py](tools/dev_start.py)。
2. **切換**——換平台時該做什麼、該驗什麼：見〈🔁 平台切換 SOP〉。**A 段（離開前）事後補不回來**；**B 段有一件事只能在目標平台做**（ONBOARDING §7 表② dated snapshot 回填）。

> 兩份提示詞刻意各自完整（要能整段貼上），故有重複；差異只在載具、venv 路徑與平台專屬健檢項。核心紀律相同：不硬做、不自動 push/stash、先讀子專案 CLAUDE.md、繁體中文回覆。

---

## 🍎 macOS 版

```
我現在在 macOS 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.sh 存不存在才決定要不要同步——落後 origin 與「檔案存在但版本過舊」兩種情況都該先同步）：
   a. git branch --show-current 確認在 main。若不是 main，把分支名與 git status 列給我看，等我決定；不要自行切換，也不要在非 main 分支跑下面的 merge（在 main 的舊祖先分支上 --ff-only 會把該分支指標靜默推到 origin/main＝改寫分支）。
   b. 確認此刻沒有 nightly 在跑（**不可跳過**）：
        .venv/bin/python tools/dev_start.py --check-nightly
      三態：idle（rc=0）才往下做；NIGHTLY-RUNNING（rc=1）停下等它跑完再同步，**期間不要跑任何測試**；UNDETERMINED（rc 仍為 0，代表偵測機制自己判不出來，**不是「沒在跑」**）則自己查證再往下。
      查證用「行程是否存活」最決定性（log 尾巴會有停頓，容易誤判）：
        ps -eo pid,etime,command | grep -E 'run_local_nightly|-m pytest' | grep -v grep
      為何非查不可：nightly 由 launchd 排程（含 RunAtLoad 補跑），極易與「開機後開工」撞在同一分鐘。Windows 側 2026-07-27 實測：merge 抽換檔案正落在 nightly 的 pytest 區間中間 → 5 支假紅（單獨重跑全綠），且假紅會寫進心跳檔，讓**之後每天早上**的 dev_start 都報「上一輪有失敗」，把人導去追不存在的迴歸。兩平台同構。
      （首次 clone、.venv 還沒建好時可略過——沒有 .venv 就沒有 nightly 排程；舊 checkout 若回報 unrecognized arguments，代表這支旗標要同步後才有。）
   c. git fetch origin
      fetch 失敗（離線）：不要重試卡住，明確說「本次離線、跳過同步」，第 2 步改成 source tools/dev_start.sh --no-sync。
   d. git merge --ff-only origin/main
      失敗（本地領先／分叉／未提交變更擋住）：把 git status 與 git log main..origin/main 列給我看，不要自動 rebase、reset --hard 或 stash。
   同步完成（或確認離線）才繼續下一步。

2. 用 Bash 工具在 repo 根目錄執行（**timeout 設到上限 10 分鐘**：首次執行或依賴變動時 bootstrap 合法耗時數分鐘，預設 2 分鐘會腰斬安裝。真的被中斷就重跑同一條——腳本有未完成哨兵，會自動偵測半殘 .venv 重新整備）：
   source tools/dev_start.sh
   （bash/zsh 皆可；勿用 POSIX sh/dash，wrapper 明文不支援）
   它會依序做七件事：[1/7] 偵測是否跨平台切換 ／ [2/7] GitHub 同步（髒工作樹／分叉／離線只提醒，不自動 stash/rebase/push；偵測到 nightly 在跑時即使落後也**不自動 pull**）／ [3/7] 切換時清除失效快取 ／ [4/7] 整備或修復 .venv（跨平台換手保留、依賴 hash 比對、必要時自動 bootstrap）／ [5/7] 檢查並修復 git hooks（core.hooksPath）／ [6/7] 平台健檢 ／ [7/7] 狀態寫回。
   [6/7] 有三件事要注意：
     · nightly 心跳三態：mac 上用 launchctl 消歧「已載入尚未首跑」vs「未安裝」；查不到就印「未偵測＝排程未啟用或尚未跑過第一輪」，屬 advisory 不會 ❌。
     · **心跳「新鮮」不等於「上一輪跑成功」**——心跳未過期時，若上一輪實際有失敗仍會另印一行「⚠️ nightly 最近一輪有 FAIL=N」，看到心跳正常也要讀那一行。
     · GitHub CI 可能印兩種 ⚠️（最新一筆 run 非 success／排程軌長期未成功，兩種粒度）。**都不要當背景雜訊**：雲端 CI 是否活著是輪次屬性、不是常數 ⇒ 看到就當場唯讀現查 `gh run list --limit 10` 再判讀。（僅在本機有 gh 且 fetch 未離線時才嘗試。）

3. 檢查輸出的「dev_start 摘要」：
   - 結尾是 ❌：先幫我排除，不要跳過忽略，也不要用 --force-bootstrap 以外的手段硬做。
   - ❌ 是「另一個 dev_start 正在整備 venv／取不到互斥鎖」：先確認真的沒有另一個 dev_start 在跑（含前次中斷遺留的行程）再回報我；陳舊鎖會在下次執行時自動清除，不要手動刪 .dev_start.lock。
   - 只有 ⚠️（「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類）：簡短列給我，讓我決定，不要自動 commit/stash/push。
   - ⚠️ 是「nightly 最近一輪有失敗」：🔴 **不是只有「假紅／真迴歸」兩態，共三態**。① 比對失敗 stage 起訖時間與 `git reflog --date=iso` 最近一次 merge/pull，時間重疊＝高度可疑假紅；② **不論時間有無重疊，都必須在當前 HEAD 上重跑一次**——nightly 跑的是 merge **前**的 code，對 merge 後的 HEAD 沒有推論力；③ 實遇第三態（2026-08-10）：時間不重疊（非假紅），但那輪的失敗已被 merge 進來的修復解掉，同時換上一批**全新**失敗。只回答「是不是假紅」就結案，會同時追錯舊紅、漏看新紅（DEF-101-999(d)）。假紅要跟我說一聲，別默默當迴歸修。
   - **沒看到「工作樹不乾淨」不等於工作樹乾淨**：① dev_start 只在「同時落後 origin、真的要 pull」時才提；② 它用的是 `--untracked-files=no`，**未追蹤檔完全不在視野內**（ff pull 對未追蹤檔安全，是刻意設計）。要確認自己跑 `git status --porcelain --untracked-files=all`（理由見 A 段）。

4. shell 狀態不跨工具呼叫存活（每次呼叫都是新行程，source 啟用的 .venv 只在那一次有效）⇒ 之後所有 Python 指令（pytest、ruff、pip）一律用 `.venv/bin/python`，不要誤用系統 Python。

5. 確認你已讀過根 CLAUDE.md（monorepo 導覽）；動手前先確定本次工作屬於哪個子專案，進去前先讀它自己的 CLAUDE.md——兩份子 CLAUDE.md 都是 override 級規範，其目錄／命名／測試規則以子專案內部路徑為準。

6. 回覆一律使用繁體中文。

7. **ONBOARDING §7 表② macOS 欄回填**——🔴 **判斷依據是機械判準，不是記憶、也不是 dev_start [1/7]**（`[1/7]` 讀本機 .dev_env_state.json，雙機各自 clone 的拓撲永遠印「無切換」，用它判斷必然漏做）。**每次啟動都跑這一條**：
     .venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot
   讀 **macOS 欄**：只要它是 `presumed stale`、或 `baseline-origin` 不是 `self-recorded`，本欄就需要回填；三項都新鮮才可跳過。
   🔴 **綠了也不代表本輪不必做**：只要你本輪 commit 動到受監測的樹（tools/、AutoClaude/、AISDLC_SDD/），指紋就會漂移、這一條會由綠翻紅，而它是 pre-push 的阻斷項 ⇒ **回填要排在 commit/push 之前，且回填之後不要再改那些樹**（改了就得再回填一次）。
   回填只能在 macOS 本機做（跨平台代填＝假 provenance，工具 rc=2 拒絕），且必須用**不含 postgres/pgvector 的出廠環境 venv**，**不准**加 --allow-pg-extras 繞過。🔴 那個 venv **不是**本機 .venv（本機 .venv 幾乎必然已被 pg extras 汙染，工具會 rc=2 拒跑）⇒ 必須另建臨時乾淨 venv（建法與污染探針見 B 段第 3 點；本機**沒有** uv，用 venv 自帶的 pip）。動手前把 B 段整段讀完，不要只照這一行做；做完把工具輸出貼給我。

完成後跟我簡短回報環境狀態（是否首次執行、是否偵測到跨平台切換、GitHub 同步結果、.venv 是否重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際任務，不要自己先開始做事。
```

---

## 🪟 Windows 版

```
我現在在 Windows 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.ps1 存不存在才決定要不要同步）：
   a. git branch --show-current 確認在 main。若不是 main，把分支名與 git status 列給我看，等我決定；不要自行切換，也不要在非 main 分支跑下面的 merge（在 main 的舊祖先分支上 --ff-only 會把該分支指標靜默推到 origin/main＝改寫分支）。
   b. 確認此刻沒有 nightly 在跑（**不可跳過**）：
        .venv\Scripts\python.exe tools/dev_start.py --check-nightly
      三態：idle（rc=0）才往下做；NIGHTLY-RUNNING（rc=1）停下等它跑完再同步，**期間不要跑任何測試**；UNDETERMINED（rc 仍為 0，代表偵測機制自己判不出來，**不是「沒在跑」**）則自己查證再往下（查 AutoClaude/logs/ 最新 nightly log 尾巴是否還在長，或用 Get-Process 查行程是否存活——後者更決定性）。
      為何非查不可：本機 nightly 走 schtasks 補跑（WakeToRun／StartWhenAvailable），機器一喚醒就補跑，正是你開工的同一分鐘。2026-07-27 實測：git merge 於 18:41:26 抽換 113 個檔案，落在 nightly 那輪 pytest 區間（18:41:10～18:42:50）正中間 → 5 支假紅（單獨重跑全數通過）；更糟的是假紅寫進 nightly_latest.log，讓**之後每天早上**的心跳哨兵都報「上一輪有失敗」，把人導去追不存在的迴歸。
      （首次 clone、.venv 還沒建好時可略過；舊 checkout 若回報 unrecognized arguments，代表這支旗標要同步後才有。）
   c. git fetch origin
      fetch 失敗（離線）：不要重試卡住，明確說「本次離線、跳過同步」，第 2 步的 dev_start 指令後面加 --no-sync。
   d. git merge --ff-only origin/main
      失敗（本地領先／分叉／未提交變更擋住）：把 git status 與 git log main..origin/main 列給我看，不要自動 rebase、reset --hard 或 stash。
   同步完成（或確認離線）才繼續下一步。

2. 執行啟動程序（**timeout 設到上限 10 分鐘**：首次執行或依賴變動時 bootstrap 合法耗時數分鐘。被中斷就重跑同一條——腳本有未完成哨兵）。依載具二選一：
   - 原生 PowerShell（含 Claude Code 的 PowerShell 工具；**優先用這條**）——在 repo 根目錄 dot-source（前面的點與空格不可省）：
     . .\tools\dev_start.ps1
     成敗看輸出結尾「dev_start 摘要」的 ✅/❌ 或 $LASTEXITCODE；**絕不可用 $?**（dot-source 後任何成功的陳述式都會把 $? 重設為 true，wrapper 檔頭 .NOTES 明載此陷阱）。
   - Git Bash／WSL 等非 PowerShell 載具：
     powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1
     一定要 -File，**不要**用 -Command 包 dot-source（dot-source 模式的 wrapper 刻意不呼叫 exit 以免關掉使用者 shell，經 -Command 呼叫時失敗的 exit code 會被吞掉、外層恆拿到 0＝假綠）。
   它會依序做七件事：[1/7] 偵測是否跨平台切換 ／ [2/7] GitHub 同步（髒工作樹／分叉／離線只提醒，不自動 stash/rebase/push；偵測到 nightly 在跑時即使落後也**不自動 pull**）／ [3/7] 切換時清除失效快取 ／ [4/7] 整備或修復 .venv ／ [5/7] 檢查並修復 git hooks ／ [6/7] 平台健檢 ／ [7/7] 狀態寫回。
   [6/7] 有四件事要注意：
     · 自動設定 core.longpaths=true——🔴 **別讀成「有人在管了」**：這裡設的是 --local，`git clone` 當下它還不存在（三層 config 實查只有 --local 是 true ⇒ fresh clone 零保護）。實測未帶旗標 clone 到深路徑會 rc=128、tracked 檔只落地零星幾百支且 tools\bootstrap.ps1 根本不在磁碟上，那種工作樹上第 2 點那條指令毫無意義。⇒ **clone 當下必須自己帶** `git clone -c core.longpaths=true <url>`，並建議一次性 `git config --global core.longpaths true`；完整開箱見 ONBOARDING.md §2 第 0 步。
     · nightly 心跳三態：「未偵測」＝排程未啟用**或**已安裝但尚未跑過第一輪，屬 advisory 不會 ❌。
     · **心跳「新鮮」不等於「上一輪跑成功」**——心跳未過期時，若上一輪實際有失敗仍會另印「⚠️ …有失敗…exit=1（failed stages: …）」，看到心跳正常也要讀那一行。
     · GitHub CI 可能印兩種 ⚠️（最新一筆 run 非 success／排程軌長期未成功，兩種粒度）。**都不要當背景雜訊**：雲端 CI 是否活著是輪次屬性、不是常數 ⇒ 看到就當場唯讀現查 `gh run list --limit 10` 再判讀。（僅在本機有 gh 且 fetch 未離線時才嘗試。）

3. 檢查輸出的「dev_start 摘要」：
   - 結尾是 ❌：先幫我排除，不要跳過忽略，也不要用 --force-bootstrap 以外的手段硬做。
   - ❌ 是「另一個 dev_start 正在整備 venv／取不到互斥鎖」：先確認真的沒有另一個 dev_start 在跑再回報我；陳舊鎖會自動清除，不要手動刪 .dev_start.lock。
   - 只有 ⚠️（「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類）：簡短列給我，讓我決定，不要自動 commit/stash/push。
   - 出現「偵測不到 Git Bash（bash.exe）」（來自 [5/7] 的 hooks 安裝腳本，不進摘要警告計數）：**不要當無害雜訊**。`tools/lib/Find-GitBash.ps1::Find-GitBash` 先查 PATH（排除 System32 的 WSL 佔位）再回退查標準安裝目錄，而回退存在的目的正是「標準安裝只把 Git\cmd 放進 PATH」⇒ **連回退都落空才會印這行**，多半真的沒裝 Git for Windows。三支 dispatcher hooks 都是 `#!/usr/bin/env bash`，屆時 commit/push 會真的跑不起來。請先跑 `git --version` 與 `where.exe bash` 把實況列給我。
   - ⚠️ 是「nightly 最近一輪有失敗」：🔴 **共三態，不是兩態**。① 比對失敗 stage 起訖時間與 `git reflog --date=iso` 最近一次 merge/pull，時間重疊＝高度可疑假紅（2026-07-27 實測即是：5 支假紅、單獨重跑全通）；② **不論時間有無重疊，都必須在當前 HEAD 上重跑一次**——nightly 跑的是 merge **前**的 code，對 merge 後的 HEAD 沒有推論力；③ 實遇第三態（2026-08-10 mac 側）：時間不重疊（非假紅），但那輪失敗已被 merge 進來的修復解掉，同時換上一批**全新**失敗。只回答「是不是假紅」就結案，會同時追錯舊紅、漏看新紅（DEF-101-999(d)）。假紅要跟我說一聲，別默默當迴歸修。
   - **沒看到「工作樹不乾淨」不等於工作樹乾淨**：① dev_start 只在「同時落後 origin、真的要 pull」時才提；② 它用的是 `--untracked-files=no`，**未追蹤檔完全不在視野內**。要確認自己跑 `git status --porcelain --untracked-files=all`（理由見 A 段）。

4. 之後所有 Python 指令（pytest、ruff、pip）一律用 `.venv\Scripts\python.exe`（Git Bash 載具下 `.venv/Scripts/python.exe`），不要誤用系統 Python。

5. 確認你已讀過根 CLAUDE.md（monorepo 導覽）；動手前先確定本次工作屬於哪個子專案，進去前先讀它自己的 CLAUDE.md——兩份子 CLAUDE.md 都是 override 級規範，其目錄／命名／測試規則以子專案內部路徑為準。

6. 回覆一律使用繁體中文。

7. **ONBOARDING §7 表② Windows 欄回填**——🔴 **判斷依據是機械判準，不是記憶、也不是 dev_start [1/7]**（`[1/7]` 讀本機 .dev_env_state.json，雙機各自 clone 的拓撲永遠印「無切換」）。**每次啟動都跑這一條**：
     .venv\Scripts\python.exe tools/sync_onboarding_baselines.py --check-snapshot
   讀 **Windows 欄**：只要它是 `presumed stale`、或 `baseline-origin` 不是 `self-recorded`，本欄就需要回填；三項都新鮮才可跳過。
   🔴 **綠了也不代表本輪不必做**：只要你本輪 commit 動到受監測的樹（tools/、AutoClaude/、AISDLC_SDD/），指紋就會漂移、這一條會由綠翻紅，而它是 pre-push 的阻斷項 ⇒ **回填要排在 commit/push 之前，且回填之後不要再改那些樹**。
   回填只能在 Windows 本機做（跨平台代填＝假 provenance，工具 rc=2 拒絕），且必須用**不含 postgres/pgvector 的出廠環境 venv**，**不准**加 --allow-pg-extras 繞過。🔴 那個 venv **不是**本機 .venv（主 .venv 只要曾裝過 [postgres,pgvector] 就會讓工具 rc=2 拒跑）⇒ 必須另建臨時乾淨 venv（建法與污染探針見 B 段第 3 點）。動手前把 B 段整段讀完；做完把工具輸出貼給我。

完成後跟我簡短回報環境狀態（是否首次執行、是否偵測到跨平台切換、GitHub 同步結果、.venv 是否重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際任務，不要自己先開始做事。
```

---

## 🔁 平台切換 SOP

適用兩種拓撲（見 [ONBOARDING.md](ONBOARDING.md) §2.1）：**共用工作目錄**（外接碟／同步資料夾輪開同一份）與**雙機各自 clone**。差別只在「切換」是不是同一顆工作樹——A、B 兩段都要做。

### A. 切換前 —— 做在「要離開」的那台機器上

每一項在關機之後都補不回來。五條指令兩平台**逐字相同**：

```bash
git fetch origin                                       # 先 fetch，下一條才有意義
git status --porcelain --untracked-files=all           # 期望：完全無輸出
git rev-list --left-right --count origin/main...main   # 期望：0<TAB>0（左＝落後、右＝領先未 push）
git stash list                                         # 期望：完全無輸出
git worktree list                                      # 期望：只有主 checkout 一行
```

🔴 **`--untracked-files=all` 不可省**：預設 `-unormal` 會把整個未追蹤目錄摺成一行 `?? sub/`，而**未 `git add` 的新檔對 `git ls-files` 型掃描面天然隱形**——`DEF-101-751`／`752` 就是這樣：一支全程 untracked 的新 `.py` 讓四輪四方複審與多次全套閘門都拿到「全綠」，直到 `git add` 那刻才冒出真紅。把它留在原機器＝把一個看不見的違規留在原地。

🔴 **雲端 CI：唯讀現查，且「未觸發 ≠ 綠」**

```bash
gh run list --limit 10 --json workflowName,conclusion,event,createdAt,headSha
```

根層 workflow 只有 `root-infra-ci.yml` 是全變更觸發（`on:` 底下無 `paths`，可自行實查）；其餘都有 `paths` 白名單，沒命中就**根本不會出現在 run 清單裡** ⇒ 判讀時先列出「這次 push 應該觸發哪幾支」再對帳，**缺席一律當未驗證，不是通過**。走人前若有還沒回來的 run，把 `headSha` 記進交接說明。

> 本節刻意**不記**「哪個平台的 CI 現在是綠是紅」——那是輪次屬性、不是常數（ONBOARDING §6.1／§9 同型訂正）。

### B. 切換後 —— 做在「剛到」的那台機器上

🔴 **三步順序不可調換，「閘門」必須排在「回填」之前**：回填寫的是 `ONBOARDING.md`＝根層檔，而 `tools/git-hooks/pre-push` 的慢層（`py_compile` ＋ `run_root_unittests.py`）**只在 push 範圍含根層檔時才跑**。先回填、後才發現那層有紅 ⇒ 回填成果 commit 過得去卻 **push 不出去**，被自己的紅鎖在本機（2026-08-10 實遇，DEF-101-999(e)）。

1. **照對應平台的啟動提示詞跑一次**。全新 Windows 機器另有一次性前置：預設 `ExecutionPolicy=Restricted` 會擋掉所有 `.ps1`（**含 dot-source 與 `Activate.ps1`**），先跑 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`（一般權限即可，見 ONBOARDING §2.1／§5）。預期會看到 `[1/7]` 印跨平台切換、`[3/7]` 清掉含絕對路徑的 `.pytest_cache`/`.ruff_cache`、`[4/7]` 把另一平台的 `.venv` 換手保留（共用工作目錄拓撲；雙機拓撲則各自新鮮）。

2. **跑一次全套閘門確立新平台基線，紅燈在這一步清完**：指令清單以 ONBOARDING §7 與根 [CLAUDE.md](CLAUDE.md) 為準。**本檔刻意不重抄任何數字**——基線數字唯一站點是 ONBOARDING §7（`tools/check_pytest_baseline_sites.py` 機械守門，本檔在其掃描面內）。剛過來的第一輪最容易在這裡冒出跨平台缺口（對方平台結構上跑不到的路徑），**那是本步驟的目的、不是意外**。

3. 🔴 **回填該平台的 ONBOARDING §7 表② dated snapshot —— 整份 SOP 裡唯一「只能在目標平台做」的事**：

   ```bash
   <乾淨 venv>/bin/python tools/sync_onboarding_baselines.py --write --with-slow
   ```

   - **為何只能在目標平台**：表② 是 dated snapshot（無 live 鎖，機器算不出來），逐平台記帳；跨平台代填＝假 provenance，工具對無對應欄的平台直接 rc=2 拒絕。
   - 🔴 **前置①：乾淨 venv（不是本機 `.venv`）**：`psycopg2` 與 `sqlalchemy` 都必須是 ModuleNotFoundError。污染探針用這個寫法（乾淨與污染**兩種情況都必定印出東西**，沒有會被誤讀成乾淨的「靜默零輸出」；`pip list` 在 uv 建的 venv 上零鑑別力——那種 venv 內根本沒有 `pip` 模組）：

     ```bash
     python -c "import importlib.util as u; [print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') for m in ('psycopg2','sqlalchemy')]"
     ```

     兩行都要是 `ABSENT` 才算乾淨；**任何一行印不出來就是探針壞了**，不是「乾淨」。建法：全新臨時目錄 ＋ `python3.11 -m venv` ＋ `uv pip install -e '.[dev,notifications]'`；🔴 **但 `uv` 不一定在**（mac 側實測 `command -v uv` 為空，它只活在 shell profile 裡），此時改用新 venv 自帶的 `python -m pip install -e '.[dev,notifications]'`。
   - 🔴 **前置②：docker daemon 要開**：ci-gate 逐軌計數對它敏感，provenance 會如實記 `docker=up`／`down`。兩平台欄一個 up 一個 down 就是**不同條件**，依 §7 紀律**不可相減**（2026-08-10 實遇：忘了開，兩欄從此不可比，只能等下次重量，DEF-101-999(e)）。
   - 🔴 **不准用 `--allow-pg-extras` 繞過拒跑**：那會讓 provenance 記成 `pgextras=present`，等於悄悄改掉「出廠環境」的定義，且**沒有任何機械物會替你察覺**。工具拒跑是設計，不是障礙。
   - 🔴 **回填要排在 commit／push 之前**：這一條的指紋讀的是工作樹。本輪 commit 只要動到受監測的樹，`--check-snapshot` 就會由綠翻紅，而它是 pre-push 阻斷項 ⇒ 回填之後不要再改那些樹（改了就得再回填一次）。
   - **`unrecorded` 的語意**：只代表「該欄數字量於逐平台 provenance 機制落地之前，或不是同世代值」，**不等於那個平台沒有真機開發史**。要知道哪一欄新鮮、誰在哪台機器量的，一律看 live 來源：

     ```bash
     python tools/sync_onboarding_baselines.py --check-snapshot   # 各欄 provenance ＋ presumed-stale 判定
     grep -n 'snapshot-fingerprints-' ONBOARDING.md               # 兩條錨的 measured-at/host/docker/pgextras
     ```

     `--check-snapshot` 的 rc 反映的是「**本機平台那一欄**的指紋有沒有漂移」，不是「有沒有真機量測過」。非本機平台欄在單機交替下**結構上恆為 presumed stale**，那則 `ℹ️` 是常態而非事件。

### C. 兩平台語法差異雷區（照抄另一平台的指令會出事）

完整對照見 ONBOARDING §5（雷區表）、§6（雙平台腳本對照）、§7（雙平台驗證指令）。以下都是實際踩過的。

| 症狀 | 根因 | 正確寫法 |
|------|------|---------|
| macOS 上安裝 extras 報 `zsh: no matches found`，訊息與套件無關 | zsh 預設 `nomatch`：未加引號的 `.[...]` 被當 glob 做 filename generation，repo 內無匹配即**在執行前中止整條指令**（uv／pip 根本沒被呼叫）。同一行在 bash 與 PowerShell 下正常 ⇒ Windows 開發者永遠不會遇到 | extras 一律**單引號**：`uv pip install -e '.[dev,notifications]'`（三種 shell 皆正確）；具名套件同理 `'autoclaude[postgres]'`。機械鎖：`tools/tests/test_extras_quoting_zsh_safety.py` |
| Windows 上 `PYTHONUTF8=1 lint-imports` 報 `The term 'PYTHONUTF8=1' is not recognized`，看起來像 lint-imports 沒裝 | PowerShell **沒有** `VAR=value <指令>` 行內前綴語法 | 改寫 `$env:PYTHONUTF8=1; lint-imports`。機械鎖：`tools/tests/test_doc_env_prefix_platform_parity_r60.py` |
| Windows 上呼叫 bash 腳本得到 UTF-16LE 亂碼 `Windows Subsystem for Linux has no installed distributions.`，而受測腳本**一行都沒執行**（歸因完全錯誤的紅燈） | `CreateProcess(lpApplicationName=NULL)` 解析裸名的順序把 **System32 排在 PATH 之前** ⇒ argv[0] 是裸名 `"bash"` 時，`C:\Windows\System32\bash.exe`（WSL 啟動器）**必定**先命中，與 PATH 上有沒有 Git Bash 無關（`DEF-101-753`） | 一律解析成**絕對路徑**再呼叫：PowerShell 用 `tools/lib/Find-GitBash.ps1::Find-GitBash`、Python 測試用 `tools/tests/_platform_helpers.usable_bash_for_fixture()`、Python 工具用 `tools/integration_gate_core.py::find_git_bash()`。**禁止**把裸 `"bash"` 交給 `subprocess` |
| macOS 上讀 `${PIPESTATUS[0]}` 拿到**空字串**，管線 rc 靜默消失（`cmd \| tail` 之後判不出成敗，容易把紅讀成綠） | Claude Code 的 Bash 工具在 macOS 走 **zsh**，`PIPESTATUS` 是 bash 的陣列名；zsh 叫 `pipestatus` 且**下標從 1 起**（`$pipestatus[1]`）。兩平台的 `.ps1`／CI 不受影響 | 別用管線判 rc：改 `cmd > out.log 2>&1; rc=$?` 再讀檔；或整段包 `bash -c '…'`。2026-08-10 實遇（DEF-101-999(c)） |
| macOS 上迴圈跑「帶子指令參數的守門」全報 `rc=2`，像整批守門紅掉，實際 `bash` 下全綠 | zsh **預設不對未加引號的變數做分詞**（no SH_WORD_SPLIT）：`for g in "x.py --check"; do $PY $g; done` 把整串當**單一檔名**交給 python ⇒ `can't open file` 的 rc 恰好也是 2，與「守門判紅」從 rc 無法區分 | 需要分詞就顯式包 `bash -c '…'`（pre-push 本身是 bash，故 hook 內同寫法正確）；或改用陣列逐項傳參。2026-08-10 實遇並**一度誤報三支守門為紅**（DEF-101-999(c)） |
| push 被 pre-push 擋下並印「找不到 ruff」 | root-infra 快層對齊 `root-infra-ci.yml`，會跑 `ruff check tools/ --no-cache`；**ruff 缺席＝fail-loud（rc=1），刻意不軟跳過**（軟跳過會退回「宣告有、執行者無」的假綠）。另：ruff 的 `warning:`（如壞掉的 noqa）走 stderr 且不改 rc，本層收下 stderr 仍判失敗 | 先啟用 `.venv` 並裝好開發相依（hook 訊息即指路）。`--no-cache` 不可省的理由見 `tools/git-hooks/pre-push` 該段註解 |
| `git push` 回非零但**看不到 `remote:` 行**，而尾段還印著像「全綠」的字樣 | 沒有 `remote:`／`main -> main` ⇒ 根本沒送到伺服器，是 pre-push 自己回非零。尾段的樂觀字樣屬於**某一段** leg（例如 AutoClaude leg 的「✅ 本機 CI 閘門全綠」），不是整體判決 | 判「有沒有真的推上去」只看 `main -> main` 那一行。找真因搜 dispatcher 的 ❌ 行：`grep -nE '\[pre-push.*(❌\|✅)' <push log>`，真因在**中段**不在尾段 |

> 兩平台共通：shell 狀態不跨工具呼叫存活 ⇒ `source`／dot-source 啟用的 venv 只在那一次有效，之後一律用完整路徑 `.venv/bin/python`（mac）或 `.venv\Scripts\python.exe`（Windows）。

### D. 跑全套測試前：先把 CI 對等 PG 容器拉起來（兩平台共通）

AutoClaude 全套 pytest 的 `skipped` 裡有**一整類**（PG 相依）只是因為 docker daemon 沒開——不是缺件、不是平台差、也不是退化。解法是一行 `docker compose`，零程式改動、零環境變數（`AutoClaude/tests/conftest.py` 的 PG autodetect 會自己偵測並注入 DSN）。它影響幾支是**量測值**，本檔不寫死；完整做法、憑證行與誠實劃界見 **ONBOARDING.md §7.1**（唯一站點）。

```bash
# macOS / Linux（Windows 版見下一塊）
open -a Docker                                                   # 啟動 Docker Desktop
docker info --format '{{.ServerVersion}}'                        # 印得出版本號才算 daemon 活著
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d
# 容器是 tmpfs、用完即丟 ⇒ 每次新建都要 migrate 一次，否則 autodetect 的剎車會拒絕注入。
# migrate 必須自己給 DSN（alembic 是另一個行程，autodetect 只注入 pytest 那個行程）；刻意用
# 行內前綴而非 export——export 出去會讓 pytest 走「顯式優先」剎車，PG 照樣接得上，但你就
# 驗不到 autodetect 這條路是通的
AUTOCLAUDE_DB_DSN='postgresql://autoclaude:autoclaude@localhost:5432/autoclaude' alembic upgrade head
python -m pytest tests/ -q                                       # 尾端要出現 `[PG autodetect] 已注入 …`
```

```powershell
# Windows：先用 GUI 啟動 Docker Desktop，再跑下面這幾行
docker info --format '{{.ServerVersion}}'
# 🔴 定位子專案一律走 git 頂層，**不要**寫 `$env:CLAUDE_PROJECT_DIR\AutoClaude`——那個變數
# 只由 Claude Code 注入 hook 子行程，開發者自己開的終端機裡是空的，會展開成磁碟機根目錄
# （實測逐字 `Cannot find path '/AutoClaude' because it does not exist.`）
Push-Location (Join-Path (git rev-parse --show-toplevel) 'AutoClaude')
docker compose -f docker-compose.ci.yml up -d
$env:AUTOCLAUDE_DB_DSN = 'postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
alembic upgrade head
Remove-Item Env:\AUTOCLAUDE_DB_DSN     # 不清掉會讓下一行的 autodetect 被「顯式優先」剎車擋下
python -m pytest tests/ -q
Pop-Location
```

⚠️ **別和 B 段第 3 步搞混**：那一步（回填表②）要的是**出廠環境乾淨 venv**（PG driver 必須缺席）；本節是「日常開發時把 skip 降到最低」。provenance 會如實記 `docker=up`／`down`，**不同條件的兩欄依 §7 紀律不可相減**。

🔴 **mac 側第一次建 `run_act` runner 映像會撞 `DeadlineExceeded`（DEF-200-010）**：正解是**先 pull 基底、再 build**。做法、因果與失敗字面見 **ONBOARDING.md §前置條件的 Docker 那一列**（唯一站點）。

---

## 可選旗標

追加在提示詞第 2 步的 dev_start 指令後面（wrapper 原樣轉傳給 `tools/dev_start.py`）：

- `--no-sync`：跳過 GitHub 同步（離線時用；此時提示詞第 1 步的手動同步也一併跳過）
- `--force-bootstrap`：強制重跑 bootstrap 重新整備依賴（懷疑 .venv 不完整時用）
- `--check-nightly`：**只查**本機是否有 nightly 在跑後立刻結束，不做任何整備（idle→rc=0／NIGHTLY-RUNNING→rc=1／UNDETERMINED→rc=0）。提示詞第 1 步 b 用的就是它；平時想確認「現在能不能安心跑全套測試」也可單獨呼叫。查的是 nightly 腳本自己持有的去重鎖（Windows 具名 Mutex／mac 鎖目錄），**不是猜 log 時間**。

```
source tools/dev_start.sh --no-sync                                      # macOS
. .\tools\dev_start.ps1 --no-sync                                        # Windows（PowerShell）
powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1 --no-sync   # Windows（Git Bash/WSL 載具）
```
