# 跨平台啟動提示詞與平台切換 SOP（macOS / Windows）

本檔兩用：

1. **啟動**——給 Claude Code 使用的完整提示詞，於**新開 session 的第一則訊息**直接複製貼上對應平台版本即可。核心依據：[tools/dev_start.py](tools/dev_start.py) 跨平台自動偵測啟動程序。
2. **切換**——從一個平台換到另一個平台時「該做什麼、該驗什麼」：見下方〈🔁 平台切換 SOP〉。**切換前那一段做在「要離開」的機器上**，事後補不回來；**切換後那一段有一件事只能在目標平台做**（ONBOARDING §7 表② 的 dated snapshot 回填）。

兩份提示詞的差異只在啟動指令與載具（shell）注意事項、venv 路徑格式（`/` vs `\`、`bin/python` vs `Scripts\python.exe`）與平台健檢項目說明，核心紀律（不硬做、不自動 push/stash、先讀子專案 CLAUDE.md、繁體中文回覆）完全一致。

---

## 🍎 macOS 版

```
我現在在 macOS 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.sh 是否存在再決定要不要同步——本機可能落後 origin/main、或雖然檔案存在但版本過舊，兩種情況都該先同步再說）：
   a. 先確認目前在 main 分支：git branch --show-current。若不是 main，停下來把分支名與 git status 列給我看，等我決定，不要自行切換分支，也不要在非 main 分支上執行下面的 merge（在 main 的舊祖先分支上跑 --ff-only merge 會把該分支指標靜默推到 origin/main，等於改寫分支）。
   b. 再確認此刻沒有 nightly 正在跑（**不可跳過**）：
        .venv/bin/python tools/dev_start.py --check-nightly
      印出 idle（rc=0）才往下做；印出 NIGHTLY-RUNNING（rc=1）就停下來等它跑完（通常數分鐘，可看 AutoClaude/logs/ 最新 nightly_mac log 的尾巴是否還在長）再同步，**期間也不要跑任何測試**。
      若印出的是 **UNDETERMINED**（rc 仍為 0，代表偵測機制自己無法判定，不是「沒在跑」）：請自己看 AutoClaude/logs/ 最新 nightly log 的尾巴是否還在長，確認沒在跑再往下做（R59 SD-R59-07 補：此前只交代 idle／NIGHTLY-RUNNING 兩態，第三態可達卻無指示，照做的人會卡住或亂猜）。
      為何必要：nightly 由 launchd 排程（含 RunAtLoad 補跑），很容易與「開機後開工」撞在同一分鐘。Windows 側 2026-07-27 已實測出這個事故：git merge 抽換 113 個檔案時正落在 nightly 那輪 pytest 的執行區間中間 → 5 支測試假紅（單獨重跑全綠）；假紅還會寫進心跳檔，讓**之後每天早上**的 dev_start 都報「上一輪 nightly 有失敗」，把人導去追不存在的迴歸。兩平台同構，故 mac 側同樣先查再同步。
      （首次 clone、.venv 還沒建好時可略過此步——沒有 .venv 就不會有 nightly 排程；舊 checkout 若回報 unrecognized arguments，代表這支旗標要同步後才有，本次略過即可。）
   c. git fetch origin
      若 fetch 失敗（離線／網路問題）：不要卡住重試，明確告訴我「本次離線、跳過同步」，並把第 2 步的指令改成 source tools/dev_start.sh --no-sync 繼續本機整備。
   d. git merge --ff-only origin/main
      若 --ff-only 失敗（本地領先、與遠端分叉、或未提交變更擋住 fast-forward），把 git status 和 git log main..origin/main 的結果列給我看，不要自動 rebase、reset --hard 或 stash；先讓我看過再決定。
   同步完成（或確認離線）後才繼續下一步（此時 tools/dev_start.sh 必定存在且是最新版）。

