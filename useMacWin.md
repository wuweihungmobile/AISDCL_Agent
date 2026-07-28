# 跨平台啟動提示詞（macOS / Windows）

給 Claude Code 使用的完整提示詞，於**新開 session 的第一則訊息**直接複製貼上對應平台版本即可。核心依據：[tools/dev_start.py](tools/dev_start.py) 跨平台自動偵測啟動程序。

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
   [6/7] 平台健檢（含 nightly 心跳三態檢查——mac 上會用 `launchctl` 自動消歧「已載入尚未首跑」vs「未安裝」（R15，SA-R15-REV-3 訂正同步）；查不到 launchctl 結果時退回「未偵測＝排程未啟用或尚未跑過第一輪」雙可能文案（R14），屬 advisory 不會 ❌；**心跳「新鮮」不等於「上一輪跑成功」**——即使心跳檔案本身新鮮（未過期），只要上一輪 nightly 實際有失敗，仍會額外印出一行「⚠️ nightly 最近一輪有 FAIL=N」類訊息（R15 起偵測），看到心跳正常也要留意這行；另會嘗試讀 GitHub CI 最新 run 狀態，若 CI 帳務停擺/失敗中會印一行 ⚠️ 屬預期〔R15，僅當本機裝有 `gh` 且 git fetch 未離線/未被跳過時才會嘗試——ARCH-R15-REV-7 訂正：條件是「非離線、非跳過同步判定」而非「已同步成功」，工作樹髒污/與遠端分叉/pull 失敗導致實際未同步時，只要 fetch 本身有成功，仍會嘗試〕；Windows 專屬項目在 mac 上會跳過）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若 ❌ 原因是「另一個 dev_start 正在整備 venv／無法取得互斥鎖」：先確認真的沒有另一個 dev_start 在跑（含前次被中斷遺留的行程），把狀況回報給我；殘留的陳舊鎖在相關行程結束後、下次執行時會自動清除，不要急著手動刪 .dev_start.lock。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。
   - 若警告是「nightly 最近一輪有失敗」：**先判斷那輪紅是不是被同步撞出來的假紅**，再決定要不要追。作法＝比對 nightly log 裡失敗 stage 的起訖時間與 `git reflog --date=iso` 最近一次 merge/pull 的時間，時間區間重疊就高度可疑；接著把失敗的測試單獨重跑一次，全綠即為假紅。假紅要跟我說一聲，別默默當成迴歸去修。
   - **沒看到「工作樹不乾淨」警告不等於工作樹是乾淨的**：dev_start 只在「同時落後 origin、真的要 pull」時才會提這件事（不需要 pull 就沒有擋的必要）。要確認請自己跑 git status。

4. 由於 shell 狀態不會在你之後每次呼叫工具時持續生效（每次工具呼叫都是新行程，source 啟用的 .venv 只在那一次呼叫內有效），之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv/bin/python`（或先確認 `which python` 真的指向這個路徑）執行，不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

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
   [6/7] 平台健檢（自動設定 core.longpaths=true，避免 MAX_PATH=260 限制炸掉深路徑；含 nightly 心跳三態檢查，「未偵測」＝排程未啟用**或已安裝但尚未跑過第一輪**（R14 消歧），屬 advisory 不會 ❌；**心跳「新鮮」不等於「上一輪跑成功」**——即使心跳檔案本身新鮮（未過期），只要上一輪 nightly 實際有失敗，仍會額外印出類似「⚠️ …有失敗…exit=1（failed stages: …）」的訊息（R23 起偵測，tail 掃描排程 log），看到心跳正常也要留意這行；另會嘗試讀 GitHub CI 最新 run 狀態，若 CI 帳務停擺/失敗中會印一行 ⚠️ 屬預期〔R15，僅當本機裝有 `gh` 且 git fetch 未離線/未被跳過時才會嘗試——ARCH-R15-REV-7 訂正：條件是「非離線、非跳過同步判定」而非「已同步成功」，工作樹髒污/與遠端分叉/pull 失敗導致實際未同步時，只要 fetch 本身有成功，仍會嘗試〕）
   [7/7] 狀態寫回

3. 檢查輸出的「dev_start 摘要」：
   - 若結尾是 ❌，先幫我排除錯誤，不要跳過或忽略，也不要自己嘗試用 --force-bootstrap 以外的手段硬做。
   - 若 ❌ 原因是「另一個 dev_start 正在整備 venv／無法取得互斥鎖」：先確認真的沒有另一個 dev_start 在跑（含前次被中斷遺留的行程），把狀況回報給我；殘留的陳舊鎖在相關行程結束後、下次執行時會自動清除，不要急著手動刪 .dev_start.lock。
   - 若只有 ⚠️ 警告（尤其是「工作樹不乾淨」「與 origin 分叉」「領先 origin 未 push」這類），簡短列給我看，讓我自己決定要不要處理，不要自動 commit/stash/push 幫我決定。
   - 若警告是「偵測不到 Git Bash（bash.exe）」：這在標準 Git for Windows 安裝下很常見（安裝程式預設只把 `Git\cmd` 加進 PATH，`Git\bin\bash.exe` 本來就不在 PATH，是官方建議設定，不代表沒裝 Git Bash）。先用 `git --version` 確認有裝 Git for Windows 就好，不必為此改 PATH；只有之後真的 commit/push 卡住才需要進一步處理。
   - 若警告是「nightly 最近一輪有失敗」：**先判斷那輪紅是不是被同步撞出來的假紅**，再決定要不要追。作法＝比對 nightly log 裡失敗 stage 的起訖時間與 `git reflog --date=iso` 最近一次 merge/pull 的時間，時間區間重疊就高度可疑；接著把失敗的測試單獨重跑一次，全綠即為假紅（2026-07-27 實測就是這樣：5 支假紅、單獨重跑全數通過）。假紅要跟我說一聲，別默默當成迴歸去修。
   - **沒看到「工作樹不乾淨」警告不等於工作樹是乾淨的**：dev_start 只在「同時落後 origin、真的要 pull」時才會提這件事（不需要 pull 就沒有擋的必要）。要確認請自己跑 git status。

4. 之後所有 Python 相關指令（pytest、ruff、pip 等）請直接使用 `.venv\Scripts\python.exe`（Git Bash 載具下寫 `.venv/Scripts/python.exe`），不要誤用系統 Python。

5. 確認你已讀過根目錄 CLAUDE.md（monorepo 導覽），並在動手前先讀清楚本次工作屬於哪個子專案（AutoClaude 或 AISDLC_SDD），進去該子專案前務必先讀它自己的 CLAUDE.md ——兩份子 CLAUDE.md 都是 override 級規範，其目錄/命名/測試規則以子專案內部路徑為準，不要套用錯誤的相對路徑假設。

6. 回覆一律使用繁體中文。

完成以上準備後，跟我簡短回報目前環境狀態（是否首次執行、是否偵測到從 mac 切換過來、GitHub 同步結果〔已同步/離線跳過/有分叉等警告〕、.venv 是否有重建、hooks 是否正常、有沒有需要我處理的警告），然後等我下達實際的開發任務，不要自己先開始做事。
```

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