2. 用 Bash 工具在 repo 根目錄執行（這次工具呼叫請把 timeout 設到上限 10 分鐘：首次執行或依賴變動時 bootstrap 合法耗時數分鐘，預設 2 分鐘 timeout 會腰斬安裝。萬一真的被中斷，直接重跑同一指令即可——腳本有未完成哨兵，會自動偵測半殘 .venv 重新整備）：
   source tools/dev_start.sh
   （bash/zsh 皆可；勿以 POSIX sh/dash 執行，wrapper 明文不支援）
   這是本專案的跨平台自動偵測啟動程序，會自動依序完成七件事：
   [1/7] 偵測目前環境（Developing vs Now）是否跨平台切換
   [2/7] GitHub 同步（fetch + fast-forward pull；髒工作樹/分叉/離線只會明示提醒，不會自動 stash/rebase/push；另偵測「nightly 正在跑」——此時落後 origin 也**不自動 pull**，只提醒你等它跑完再執行一次，避免抽換檔案造成整批假紅）
   [3/7] 跨平台切換時清除失效快取
   [4/7] 整備/修復 .venv（含跨平台換手保留、依賴 hash 比對、必要時自動跑 bootstrap）
   [5/7] 檢查並修復 git hooks（core.hooksPath）
   [6/7] 平台健檢（含 nightly 心跳三態檢查——mac 上會用 `launchctl` 自動消歧「已載入尚未首跑」vs「未安裝」（R15，SA-R15-REV-3 訂正同步）；查不到 launchctl 結果時退回「未偵測＝排程未啟用或尚未跑過第一輪」雙可能文案（R14），屬 advisory 不會 ❌；**心跳「新鮮」不等於「上一輪跑成功」**——即使心跳檔案本身新鮮（未過期），只要上一輪 nightly 實際有失敗，仍會額外印出一行「⚠️ nightly 最近一輪有 FAIL=N」類訊息（R15 起偵測），看到心跳正常也要留意這行；另會讀 GitHub CI 狀態並可能印兩種 ⚠️：最新一筆 run 非 success，以及「GitHub 排程軌長期未成功」（逐軌陳舊度，與最新一筆 run 是兩種粒度）——**這兩行都不要當成預設背景雜訊**：雲端 CI 是否活著是**輪次屬性、不是本文件的常數**（ONBOARDING §6.1／§9 已對同型句子做過同樣訂正），看到就當場唯讀現查 `gh run list --limit 10` 再判讀〔R15，僅當本機裝有 `gh` 且 git fetch 未離線/未被跳過時才會嘗試——ARCH-R15-REV-7 訂正：條件是「非離線、非跳過同步判定」而非「已同步成功」，工作樹髒污/與遠端分叉/pull 失敗導致實際未同步時，只要 fetch 本身有成功，仍會嘗試〕；Windows 專屬項目在 mac 上會跳過）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若 ❌ 原因是「另一個 dev_start 正在整備 venv／無法取得互斥鎖」：先確認真的沒有另一個 dev_start 在跑（含前次被中斷遺留的行程），把狀況回報給我；殘留的陳舊鎖在相關行程結束後、下次執行時會自動清除，不要急著手動刪 .dev_start.lock。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。
   - 若警告是「nightly 最近一輪有失敗」：**先判斷那輪紅是不是被同步撞出來的假紅**，再決定要不要追。作法＝比對 nightly log 裡失敗 stage 的起訖時間與 `git reflog --date=iso` 最近一次 merge/pull 的時間，時間區間重疊就高度可疑；接著把失敗的測試單獨重跑一次，全綠即為假紅。假紅要跟我說一聲，別默默當成迴歸去修。
     🔴 **不是只有「假紅／真迴歸」兩態**：nightly 跑的是 **merge 前**的 code，它的紅綠對 merge 後的 HEAD **沒有推論力**，所以不論時間有無重疊，都必須**在當前 HEAD 上重跑一次**。實遇第三態（2026-08-10）＝時間不重疊（非假紅），但那輪的失敗已被 merge 進來的修復解掉，同時換上一批**全新**失敗；只回答「是不是假紅」就結案，會同時追錯舊紅、漏看新紅（DEF-101-999(d)）。
   - **沒看到「工作樹不乾淨」警告不等於工作樹是乾淨的**，有兩個獨立原因：① dev_start 只在「同時落後 origin、真的要 pull」時才會提這件事（不需要 pull 就沒有擋的必要）；② 它判斷髒污時用的是 `git status --porcelain --untracked-files=no`，**未追蹤檔完全不在它的視野內**（ff pull 對未追蹤檔安全，是刻意設計）。要確認請自己跑 `git status --porcelain --untracked-files=all`——理由見〈🔁 平台切換 SOP〉A 段。

4. 由於 shell 狀態不會在你之後每次呼叫工具時持續生效（每次工具呼叫都是新行程，source 啟用的 .venv 只在那一次呼叫內有效），之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv/bin/python`（或先確認 `which python` 真的指向這個路徑）執行，不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

7. **僅限「剛從 Windows 切換過來的第一次啟動」**（🔴 **判斷依據是機械判準，不是記憶、也不是 dev_start [1/7] 的輸出**——`[1/7]` 讀的是本機 `.dev_env_state.json`，**雙機各自 clone 的拓撲永遠印「無切換」**，用它判斷必然漏做；而「上一輪在哪台機器」沒有任何人或 AI 能可靠記得。**改跑這一條，每次啟動都適用**：`.venv/bin/python tools/sync_onboarding_baselines.py --check-snapshot`，讀 **macOS 欄**那一段——只要它是 `presumed stale`、或其 `baseline-origin` 不是 `self-recorded`，就代表本欄需要回填，**本點就要做**；三項都新鮮才可跳過。此判準與輪號、日期、HEAD 皆無關，故不會過期）：另外要做 useMacWin.md〈🔁 平台切換 SOP〉**B 段**的事，其中核心是**回填 macOS 那一欄的 ONBOARDING.md §7 表② dated snapshot**——`.venv/bin/python tools/sync_onboarding_baselines.py --write --with-slow`，只能在 macOS 本機做（跨平台代填＝假 provenance，工具會 rc=2 拒絕），且必須在**不含 postgres/pgvector 選配的出廠環境 venv** 上跑，**不准**加 `--allow-pg-extras` 繞過拒跑。🔴 **那個 venv 不是本機 `.venv`**——本機 `.venv` 幾乎必然已被 pg extras 汙染（2026-08-10 實測 `psycopg2`／`sqlalchemy` 皆 PRESENT），工具會 rc=2 拒跑，所以這一步**必然**要另建臨時乾淨 venv（建法與污染探針見 B 段第 3 點；本機**沒有** `uv`，用 venv 自帶的 pip）。動手前先把該節整段讀完，不要只照這一行做；做完把工具輸出貼給我。

完成以上準備後，跟我簡短回報目前環境狀態（是否首次執行、是否偵測到從 Windows 切換過來、GitHub 同步結果〔已同步/離線跳過/有分叉等警告〕、.venv 是否有重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際的開發任務，不要自己先開始做事。
```

---

## 🪟 Windows 版

```
我現在在 Windows 上要開始開發/使用這個 monorepo（AISDCL_Agent，含 AutoClaude 與 AISDLC_SDD 兩個子專案）。請依序完成以下準備工作：

1. 一律先做一次 GitHub 同步（不要先判斷 tools/dev_start.ps1 是否存在再決定要不要同步——本機可能落後 origin/main、或雖然檔案存在但版本過舊，兩種情況都該先同步再說）：
   a. 先確認目前在 main 分支：git branch --show-current。若不是 main，停下來把分支名與 git status 列給我看，等我決定，不要自行切換分支，也不要在非 main 分支上執行下面的 merge（在 main 的舊祖先分支上跑 --ff-only merge 會把該分支指標靜默推到 origin/main，等於改寫分支）。
   b. 再確認此刻沒有 nightly 正在跑（**不可跳過**）：
        .venv\Scripts\python.exe tools/dev_start.py --check-nightly
      印出 idle（rc=0）才往下做；印出 NIGHTLY-RUNNING（rc=1）就停下來等它跑完（通常數分鐘，可看 AutoClaude/logs/ 最新 nightly log 的尾巴是否還在長）再同步，**期間也不要跑任何測試**。
      若印出的是 **UNDETERMINED**（rc 仍為 0，代表偵測機制自己無法判定，不是「沒在跑」）：請自己看 AutoClaude/logs/ 最新 nightly log 的尾巴是否還在長，確認沒在跑再往下做（R59 SD-R59-07 補：此前只交代 idle／NIGHTLY-RUNNING 兩態，第三態可達卻無指示，照做的人會卡住或亂猜）。
      為何必要：本機 nightly 走 schtasks 補跑（WakeToRun／StartWhenAvailable），機器一喚醒就補跑——正好是你開工的同一分鐘。2026-07-27 實測：git merge 於 18:41:26 抽換 113 個檔案，落在 nightly 那輪 pytest 的執行區間（18:41:10～18:42:50）正中間 → 5 支測試假紅（事後把那 5 支單獨重跑，全數通過）；更糟的是假紅會寫進 nightly_latest.log，讓**之後每天早上**的 dev_start 心跳哨兵都報「上一輪 nightly 有失敗」，把人導去追一個不存在的迴歸。
      （首次 clone、.venv 還沒建好時可略過此步——沒有 .venv 就不會有 nightly 排程；舊 checkout 若回報 unrecognized arguments，代表這支旗標要同步後才有，本次略過即可。）
   c. git fetch origin
      若 fetch 失敗（離線／網路問題）：不要卡住重試，明確告訴我「本次離線、跳過同步」，並在第 2 步的 dev_start 指令後面加上 --no-sync 繼續本機整備。
   d. git merge --ff-only origin/main
      若 --ff-only 失敗（本地領先、與遠端分叉、或未提交變更擋住 fast-forward），把 git status 和 git log main..origin/main 的結果列給我看，不要自動 rebase、reset --hard 或 stash；先讓我看過再決定。
   同步完成（或確認離線）後才繼續下一步（此時 tools/dev_start.ps1 必定存在且是最新版）。

2. 執行啟動程序（這次工具呼叫請把 timeout 設到上限 10 分鐘：首次執行或依賴變動時 bootstrap 合法耗時數分鐘，預設 2 分鐘 timeout 會腰斬安裝。萬一真的被中斷，直接重跑同一指令即可——腳本有未完成哨兵，會自動偵測半殘 .venv 重新整備）。依你執行指令的載具二選一：
   - 原生 PowerShell（含 Claude Code 的 PowerShell 工具；優先用這條）——在 repo 根目錄 dot-source（前面的點與空格不可省略）：
     . .\tools\dev_start.ps1
     成敗判斷請看輸出結尾「dev_start 摘要」的 ✅/❌，或讀 $LASTEXITCODE；絕不可用 $?（dot-source 後任何「執行成功」的陳述式都會把 $? 重設為 true，wrapper 檔頭 .NOTES 明載此陷阱）。
   - Git Bash / WSL 等非 PowerShell 載具——改用：
     powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1
     一定要用 -File，不要用 -Command 包 dot-source（dot-source 模式的 wrapper 刻意不呼叫 exit 以免關掉使用者 shell，經 -Command 呼叫時失敗的 exit code 會被吞掉、外層恆拿到 0，形成假綠）。

   注意：不論用哪種方式，啟動程序啟用的 .venv 都只在該次工具呼叫的行程內生效（每次工具呼叫都是新行程），之後的指令一律直接指定完整路徑 .venv\Scripts\python.exe（Git Bash 載具下寫 .venv/Scripts/python.exe），不要假設 `python` 已指向正確的直譯器。

   這是本專案的跨平台自動偵測啟動程序，會自動依序完成七件事：
   [1/7] 偵測目前環境（Developing vs Now）是否跨平台切換（例如上次在 mac 開發、這次換到 Windows）
   [2/7] GitHub 同步（fetch + fast-forward pull；髒工作樹/分叉/離線只會明示提醒，不會自動 stash/rebase/push；另偵測「nightly 正在跑」——此時落後 origin 也**不自動 pull**，只提醒你等它跑完再執行一次，避免抽換檔案造成整批假紅）
   [3/7] 跨平台切換時清除失效快取
   [4/7] 整備/修復 .venv（含跨平台換手保留、依賴 hash 比對、必要時自動跑 bootstrap）
   [5/7] 檢查並修復 git hooks（core.hooksPath）
   [6/7] 平台健檢（自動設定 core.longpaths=true，避免 MAX_PATH=260 限制炸掉深路徑。🔴 **R76-01 訂正——這一句最容易被讀成「longpaths 有人在管，我不用理」，而它治不了唯一真正會讓你開不了箱的那個時點**：這裡設的是 `--local`，也就是**這個 repo 已經 clone 成功之後**才寫得進去的設定；`git clone` 當下它還不存在。實測未帶旗標 clone 到 168 字元的目錄 → rc=128、27,523 支 tracked 檔只落地 301 支、`tools\bootstrap.ps1` 不在磁碟上（`tools\dev_start.ps1` 未逐檔查證，但缺 27,222 支檔的 checkout 本來就不能拿來開發）——**這種工作樹上，本節第 2 點那條指令沒有任何意義**。三層 config 實查：`--system` rc=1、`--global` rc=1、只有主 checkout 的 `--local` 是 true ⇒ fresh clone 零保護。**clone 當下必須自己帶** `git clone -c core.longpaths=true <url>`，並建議一次性 `git config --global core.longpaths true`；完整開箱步驟見 ONBOARDING.md §2 第 0 步；含 nightly 心跳三態檢查，「未偵測」＝排程未啟用**或已安裝但尚未跑過第一輪**（R14 消歧），屬 advisory 不會 ❌；**心跳「新鮮」不等於「上一輪跑成功」**——即使心跳檔案本身新鮮（未過期），只要上一輪 nightly 實際有失敗，仍會額外印出類似「⚠️ …有失敗…exit=1（failed stages: …）」的訊息（R23 起偵測，tail 掃描排程 log），看到心跳正常也要留意這行；另會讀 GitHub CI 狀態並可能印兩種 ⚠️：最新一筆 run 非 success，以及「GitHub 排程軌長期未成功」（逐軌陳舊度，與最新一筆 run 是兩種粒度）——**這兩行都不要當成預設背景雜訊**：雲端 CI 是否活著是**輪次屬性、不是本文件的常數**（ONBOARDING §6.1／§9 已對同型句子做過同樣訂正），看到就當場唯讀現查 `gh run list --limit 10` 再判讀〔R15，僅當本機裝有 `gh` 且 git fetch 未離線/未被跳過時才會嘗試——ARCH-R15-REV-7 訂正：條件是「非離線、非跳過同步判定」而非「已同步成功」，工作樹髒污/與遠端分叉/pull 失敗導致實際未同步時，只要 fetch 本身有成功，仍會嘗試〕）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若 ❌ 原因是「另一個 dev_start 正在整備 venv／無法取得互斥鎖」：先確認真的沒有另一個 dev_start 在跑（含前次被中斷遺留的行程），把狀況回報給我；殘留的陳舊鎖在相關行程結束後、下次執行時會自動清除，不要急著手動刪 .dev_start.lock。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。
   - 若出現「偵測不到 Git Bash（bash.exe）」（這行來自第 [5/7] 步重跑 hooks 安裝腳本時，不是平台健檢，也不會進 dev_start 摘要的警告計數）：**不要把它當成無害雜訊帶過**。偵測共用實作 `tools/lib/Find-GitBash.ps1::Find-GitBash` 是「PATH 上找 bash（排除路徑含 `System32` 段的 WSL 佔位）→ 找不到再回退查 `%ProgramFiles%`／`%ProgramFiles(x86)%`／`%LocalAppData%\Programs` 底下的 `Git\bin\bash.exe`」，這個 fallback 存在的目的正是「標準安裝只把 `Git\cmd` 放進 PATH、`Git\bin\bash.exe` 本來就不在 PATH」——也就是說**連 fallback 都落空才會印這行**，多半是真的沒裝 Git for Windows 或裝在非常規位置。三支 dispatcher hooks 全是 `#!/usr/bin/env bash`，屆時 commit/push 會真的跑不起來。請先跑 `git --version` 與 `where.exe bash` 把實況列給我看，再由我決定怎麼處理。
   - 若警告是「nightly 最近一輪有失敗」：**先判斷那輪紅是不是被同步撞出來的假紅**，再決定要不要追。作法＝比對 nightly log 裡失敗 stage 的起訖時間與 `git reflog --date=iso` 最近一次 merge/pull 的時間，時間區間重疊就高度可疑；接著把失敗的測試單獨重跑一次，全綠即為假紅（2026-07-27 實測就是這樣：5 支假紅、單獨重跑全數通過）。假紅要跟我說一聲，別默默當成迴歸去修。
     🔴 **不是只有「假紅／真迴歸」兩態**：nightly 跑的是 **merge 前**的 code，它的紅綠對 merge 後的 HEAD **沒有推論力**，所以不論時間有無重疊，都必須**在當前 HEAD 上重跑一次**。實遇第三態（2026-08-10 mac 側）＝時間不重疊（非假紅），但那輪的失敗已被 merge 進來的修復解掉，同時換上一批**全新**失敗；只回答「是不是假紅」就結案，會同時追錯舊紅、漏看新紅（DEF-101-999(d)）。
   - **沒看到「工作樹不乾淨」警告不等於工作樹是乾淨的**，有兩個獨立原因：① dev_start 只在「同時落後 origin、真的要 pull」時才會提這件事（不需要 pull 就沒有擋的必要）；② 它判斷髒污時用的是 `git status --porcelain --untracked-files=no`，**未追蹤檔完全不在它的視野內**（ff pull 對未追蹤檔安全，是刻意設計）。要確認請自己跑 `git status --porcelain --untracked-files=all`——理由見〈🔁 平台切換 SOP〉A 段。

4. 之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv\Scripts\python.exe`（Git Bash 載具下寫 `.venv/Scripts/python.exe`），不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

7. **僅限「剛從 mac 切換過來的第一次啟動」**（🔴 **判斷依據是機械判準，不是記憶、也不是 dev_start [1/7] 的輸出**——`[1/7]` 讀的是本機 `.dev_env_state.json`，**雙機各自 clone 的拓撲永遠印「無切換」**，用它判斷必然漏做；而「上一輪在哪台機器」沒有任何人或 AI 能可靠記得。**改跑這一條，每次啟動都適用**：`.venv\Scripts\python.exe tools/sync_onboarding_baselines.py --check-snapshot`，讀 **Windows 欄**那一段——只要它是 `presumed stale`、或其 `baseline-origin` 不是 `self-recorded`，就代表本欄需要回填，**本點就要做**；三項都新鮮才可跳過。此判準與輪號、日期、HEAD 皆無關，故不會過期）：另外要做 useMacWin.md〈🔁 平台切換 SOP〉**B 段**的事，其中核心是**回填 Windows 那一欄的 ONBOARDING.md §7 表② dated snapshot**——`.venv\Scripts\python.exe tools/sync_onboarding_baselines.py --write --with-slow`，只能在 Windows 本機做（跨平台代填＝假 provenance，工具會 rc=2 拒絕），且必須在**不含 postgres/pgvector 選配的出廠環境 venv** 上跑，**不准**加 `--allow-pg-extras` 繞過拒跑。🔴 **那個 venv 不是本機 `.venv`**——主 `.venv` 只要曾裝過 `[postgres,pgvector]` 就會讓工具 rc=2 拒跑（mac 側 2026-08-10 實測即是），這一步**必然**要另建臨時乾淨 venv（建法與污染探針見 B 段第 3 點）。動手前先把該節整段讀完，不要只照這一行做；做完把工具輸出貼給我。

完成以上準備後，跟我簡短回報目前環境狀態（是否首次執行、是否偵測到從 mac 切換過來、GitHub 同步結果〔已同步/離線跳過/有分叉等警告〕、.venv 是否有重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際的開發任務，不要自己先開始做事。
```

---

## 🔁 平台切換 SOP

適用兩種拓撲（見 [ONBOARDING.md](ONBOARDING.md) §2.1）：**共用工作目錄**（外接碟／同步資料夾，兩平台輪開同一份）與**雙機各自 clone**。差別只在「切換」是不是同一顆工作樹——A 段（離開前）與 B 段（到達後）兩邊都要做。

### A. 切換前 —— 做在「要離開」的那台機器上

這段的每一項在你關機之後都補不回來。四條 git 指令兩平台**逐字相同**（PowerShell 下照打即可）：

```bash
git fetch origin                                       # 先 fetch，下一條才有意義
git status --porcelain --untracked-files=all           # 期望：完全無輸出
git rev-list --left-right --count origin/main...main   # 期望：0<TAB>0（左＝落後、右＝領先未 push）
git stash list                                         # 期望：完全無輸出
git worktree list                                      # 期望：只有主 checkout 一行
```

🔴 **為什麼 `--untracked-files=all` 不可省**：預設的 `-unormal` 會把整個未追蹤目錄摺成一行 `?? sub/`（本機實測：`sub/deep/a.py`、`sub/deep/b.py` 兩支只印出 `?? sub/`），而**未 `git add` 的新檔對 `git ls-files` 型的掃描面天然隱形**——`DEF-101-751`／`DEF-101-752` 就是這麼發生的：一支全程 untracked 的新 `.py` 讓四輪四方複審與多次全套閘門實跑都拿到「全綠」，直到 `git add` 使它變成 tracked 的那一刻才冒出真紅。把這種檔留在原機器上＝把一個看不見的違規留在原地，而新平台上的「乾淨」會再騙你一次。

🔴 **雲端 CI：唯讀現查，且「未觸發 ≠ 綠」**

```bash
gh run list --limit 10 --json workflowName,conclusion,event,createdAt,headSha
```

根層 `.github/workflows/` 裡**只有 `root-infra-ci.yml` 是全變更觸發**（`on:` 底下無 `paths` 過濾，可自行實查）；`autoclaude-ci.yml`／`aisdlc-sdd-ci.yml`／`macos-compat-ci.yml`／`windows-compat-ci.yml` 都有 `paths` 白名單，這次 push 沒命中就**根本不會出現在 run 清單裡**。判讀時要先列出「這次 push 應該觸發哪幾支」再對帳，**缺席的一律當作未驗證，不是通過**。切換走人前若有還沒回來的 run，把 `headSha` 記進交接說明，別讓下一台機器以為已經驗完。

> 本節刻意**不記**「哪個平台的 CI 現在是綠是紅」「哪個平台有沒有真機輪」——那是輪次屬性、不是本文件的常數（ONBOARDING §6.1／§9 已對同型句子做過同樣訂正）。

### B. 切換後 —— 做在「剛到」的那台機器上

🔴 **三步的順序不可調換，尤其「閘門」必須排在「回填」之前**：回填寫的是 `ONBOARDING.md`＝**根層檔**，而 `tools/git-hooks/pre-push` 的慢層（`py_compile` ＋ `run_root_unittests.py`）**只在 push 範圍含根層檔時才跑**。先回填、後才發現那層有紅 ⇒ 回填成果 commit 過得去卻 **push 不出去**，被自己的紅鎖在本機（2026-08-10 mac 側實遇，DEF-101-999(e)）。

1. **照上面對應平台的啟動提示詞跑一次**。全新 Windows 機器另有一次性前置：預設 `ExecutionPolicy=Restricted` 會擋掉所有 `.ps1`（**含 dot-source 與 `Activate.ps1`**），先跑 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`（一般使用者權限即可，詳見 ONBOARDING §2.1／§5）。預期會看到 dev_start `[1/7]` 印出跨平台切換、`[3/7]` 清掉含絕對路徑的 `.pytest_cache`/`.ruff_cache`、`[4/7]` 把另一平台的 `.venv` 換手保留並換回本平台快取（共用工作目錄拓撲；雙機拓撲則是各自的 venv 各自新鮮）。

2. **跑一次全套閘門確立新平台基線，紅燈在這一步清完**：指令清單以 ONBOARDING §7 與根 [CLAUDE.md](CLAUDE.md) 為準。**本文件刻意不重抄任何數字**——全 repo pytest 基線數字的唯一站點是 ONBOARDING §7（由 `tools/check_pytest_baseline_sites.py` 機械守門，本檔正在它的掃描面內）。剛從另一平台過來的第一輪最容易在這裡冒出跨平台缺口（對方平台結構上跑不到的路徑），**那是本步驟的目的、不是意外**。

3. 🔴 **回填該平台的 ONBOARDING §7 表② dated snapshot —— 整份 SOP 裡唯一「只能在目標平台做」的事**：

   ```bash
   <乾淨 venv>/bin/python tools/sync_onboarding_baselines.py --write --with-slow
   ```

   - **為什麼只能在目標平台**：表② 是 dated snapshot（機器無法在根層閘門現場算出、無 live 鎖），逐平台記帳；跨平台代填＝假 provenance，工具對無對應欄的平台直接 rc=2 拒絕。
   - 🔴 **前置①：乾淨 venv（不是本機 `.venv`——它幾乎必然已被汙染，工具會 rc=2 拒跑）**：`import psycopg2` 與 `import sqlalchemy` 都要是 ModuleNotFoundError。污染探針用 ONBOARDING §7（R59 訂正）指定的寫法——它在乾淨與污染兩種情況下**都必定印出東西**，沒有「靜默零輸出」這個會被誤讀成乾淨的狀態（`python -m pip list` 在 uv 建的 venv 上零鑑別力，該 venv 內根本沒有 `pip` 模組）：

     ```bash
     python -c "import importlib.util as u; [print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') for m in ('psycopg2','sqlalchemy')]"
     ```

     兩行都必須是 `ABSENT` 才算乾淨；**任何一行印不出來就是探針壞了**，不是「乾淨」。乾淨 venv 的建法沿用 ONBOARDING §7 各輪校正註記寫過的既有作法（全新臨時目錄 + `python3.11 -m venv` + `uv pip install -e '.[dev,notifications]'`），**不要另編一套**；🔴 **但 `uv` 不一定在**——mac 側 2026-08-10 實測 `command -v uv` 為空（它只活在 shell profile 裡；`.venv/bin`、`~/.local/bin`、`~/.cargo/bin` 皆無），照抄該行只會得到 command not found。此時改用新 venv 自帶的 `python -m pip install -e '.[dev,notifications]'`——這正是 ONBOARDING §7 R55／R56 註記走的同一條路，不算另編一套。
   - 🔴 **前置②：docker daemon 要開**：ci-gate 的逐軌計數對它敏感（§7 記載的 ±3），provenance 會如實記 `docker=up`／`down`。兩平台欄一個 `up` 一個 `down` 就是**不同條件**，依 §7 既定紀律**不可相減**——mac 側 2026-08-10 實遇：忘了開，兩欄從此不可比，只能等下次重量（DEF-101-999(e)）。
   - 🔴 **不准用 `--allow-pg-extras` 繞過拒跑**：那會讓 provenance 記成 `pgextras=present`，等於悄悄改掉「出廠環境」的定義，而且**沒有任何機械物會替你察覺這個語意變更**。工具拒跑是設計，不是障礙。
   - **`unrecorded` 的語意不要讀錯**：某欄 provenance 印 `unrecorded`，只代表「該欄數字量於逐平台 provenance 機制落地之前，或不是一次量完的同世代值」，**不等於那個平台沒有真機開發史**。要知道哪一欄新鮮、上次誰在哪台機器量的，一律看 live 來源，別看任何文件裡的結論句：

     ```bash
     python tools/sync_onboarding_baselines.py --check-snapshot   # 各欄 provenance ＋ presumed-stale 判定
     grep -n 'snapshot-fingerprints-' ONBOARDING.md               # 兩條錨的 measured-at/host/docker/pgextras
     ```

     `--check-snapshot` 的 rc 反映的是「**本機平台那一欄**的指紋有沒有漂移」，不是「有沒有真機量測過」，兩者別混。非本機平台欄在單機交替下**結構上恆為 presumed stale**，那則 `ℹ️` 是常態而非事件。

### C. 兩平台語法差異雷區（照抄另一平台的指令會出事的地方）

以下四條都是實際踩過的；完整對照見 ONBOARDING §5（雷區表）、§6（雙平台腳本對照）、§7（雙平台驗證指令）。

| 症狀 | 根因 | 正確寫法 |
|------|------|---------|
| macOS 上安裝 extras 報 `zsh: no matches found`，訊息與套件完全無關 | macOS 預設 shell 是 zsh，`nomatch` 預設開啟：未加引號的 `.[...]` 會被當 glob 做 filename generation，repo 內無匹配即**在執行前中止整條指令**（uv／pip 根本沒被呼叫）。同一行在 bash 與 PowerShell 下正常 ⇒ Windows 開發者永遠不會遇到 | extras 一律加**單引號**：`uv pip install -e '.[dev,notifications]'`（三種 shell 皆正確）。具名套件形態同理：`'autoclaude[postgres]'`。機械鎖：`tools/tests/test_extras_quoting_zsh_safety.py` |
| Windows 上照抄 `PYTHONUTF8=1 lint-imports` 得到 `The term 'PYTHONUTF8=1' is not recognized`，看起來像 lint-imports 沒裝 | PowerShell **沒有** `VAR=value <指令>` 這種行內環境變數前綴語法 | 改寫為 `$env:PYTHONUTF8=1; lint-imports`。機械鎖：`tools/tests/test_doc_env_prefix_platform_parity_r60.py`（活文件內 bash 前綴必須有同檔 PowerShell 對照） |
| Windows 上呼叫 bash 腳本，拿到 UTF-16LE 亂碼 `Windows Subsystem for Linux has no installed distributions.`，而受測腳本**一行都沒執行**（歸因完全錯誤的紅燈） | Windows 的 `CreateProcess(lpApplicationName=NULL)` 解析裸名的順序是「應用程式目錄 → 當前目錄 → **System32** → Windows 目錄 → PATH」，System32 排在 PATH **之前** ⇒ 只要 argv[0] 是裸名 `"bash"`，`C:\Windows\System32\bash.exe`（WSL 啟動器）**必定**先命中，與 PATH 上有沒有 Git Bash、排多前面無關（`DEF-101-753`） | 一律解析成**絕對路徑**再呼叫：PowerShell 用 `tools/lib/Find-GitBash.ps1::Find-GitBash`、Python 測試用 `tools/tests/_platform_helpers.usable_bash_for_fixture()`、Python 工具用 `tools/integration_gate_core.py::find_git_bash()`；`shutil.which("bash")`（只查 PATH）是天然對照組。**禁止**把裸 `"bash"` 交給 `subprocess` |
| macOS 上讀 `${PIPESTATUS[0]}` 拿到**空字串**，管線的 rc 靜默消失（`cmd \| tail` 之後判不出成敗，容易把紅讀成綠） | Claude Code 的 Bash 工具在 macOS 走 **zsh**，而 `PIPESTATUS` 是 bash 的陣列名；zsh 叫 `pipestatus` 且**下標從 1 起**（`$pipestatus[1]`）。兩平台的 `.ps1`／CI 都不受影響 ⇒ 只有在 mac 上用工具跑管線時才會踩到 | 別用管線判 rc：改成 `cmd > out.log 2>&1; rc=$?` 再讀檔；或整段包 `bash -c '…'`。2026-08-10 實遇（DEF-101-999(c)） |
| macOS 上迴圈跑「帶子指令參數的守門」全報 `rc=2`，看起來像整批守門紅掉，實際上 `bash` 下全綠 | 同上 —— zsh **預設不對未加引號的變數做分詞**（no SH_WORD_SPLIT）：`for g in "x.py --check"; do $PY $g; done` 會把整串當**單一檔名**交給 python ⇒ `can't open file` 的 rc 恰好也是 2，與「守門判紅」無法從 rc 區分 | 需要分詞就顯式包 `bash -c '…'`（pre-push 本身是 bash，故 hook 內同樣寫法正確）；或改用陣列逐項傳參。2026-08-10 實遇並**一度誤報三支守門為紅**（DEF-101-999(c)） |
| push 被 pre-push 擋下並印「找不到 ruff」 | root-infra 快層對齊 `root-infra-ci.yml`，會跑 `ruff check tools/ --no-cache`；**ruff 缺席＝fail-loud（rc=1），刻意不軟跳過**——軟跳過會退回「宣告有、執行者無」的假綠。另：ruff 的 `warning:`（如壞掉的 noqa 指令）走 stderr 且不改 rc，本層收下 stderr 後照樣判失敗 | 先啟用 `.venv` 並裝好開發相依（hook 訊息即指路：`cd AutoClaude && uv pip install -e '.[dev,notifications]'`）。`--no-cache` 不可省的理由見 `tools/git-hooks/pre-push` 該段註解 |

> 兩平台**共通**的一條：shell 狀態不會跨工具呼叫存活（每次工具呼叫都是新行程），所以 `source`／dot-source 啟用的 venv 只在那一次呼叫內有效——之後一律用完整路徑 `.venv/bin/python`（mac）或 `.venv\Scripts\python.exe`（Windows）。

### D. 跑全套測試前：先把 CI 對等 PG 容器拉起來（R83，兩平台共通）

🔴 **這一條與 B 段第 2 步（「跑一次全套閘門確立新平台基線」）直接相關**：AutoClaude 全套 pytest 的 `skipped` 裡有**一整類**（PG 相依）**只是因為 docker daemon 沒開**——不是缺件、不是平台差、也不是退化。解法是**一行 `docker compose`，零程式改動、零環境變數**（`AutoClaude/tests/conftest.py` 的 PG autodetect 會自己偵測並注入 DSN）。它消掉幾支是**量測值**，本檔刻意不寫死；完整做法、憑證行、現查指令與三點誠實劃界一律見 **ONBOARDING.md §7.1**（唯一站點，本檔不重抄，避免第二個會漂的家）。

最短路徑（切換後想立刻把基線量對時照這個順序）：

```bash
# macOS / Linux（Windows 版見下一塊）
open -a Docker                                                   # 啟動 Docker Desktop
docker info --format '{{.ServerVersion}}'                        # 印得出版本號才算 daemon 活著
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d
# migrate 這一步必須自己給 DSN（alembic 是另一個行程，autodetect 只注入 pytest 那個行程）；
# 刻意用行內前綴而非 export——export 出去會讓 pytest 走「顯式優先」剎車，憑證行改印
# `[PG autodetect] 跳過：… 已由使用者顯式設定（顯式優先）`（PG 照樣接得上，但驗不到 autodetect 這條路）
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

⚠️ **與 B 段第 3 步的關係別搞混**：那一步（回填 §7 表② dated snapshot）要的是**出廠環境乾淨 venv**，而本節是「日常開發時把 skip 降到最低」。兩者的 provenance 欄位會如實記下 `docker=up`／`down`，**不同條件的兩欄依 §7 既定紀律不可相減**。

---

## 可選旗標

需要時追加在對應提示詞第 2 步的 dev_start 指令後面（wrapper 會原樣轉傳給核心 tools/dev_start.py），或另外請 Claude Code 加上：

- `--no-sync`：跳過 GitHub 同步（離線工作時使用；此時提示詞第 1 步的手動同步也一併跳過）
- `--force-bootstrap`：強制重跑 bootstrap 重新整備依賴（懷疑 .venv 不完整時使用）
- `--check-nightly`：**只查**本機是否有 nightly 正在跑後立刻結束，不做任何整備（idle → rc=0／NIGHTLY-RUNNING → rc=1／UNDETERMINED → rc=0）。提示詞第 1 步 b 用的就是它；平時想確認「現在能不能安心跑全套測試」也可以單獨呼叫。查的是 nightly 腳本自己持有的去重鎖（Windows 具名 Mutex／mac 鎖目錄），不是猜 log 時間。

用法示例：

```
source tools/dev_start.sh --no-sync                                  # macOS
. .\tools\dev_start.ps1 --no-sync                                    # Windows（PowerShell）
powershell -ExecutionPolicy Bypass -File tools/dev_start.ps1 --no-sync   # Windows（Git Bash/WSL 載具）
```
